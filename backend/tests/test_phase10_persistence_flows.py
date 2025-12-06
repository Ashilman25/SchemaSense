"""
Comprehensive regression tests for Phase 10 persistence work (10.1–10.4).

Focus areas:
- Phase 10.1 regression: edits must never be cache-only (DDL executed + PKs/FKs intact).
- Phase 10.2: ER + DDL edit endpoints generate/execute DDL against the real database.
- Phase 10.3: Cache is invalidated and refreshed from the database after mutations.
- Phase 10.4: Session handling uses signed cookies for reconnect across reloads.
"""

import pytest
import psycopg2
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response
from http.cookies import SimpleCookie

from app.main import app
from app.db import DatabaseConfig, set_database_config
from app.schema.cache import clear_schema_cache, set_cached_schema, get_cached_schema
from app.models.schema_model import CanonicalSchemaModel, Table, Column
from app.routes import schema as schema_routes
from app.utils.session import get_or_create_session_id


@pytest.fixture
def test_db_config():
    """Provide database credentials used across these integration tests."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="schemasense",
        user="schemasense",
        password="schemasense_dev",
    )


@pytest.fixture
def client(test_db_config):
    """Fresh TestClient with DB config set and cache cleared."""
    set_database_config(test_db_config)
    clear_schema_cache()
    return TestClient(app)


@pytest.fixture
def db_connection(test_db_config):
    """Direct connection for verification queries and cleanup."""
    dsn = (
        f"postgresql://{test_db_config.user}:{test_db_config.password}"
        f"@{test_db_config.host}:{test_db_config.port}/{test_db_config.dbname}"
    )
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def cleanup_test_artifacts(db_connection):
    """
    Drop all temporary tables before and after each test.

    Order matters for FK constraints: drop children first.
    """
    tables = [
        "phase10_child_rel",
        "phase10_parent_rel",
        "phase10_inline_pk",
        "phase10_cache_new",
        "phase10_activity_table",
    ]

    cursor = db_connection.cursor()
    for name in tables:
        cursor.execute(f'DROP TABLE IF EXISTS public.{name} CASCADE')
    cursor.close()
    yield
    cursor = db_connection.cursor()
    for name in tables:
        cursor.execute(f'DROP TABLE IF EXISTS public.{name} CASCADE')
    cursor.close()
    clear_schema_cache()


class TestERInlineColumnsPrimaryKey:
    """
    Validate the regression fix where inline columns on add_table must create PKs on first try.
    """

    def test_add_table_inline_columns_creates_pk_constraint(self, client, db_connection):
        """
        Add a table with columns provided directly on the add_table action.
        Expect:
        - DDL executes successfully (table exists).
        - Primary key constraint exists in the database.
        - API response flags the PK column as is_pk=True.
        """
        er_actions = {
            "actions": [
                {
                    "type": "add_table",
                    "name": "phase10_inline_pk",
                    "schema": "public",
                    "columns": [
                        {
                            "name": "id",
                            "type": "serial",
                            "nullable": False,
                            "is_pk": True,
                            "is_fk": False,
                        },
                        {
                            "name": "name",
                            "type": "text",
                            "nullable": True,
                            "is_pk": False,
                            "is_fk": False,
                        },
                    ],
                }
            ]
        }

        response = client.post("/api/schema/er-edit", json=er_actions)
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True

        cursor = db_connection.cursor()
        cursor.execute(
            """
            SELECT constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name = 'phase10_inline_pk'
              AND constraint_type = 'PRIMARY KEY'
            """
        )
        pk_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'phase10_inline_pk'
            ORDER BY ordinal_position
            """
        )
        column_rows = cursor.fetchall()
        cursor.close()

        assert pk_rows, "Primary key constraint should be present when columns include is_pk"
        assert ("id", "NO") in column_rows, "PK column should be NOT NULL in the database"

        table = next(
            t for t in payload["schema"]["tables"] if t["name"] == "phase10_inline_pk"
        )
        id_column = next(c for c in table["columns"] if c["name"] == "id")
        assert id_column["is_pk"] is True, "API payload must surface PK flag for inline columns"


class TestCacheRefreshAndStaleCacheEviction:
    """
    Ensure Phase 10.3 behavior: mutations refresh the cache and discard stale entries.
    """

    def test_er_edit_replaces_stale_cached_model(self, client):
        """
        Preload cache with a fake table and ensure ER edit refreshes from DB,
        so stale cached-only tables are removed from the returned schema.
        """
        cached_model = CanonicalSchemaModel(
            tables={
                "public.cached_only_phase10": Table(
                    name="cached_only_phase10",
                    schema="public",
                    columns=[Column(name="ghost", type="text", is_pk=False, is_fk=False, nullable=True)],
                )
            },
            relationships=[],
        )
        set_cached_schema(cached_model)
        assert get_cached_schema() is not None, "Fixture should prime cache before mutation"

        er_actions = {
            "actions": [
                {
                    "type": "add_table",
                    "name": "phase10_cache_new",
                    "schema": "public",
                    "columns": [
                        {"name": "id", "type": "serial", "nullable": False, "is_pk": True, "is_fk": False}
                    ],
                }
            ]
        }

        response = client.post("/api/schema/er-edit", json=er_actions)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        table_names = [t["name"] for t in data["schema"]["tables"]]
        assert "cached_only_phase10" not in table_names, "Stale cached table must be evicted after refresh"
        assert "phase10_cache_new" in table_names, "New DB-backed table should appear after refresh"


class TestDDLExecutionWithRelationships:
    """
    Validate Phase 10.2/10.3 for DDL endpoint: executes statements, refreshes schema, and surfaces relationships.
    """

    def test_ddl_edit_executes_and_returns_relationships(self, client, db_connection):
        """
        Apply DDL defining parent/child tables with a foreign key.
        Confirm:
        - Tables exist in the database.
        - PK flags present on parent PK.
        - Relationship appears in API payload.
        """
        ddl = """
        CREATE TABLE public.phase10_parent_rel (
            id SERIAL PRIMARY KEY,
            label text
        );

        CREATE TABLE public.phase10_child_rel (
            id SERIAL PRIMARY KEY,
            parent_id integer REFERENCES public.phase10_parent_rel(id),
            note text
        );
        """

        response = client.post("/api/schema/ddl-edit", json={"ddl": ddl})
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

        cursor = db_connection.cursor()
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name IN ('phase10_parent_rel', 'phase10_child_rel')
            """
        )
        tables_in_db = {row[0] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT constraint_type
            FROM information_schema.table_constraints
            WHERE table_schema = 'public'
              AND table_name = 'phase10_parent_rel'
              AND constraint_type = 'PRIMARY KEY'
            """
        )
        pk_parent = cursor.fetchall()
        cursor.close()

        assert {"phase10_parent_rel", "phase10_child_rel"} <= tables_in_db
        assert pk_parent, "Parent table should have a PK constraint"

        tables = {t["name"]: t for t in result["schema"]["tables"]}
        assert tables["phase10_parent_rel"]["columns"][0]["is_pk"] is True

        relationships = result["schema"]["relationships"]
        assert any(
            rel["from_table"].endswith("phase10_child_rel")
            and rel["to_table"].endswith("phase10_parent_rel")
            and rel["from_column"] == "parent_id"
            and rel["to_column"] == "id"
            for rel in relationships
        ), "FK relationship should be present in schema payload after refresh"


class TestActivityTrackingForManagedDBs:
    """
    Ensure Phase 10.3 behavior: update_db_activity is invoked for managed DB prefixes without touching live admin DBs.
    """

    def test_activity_tracking_called_for_managed_db_prefix(self, client, monkeypatch):
        """
        Simulate a managed DB config (schemasense_user_*) and assert update_db_activity is called.
        Use monkeypatch to keep real DB connections intact while faking the managed DB name.
        """
        calls = []

        def fake_update(db_name: str):
            calls.append(db_name)

        monkeypatch.setattr(schema_routes, "update_db_activity", fake_update)

        class FakeConfig(DatabaseConfig):
            pass

        def fake_get_db_config():
            return FakeConfig(
                host="localhost",
                port=5432,
                dbname="schemasense_user_mocked",
                user="schemasense",
                password="schemasense_dev",
            )

        monkeypatch.setattr(schema_routes, "get_database_config", fake_get_db_config)

        er_actions = {
            "actions": [
                {
                    "type": "add_table",
                    "name": "phase10_activity_table",
                    "schema": "public",
                    "columns": [
                        {"name": "id", "type": "serial", "nullable": False, "is_pk": True, "is_fk": False}
                    ],
                }
            ]
        }

        response = client.post("/api/schema/er-edit", json=er_actions)
        assert response.status_code == 200
        assert response.json()["success"] is True

        assert calls == ["schemasense_user_mocked"], "update_db_activity should run for managed DB prefixes"


class TestSessionCookiePersistence:
    """
    Cover Phase 10.4: session IDs must persist across requests via signed cookies.
    """

    def test_get_or_create_session_id_sets_and_reuses_cookie(self):
        """
        First call (no cookie) should set a signed cookie.
        Second call with that cookie should reuse the same session and not emit a new Set-Cookie.
        """
        request1 = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [],
            }
        )
        response1 = Response()

        session_id_first = get_or_create_session_id(request1, response1)
        assert session_id_first

        set_cookie_header = response1.headers.get("set-cookie")
        assert set_cookie_header, "First call should set a session cookie"

        cookie = SimpleCookie()
        cookie.load(set_cookie_header)
        session_cookie_value = next(iter(cookie.values())).value
        cookie_name = next(iter(cookie.keys()))

        request2 = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [(b"cookie", f"{cookie_name}={session_cookie_value}".encode())],
            }
        )
        response2 = Response()

        session_id_second = get_or_create_session_id(request2, response2)
        assert session_id_second == session_id_first, "Session ID should persist across calls with cookie"
        assert "set-cookie" not in response2.headers, "Existing session should not emit a new cookie"
