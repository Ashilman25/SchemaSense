"""
Integration tests for Phase 10.2 - DDL Execution from ER/Schema SQL Edits

Tests that schema edits are actually executed against the database and can be queried.
"""

import pytest
import psycopg2
from fastapi.testclient import TestClient
from app.main import app
from app.db import set_database_config, DatabaseConfig
from app.schema.cache import clear_schema_cache


@pytest.fixture
def test_db_config():
    """Provide test database configuration."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="schemasense",
        user="schemasense",
        password="schemasense_dev"
    )


@pytest.fixture
def client(test_db_config):
    """Create test client with database configuration."""
    set_database_config(test_db_config)
    clear_schema_cache()
    return TestClient(app)


@pytest.fixture
def db_connection(test_db_config):
    """Create direct database connection for verification."""
    dsn = f"postgresql://{test_db_config.user}:{test_db_config.password}@{test_db_config.host}:{test_db_config.port}/{test_db_config.dbname}"
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def cleanup_test_tables(db_connection):
    """Clean up test tables before and after each test."""
    cursor = db_connection.cursor()

    # Cleanup before test
    try:
        cursor.execute("DROP TABLE IF EXISTS public.test_table_phase10 CASCADE")
        cursor.execute("DROP TABLE IF EXISTS public.users_test CASCADE")
        cursor.execute("DROP TABLE IF EXISTS public.orders_test CASCADE")
    except Exception:
        pass

    yield

    # Cleanup after test
    try:
        cursor.execute("DROP TABLE IF EXISTS public.test_table_phase10 CASCADE")
        cursor.execute("DROP TABLE IF EXISTS public.users_test CASCADE")
        cursor.execute("DROP TABLE IF EXISTS public.orders_test CASCADE")
    except Exception:
        pass

    cursor.close()


class TestEREditDDLExecution:
    """Test ER edit actions execute DDL against the database."""

    def test_add_table_creates_in_database(self, client, db_connection):
        """Test that adding a table via ER edit creates it in the database."""
        # Arrange
        er_actions = {
            "actions": [
                {
                    "type": "add_table",
                    "name": "test_table_phase10",
                    "schema": "public"
                }
            ]
        }

        # Act
        response = client.post("/api/schema/er-edit", json=er_actions)

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify table exists in database
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'test_table_phase10'
            )
        """)
        exists = cursor.fetchone()[0]
        cursor.close()

        assert exists is True, "Table should exist in database after ER edit"

    def test_add_column_creates_in_database(self, client, db_connection):
        """Test that adding a column via ER edit creates it in the database."""
        # Arrange - First create a table
        cursor = db_connection.cursor()
        cursor.execute("CREATE TABLE public.test_table_phase10 (id serial PRIMARY KEY)")
        cursor.close()
        clear_schema_cache()

        er_actions = {
            "actions": [
                {
                    "type": "add_column",
                    "table": "public.test_table_phase10",
                    "column": {
                        "name": "test_column",
                        "type": "text",
                        "nullable": True,
                        "is_pk": False,
                        "is_fk": False
                    }
                }
            ]
        }

        # Act
        response = client.post("/api/schema/er-edit", json=er_actions)

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify column exists in database
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'test_table_phase10'
                AND column_name = 'test_column'
            )
        """)
        exists = cursor.fetchone()[0]
        cursor.close()

        assert exists is True, "Column should exist in database after ER edit"

    def test_created_table_is_queryable(self, client, db_connection):
        """Test that tables created via ER edit can be queried."""
        # Arrange & Act - Create table via ER edit
        er_actions = {
            "actions": [
                {
                    "type": "add_table",
                    "name": "users_test",
                    "schema": "public"
                },
                {
                    "type": "add_column",
                    "table": "public.users_test",
                    "column": {
                        "name": "id",
                        "type": "serial",
                        "nullable": False,
                        "is_pk": True,
                        "is_fk": False
                    }
                },
                {
                    "type": "add_column",
                    "table": "public.users_test",
                    "column": {
                        "name": "username",
                        "type": "text",
                        "nullable": False,
                        "is_pk": False,
                        "is_fk": False
                    }
                }
            ]
        }
        response = client.post("/api/schema/er-edit", json=er_actions)
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Insert data to verify table is functional
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO public.users_test (username) VALUES ('testuser')")
        cursor.execute("SELECT username FROM public.users_test WHERE id = 1")
        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == "testuser"


class TestDDLEditExecution:
    """Test DDL edit endpoint executes against the database."""

    def test_create_table_ddl_executes(self, client, db_connection):
        """Test that DDL for CREATE TABLE is executed against the database."""
        # Arrange
        ddl = """
        CREATE TABLE public.test_table_phase10 (
            id serial PRIMARY KEY,
            name text NOT NULL,
            created_at timestamp DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Act
        response = client.post("/api/schema/ddl-edit", json={"ddl": ddl})

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify table exists
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'test_table_phase10'
            )
        """)
        exists = cursor.fetchone()[0]
        cursor.close()

        assert exists is True

    def test_ddl_created_table_is_queryable(self, client, db_connection):
        """Test that tables created via DDL edit can be queried."""
        # Arrange & Act
        ddl = """
        CREATE TABLE public.users_test (
            id serial PRIMARY KEY,
            email text NOT NULL
        )
        """
        response = client.post("/api/schema/ddl-edit", json={"ddl": ddl})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Insert and query data
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO public.users_test (email) VALUES ('test@example.com')")
        cursor.execute("SELECT email FROM public.users_test WHERE id = 1")
        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == "test@example.com"

    def test_invalid_ddl_returns_error(self, client):
        """Test that invalid DDL returns an error without breaking the system."""
        # Arrange
        invalid_ddl = "CREATE TABL public.bad_syntax"  # Missing 'E' in TABLE

        # Act
        response = client.post("/api/schema/ddl-edit", json={"ddl": invalid_ddl})

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is False
        assert "error" in response_data


class TestSchemaRefreshAfterEdits:
    """Test that schema is refreshed from database after edits."""

    def test_er_edit_refreshes_schema(self, client):
        """Test that ER edit returns refreshed schema from database."""
        # Act - Create table with a column via ER edit (empty tables may not introspect well)
        er_actions = {
            "actions": [
                {
                    "type": "add_table",
                    "name": "test_table_phase10",
                    "schema": "public"
                },
                {
                    "type": "add_column",
                    "table": "public.test_table_phase10",
                    "column": {
                        "name": "id",
                        "type": "serial",
                        "nullable": False,
                        "is_pk": True,
                        "is_fk": False
                    }
                }
            ]
        }
        response = client.post("/api/schema/er-edit", json=er_actions)

        # Assert - Response should include the table from database
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True

        # Check that schema includes the new table
        schema = response_data["schema"]
        table_names = [t["name"] for t in schema["tables"]]
        assert "test_table_phase10" in table_names

    def test_ddl_edit_refreshes_schema(self, client):
        """Test that DDL edit returns refreshed schema from database."""
        # Act
        ddl = "CREATE TABLE public.test_table_phase10 (id serial PRIMARY KEY)"
        response = client.post("/api/schema/ddl-edit", json={"ddl": ddl})

        # Assert
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True

        # Check that schema includes the new table
        schema = response_data["schema"]
        table_names = [t["name"] for t in schema["tables"]]
        assert "test_table_phase10" in table_names


class TestTransactionRollback:
    """Test that failed DDL executions rollback properly."""

    def test_er_edit_invalid_action_does_not_affect_db(self, client, db_connection):
        """Test that validation errors prevent any database changes."""
        # Arrange - Try to add a column to a non-existent table
        er_actions = {
            "actions": [
                {
                    "type": "add_column",
                    "table": "public.nonexistent_table",
                    "column": {
                        "name": "bad_column",
                        "type": "text",
                        "nullable": True,
                        "is_pk": False,
                        "is_fk": False
                    }
                }
            ]
        }

        # Act
        response = client.post("/api/schema/er-edit", json=er_actions)

        # Assert - Should fail validation before reaching the database
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is False
        assert "errors" in response_data

    def test_ddl_syntax_error_does_not_affect_db(self, client, db_connection):
        """Test that DDL syntax errors don't leave the database in a bad state."""
        # Arrange - First create a valid table
        cursor = db_connection.cursor()
        cursor.execute("CREATE TABLE public.test_table_phase10 (id serial PRIMARY KEY)")
        cursor.close()
        clear_schema_cache()

        # Act - Try to run invalid DDL
        invalid_ddl = "ALTER TABLE public.test_table_phase10 ADD COLUMN bad syntax error"
        response = client.post("/api/schema/ddl-edit", json={"ddl": invalid_ddl})

        # Assert - Should fail
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is False

        # Verify original table is unchanged
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'test_table_phase10'
            AND table_schema = 'public'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        cursor.close()

        # Should only have the original 'id' column
        assert columns == ["id"]
