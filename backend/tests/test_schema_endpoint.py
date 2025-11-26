import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.main import app
import app.routes.schema as schema_route


class DummySchemaModel:
    def __init__(self, payload: dict):
        self.payload = payload
        self.to_dict_calls = 0

    def to_dict_for_api(self) -> dict:
        self.to_dict_calls += 1
        return self.payload


@pytest.fixture
def client():
    return TestClient(app)


def test_schema_endpoint_serializes_model(monkeypatch, client):
    """Per plan 1.6: the endpoint should serialize the canonical model via to_dict_for_api()."""
    payload = {
        "tables": [
            {
                "schema": "public",
                "name": "customers",
                "columns": [
                    {"name": "id", "type": "integer", "is_pk": True, "is_fk": False, "nullable": False},
                    {"name": "name", "type": "text", "is_pk": False, "is_fk": False, "nullable": True},
                ],
            }
        ],
        "relationships": [
            {
                "from_table": "public.orders",
                "from_column": "customer_id",
                "to_table": "public.customers",
                "to_column": "id",
            }
        ],
    }
    model = DummySchemaModel(payload)
    conn = object()

    monkeypatch.setattr(schema_route, "get_connection", lambda: conn, raising=False)
    monkeypatch.setattr(
        schema_route,
        "get_or_refresh_schema",
        lambda passed_conn: model if passed_conn is conn else None,
        raising=False,
    )

    response = client.get("/api/schema")

    assert response.status_code == 200
    assert response.json() == payload
    assert model.to_dict_calls == 1


def test_schema_endpoint_refreshes_when_cache_empty(monkeypatch, client):
    """First call should refresh, subsequent calls should reuse the cached model."""
    payload = {"tables": [], "relationships": []}
    model = DummySchemaModel(payload)
    conn = object()
    refresh_calls = {"count": 0}

    def fake_get_connection():
        return conn

    def fake_get_or_refresh_schema(passed_conn):
        assert passed_conn is conn
        if refresh_calls["count"] == 0:
            refresh_calls["count"] += 1
        return model

    monkeypatch.setattr(schema_route, "get_connection", fake_get_connection, raising=False)
    monkeypatch.setattr(schema_route, "get_or_refresh_schema", fake_get_or_refresh_schema, raising=False)

    first = client.get("/api/schema")
    second = client.get("/api/schema")

    assert first.status_code == 200
    assert second.status_code == 200
    assert refresh_calls["count"] == 1  # Only the first request should trigger a refresh
    assert model.to_dict_calls == 2  # Serialization happens on every response


def test_schema_endpoint_handles_empty_schema(monkeypatch, client):
    """Ensure empty schema models still return the expected shape."""
    payload = {"tables": [], "relationships": []}
    model = DummySchemaModel(payload)
    conn = object()

    monkeypatch.setattr(schema_route, "get_connection", lambda: conn, raising=False)
    monkeypatch.setattr(
        schema_route,
        "get_or_refresh_schema",
        lambda passed_conn: model if passed_conn is conn else None,
        raising=False,
    )

    response = client.get("/api/schema")

    assert response.status_code == 200
    body = response.json()
    assert body["tables"] == []
    assert body["relationships"] == []
    assert model.to_dict_calls == 1


def test_schema_endpoint_returns_tables_with_pk_and_fk_flags(monkeypatch, client):
    """Validate table/column fields and PK/FK flags per the API contract."""
    payload = {
        "tables": [
            {
                "schema": "sales",
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "integer", "is_pk": True, "is_fk": False, "nullable": False},
                    {"name": "customer_id", "type": "integer", "is_pk": False, "is_fk": True, "nullable": False},
                    {"name": "notes", "type": "text", "is_pk": False, "is_fk": False, "nullable": True},
                ],
            }
        ],
        "relationships": [
            {
                "from_table": "sales.orders",
                "from_column": "customer_id",
                "to_table": "public.customers",
                "to_column": "id",
            }
        ],
    }
    model = DummySchemaModel(payload)
    conn = object()

    monkeypatch.setattr(schema_route, "get_connection", lambda: conn, raising=False)
    monkeypatch.setattr(
        schema_route,
        "get_or_refresh_schema",
        lambda passed_conn: model if passed_conn is conn else None,
        raising=False,
    )

    response = client.get("/api/schema")

    assert response.status_code == 200
    body = response.json()
    assert len(body["tables"]) == 1
    table = body["tables"][0]
    assert table["schema"] == "sales"
    assert table["name"] == "orders"
    assert table["columns"][0]["is_pk"] is True
    assert table["columns"][1]["is_fk"] is True
    assert body["relationships"][0]["from_table"] == "sales.orders"
    assert body["relationships"][0]["to_table"] == "public.customers"


def test_schema_endpoint_supports_multiple_tables_and_schemas(monkeypatch, client):
    """Return should include all tables and relationship edges."""
    payload = {
        "tables": [
            {
                "schema": "public",
                "name": "customers",
                "columns": [{"name": "id", "type": "integer", "is_pk": True, "is_fk": False, "nullable": False}],
            },
            {
                "schema": "analytics",
                "name": "events",
                "columns": [{"name": "event_id", "type": "uuid", "is_pk": True, "is_fk": False, "nullable": False}],
            },
        ],
        "relationships": [
            {
                "from_table": "analytics.events",
                "from_column": "customer_id",
                "to_table": "public.customers",
                "to_column": "id",
            }
        ],
    }
    model = DummySchemaModel(payload)
    conn = object()

    monkeypatch.setattr(schema_route, "get_connection", lambda: conn, raising=False)
    monkeypatch.setattr(
        schema_route,
        "get_or_refresh_schema",
        lambda passed_conn: model if passed_conn is conn else None,
        raising=False,
    )

    response = client.get("/api/schema")

    assert response.status_code == 200
    body = response.json()
    schemas = {tbl["schema"] for tbl in body["tables"]}
    table_names = {tbl["name"] for tbl in body["tables"]}
    assert schemas == {"public", "analytics"}
    assert {"customers", "events"} == table_names
    assert body["relationships"][0]["from_table"] == "analytics.events"
    assert body["relationships"][0]["to_table"] == "public.customers"
