import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import psycopg2

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.db import DatabaseConfig
from app.routes.config import update_db_credentials


def make_connection(schemas=None):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)
    cursor.fetchall.return_value = [(schema,) for schema in (schemas or [])]
    conn.cursor.return_value = cursor
    return conn, cursor


def make_admin_connection():
    admin_conn = MagicMock()
    admin_cursor = MagicMock()
    admin_conn.cursor.return_value.__enter__.return_value = admin_cursor
    admin_conn.cursor.return_value.__exit__.return_value = False
    return admin_conn, admin_cursor


def test_update_password_only_uses_parameterized_query():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="schemasense_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="schemasense_user", password="new_pw"
    )

    primary_conn, primary_cursor = make_connection()
    verify_conn, _ = make_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]):

        response = update_db_credentials(new_config)

    assert response["success"] is True
    assert len(primary_cursor.execute.call_args_list) >= 2

    alter_call = primary_cursor.execute.call_args_list[1]
    assert "ALTER USER" in alter_call.args[0]
    assert alter_call.args[1] == (new_config.password,)

    mock_set_config.assert_called_with(new_config)
    mock_clear_cache.assert_called_once()
    # No CREATE USER should be issued for password-only change
    assert not any("CREATE USER" in call.args[0] for call in primary_cursor.execute.call_args_list)


def test_update_credentials_changes_username_and_drops_old_user():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="new_pw"
    )

    primary_conn, primary_cursor = make_connection(schemas=["public", "sales"])
    verify_conn, _ = make_connection()
    admin_conn, admin_cursor = make_admin_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]), \
         patch("app.routes.config.get_settings",
               return_value=type("Settings", (), {"managed_pg_admin_dsn": "postgresql://admin:pw@localhost:5432/postgres"})), \
         patch("app.routes.config.psycopg2.connect", return_value=admin_conn) as mock_admin_connect, \
         patch("time.sleep"):

        response = update_db_credentials(new_config)

    assert response["success"] is True

    sql_calls = [call.args[0] for call in primary_cursor.execute.call_args_list]
    assert any("CREATE USER new_user" in stmt for stmt in sql_calls)
    assert any("GRANT ALL PRIVILEGES ON DATABASE testdb TO new_user" in stmt for stmt in sql_calls)
    assert any("GRANT ALL PRIVILEGES ON SCHEMA public TO new_user" in stmt for stmt in sql_calls)

    admin_calls = [call.args[0] for call in admin_cursor.execute.call_args_list]
    assert any("REASSIGN OWNED BY old_user TO new_user" in stmt for stmt in admin_calls)
    assert any("DROP USER old_user" in stmt for stmt in admin_calls)

    mock_admin_connect.assert_called_once()
    mock_set_config.assert_called_with(new_config)
    mock_clear_cache.assert_called_once()
    # Ensure grants executed for each schema returned
    for schema in ["public", "sales"]:
        assert any(f"GRANT ALL PRIVILEGES ON SCHEMA {schema} TO new_user" in stmt for stmt in sql_calls)


def test_update_credentials_rejects_malicious_username():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="safe_user", password="old_pw"
    )
    malicious_config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="testdb",
        user="bad_user; DROP ROLE admin;--",
        password="pw",
    )

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection") as mock_get_connection:

        response = update_db_credentials(malicious_config)

    assert response["success"] is False
    assert "invalid username" in response["message"].lower()
    mock_get_connection.assert_not_called()
    mock_set_config.assert_called_with(old_config)
    mock_clear_cache.assert_not_called()


def test_update_credentials_rejects_username_format():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="safe_user", password="old_pw"
    )
    bad_format_config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="testdb",
        user="123invalid",
        password="pw",
    )

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection") as mock_get_connection:

        response = update_db_credentials(bad_format_config)

    assert response["success"] is False
    assert "invalid username" in response["message"].lower()
    mock_get_connection.assert_not_called()
    mock_set_config.assert_called_with(old_config)
    mock_clear_cache.assert_not_called()


def test_update_credentials_rejects_username_too_long():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="safe_user", password="old_pw"
    )
    long_username = "a" + ("b" * 80)
    bad_config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="testdb",
        user=long_username,
        password="pw",
    )

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection") as mock_get_connection:

        response = update_db_credentials(bad_config)

    assert response["success"] is False
    assert "invalid username" in response["message"].lower()
    mock_get_connection.assert_not_called()
    mock_set_config.assert_called_with(old_config)
    mock_clear_cache.assert_not_called()


def test_update_credentials_returns_permission_error_for_create_role():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="new_pw"
    )

    failing_conn, failing_cursor = make_connection()
    failing_cursor.execute.side_effect = [None, Exception("permission denied to create role")]

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", return_value=failing_conn):

        response = update_db_credentials(new_config)

    assert response["success"] is False
    assert "permission" in response["message"].lower()
    assert response["error"] == "permission denied to create role"

    mock_set_config.assert_called_with(old_config)
    mock_clear_cache.assert_not_called()


def test_update_credentials_requires_existing_connection():
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="new_pw"
    )

    with patch("app.routes.config.get_database_config", return_value=None), \
         patch("app.routes.config.get_connection") as mock_get_connection, \
         patch("app.routes.config.set_database_config") as mock_set_config:

        response = update_db_credentials(new_config)

    assert response["success"] is False
    assert "no existing connection" in response["message"].lower()
    mock_get_connection.assert_not_called()
    mock_set_config.assert_not_called()


def test_update_credentials_rolls_back_if_new_connection_fails():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="new_pw"
    )

    primary_conn, primary_cursor = make_connection()
    # First get_connection for current creds succeeds, second (verification) fails
    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, RuntimeError("verify failed")]):

        response = update_db_credentials(new_config)

    assert response["success"] is False
    assert "failed to update credentials" in response["message"].lower()
    # Should have restored old config on failure
    mock_set_config.assert_called_with(old_config)
    mock_clear_cache.assert_not_called()
    # Verify password change attempt happened before failure
    assert any("CREATE USER new_user" in call.args[0] for call in primary_cursor.execute.call_args_list)


def test_update_credentials_admin_dsn_parsing_for_cleanup():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="new_pw"
    )

    primary_conn, primary_cursor = make_connection()
    verify_conn, _ = make_connection()
    admin_conn, admin_cursor = make_admin_connection()

    admin_dsn = "postgresql://admin:pw@admin-host:6543/postgres"

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config"), \
         patch("app.routes.config.clear_schema_cache"), \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]), \
         patch("app.routes.config.get_settings", return_value=type("Settings", (), {"managed_pg_admin_dsn": admin_dsn})), \
         patch("app.routes.config.psycopg2.connect", return_value=admin_conn) as mock_admin_connect, \
         patch("time.sleep"):

        response = update_db_credentials(new_config)

    assert response["success"] is True
    # Should have built a DSN that swaps in the target dbname but keeps admin creds/host/port
    mock_admin_connect.assert_called_with("postgresql://admin:pw@admin-host:6543/testdb")
    # Ensure cleanup statements executed in admin cursor (drop old user etc.)
    admin_calls = [call.args[0] for call in admin_cursor.execute.call_args_list]
    assert any("DROP USER old_user" in stmt for stmt in admin_calls)


def test_admin_cleanup_failure_is_non_fatal():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="new_pw"
    )

    primary_conn, primary_cursor = make_connection(schemas=["public"])
    verify_conn, _ = make_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]), \
         patch("app.routes.config.get_settings",
               return_value=type("Settings", (), {"managed_pg_admin_dsn": "postgresql://admin:pw@localhost:5432/postgres"})), \
         patch("app.routes.config.psycopg2.connect", side_effect=psycopg2.OperationalError("admin down")):

        response = update_db_credentials(new_config)

    assert response["success"] is True
    mock_set_config.assert_called_with(new_config)
    mock_clear_cache.assert_called_once()
    # Admin connect failure should not stop GRANT path
    sql_calls = [call.args[0] for call in primary_cursor.execute.call_args_list]
    assert any("CREATE USER new_user" in stmt for stmt in sql_calls)


def test_grant_failure_rolls_back_and_restores_old_config():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="new_pw"
    )

    primary_conn, primary_cursor = make_connection(schemas=["public"])
    primary_cursor.execute.side_effect = [
        None,  # SELECT 1
        None,  # CREATE USER
        None,  # GRANT ALL PRIVILEGES ON DATABASE
        None,  # SELECT schemas
        Exception("grant failed"),  # first schema grant
    ]

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", return_value=primary_conn), \
         patch("app.routes.config.get_settings",
               return_value=type("Settings", (), {"managed_pg_admin_dsn": "postgresql://admin:pw@localhost:5432/postgres"})), \
         patch("app.routes.config.psycopg2.connect") as mock_admin_connect:

        response = update_db_credentials(new_config)

    assert response["success"] is False
    assert "failed to update credentials" in response["message"].lower()
    mock_set_config.assert_called_with(old_config)
    mock_clear_cache.assert_not_called()
    mock_admin_connect.assert_not_called()


def test_password_change_escapes_password_value():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="schemasense_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost",
        port=5432,
        dbname="testdb",
        user="schemasense_user",
        password="pa$$w0rd'); DROP TABLE users;--",
    )

    primary_conn, primary_cursor = make_connection()
    verify_conn, _ = make_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config"), \
         patch("app.routes.config.clear_schema_cache"), \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]):

        response = update_db_credentials(new_config)

    assert response["success"] is True
    alter_call = primary_cursor.execute.call_args_list[1]
    assert alter_call.args[1] == (new_config.password,)


def test_username_change_applies_privileges_to_all_objects_and_defaults():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="pw"
    )

    primary_conn, primary_cursor = make_connection(schemas=["public", "sales"])
    verify_conn, _ = make_connection()
    admin_conn, _ = make_admin_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config"), \
         patch("app.routes.config.clear_schema_cache"), \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]), \
         patch("app.routes.config.get_settings",
               return_value=type("Settings", (), {"managed_pg_admin_dsn": "postgresql://admin:pw@localhost:5432/postgres"})), \
         patch("app.routes.config.psycopg2.connect", return_value=admin_conn), \
         patch("time.sleep"):

        response = update_db_credentials(new_config)

    assert response["success"] is True

    sql_calls = [call.args[0] for call in primary_cursor.execute.call_args_list]
    assert any("GRANT ALL PRIVILEGES ON DATABASE testdb TO new_user" in stmt for stmt in sql_calls)
    for schema in ["public", "sales"]:
        assert any(f"GRANT ALL PRIVILEGES ON SCHEMA {schema} TO new_user" in stmt for stmt in sql_calls)
        assert any(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} TO new_user" in stmt for stmt in sql_calls)
        assert any(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema} TO new_user" in stmt for stmt in sql_calls)
        assert any(f"GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA {schema} TO new_user" in stmt for stmt in sql_calls)
        assert any(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON TABLES TO new_user" in stmt
            for stmt in sql_calls
        )
        assert any(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON SEQUENCES TO new_user" in stmt
            for stmt in sql_calls
        )
        assert any(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON FUNCTIONS TO new_user" in stmt
            for stmt in sql_calls
        )


def test_admin_cleanup_sequence_terminates_and_reassigns_before_drop():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="pw"
    )

    primary_conn, _ = make_connection(schemas=["public"])
    verify_conn, _ = make_connection()
    admin_conn, admin_cursor = make_admin_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config"), \
         patch("app.routes.config.clear_schema_cache"), \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]), \
         patch("app.routes.config.get_settings",
               return_value=type("Settings", (), {"managed_pg_admin_dsn": "postgresql://admin:pw@localhost:5432/postgres"})), \
         patch("app.routes.config.psycopg2.connect", return_value=admin_conn), \
         patch("time.sleep"):

        response = update_db_credentials(new_config)

    assert response["success"] is True
    assert admin_conn.autocommit is True

    admin_calls = admin_cursor.execute.call_args_list
    assert "pg_terminate_backend" in admin_calls[0].args[0]
    assert admin_calls[0].args[1] == (old_config.user, new_config.dbname)
    assert "REASSIGN OWNED BY old_user TO new_user" in admin_calls[1].args[0]
    assert "DROP OWNED BY old_user" in admin_calls[2].args[0]
    assert "DROP USER old_user" in admin_calls[3].args[0]


def test_username_change_without_password_change_skips_alter_user():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="old_user", password="shared_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="new_user", password="shared_pw"
    )

    primary_conn, primary_cursor = make_connection(schemas=["public"])
    verify_conn, _ = make_connection()
    admin_conn, _ = make_admin_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]), \
         patch("app.routes.config.get_settings",
               return_value=type("Settings", (), {"managed_pg_admin_dsn": "postgresql://admin:pw@localhost:5432/postgres"})), \
         patch("app.routes.config.psycopg2.connect", return_value=admin_conn), \
         patch("time.sleep"):

        response = update_db_credentials(new_config)

    assert response["success"] is True
    assert mock_set_config.called
    mock_clear_cache.assert_called_once()

    sql_calls = primary_cursor.execute.call_args_list
    create_call = sql_calls[1]
    assert "CREATE USER new_user" in create_call.args[0]
    assert create_call.args[1] == (new_config.password,)
    assert not any("ALTER USER" in call.args[0] for call in sql_calls)


def test_password_change_does_not_trigger_admin_connection():
    old_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="schemasense_user", password="old_pw"
    )
    new_config = DatabaseConfig(
        host="localhost", port=5432, dbname="testdb", user="schemasense_user", password="new_pw"
    )

    primary_conn, primary_cursor = make_connection()
    verify_conn, _ = make_connection()

    with patch("app.routes.config.get_database_config", return_value=old_config), \
         patch("app.routes.config.set_database_config") as mock_set_config, \
         patch("app.routes.config.clear_schema_cache") as mock_clear_cache, \
         patch("app.routes.config.get_connection", side_effect=[primary_conn, verify_conn]), \
         patch("app.routes.config.psycopg2.connect") as mock_admin_connect:

        response = update_db_credentials(new_config)

    assert response["success"] is True
    alter_call = primary_cursor.execute.call_args_list[1]
    assert "ALTER USER schemasense_user" in alter_call.args[0]
    assert mock_set_config.called
    mock_clear_cache.assert_called_once()
    mock_admin_connect.assert_not_called()
