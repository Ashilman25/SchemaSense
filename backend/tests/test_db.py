"""
Tests for backend/app/db.py — Redis-backed session DB config storage,
in-memory fallback, DSN building, and connection management.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.db import (
    DatabaseConfig,
    set_database_config,
    get_database_config,
    build_dsn,
    get_connection,
    _session_configs,
    REDIS_KEY_PREFIX,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_config(**overrides) -> DatabaseConfig:
    """Create a DatabaseConfig with sensible defaults, overridable per-field."""
    defaults = {
        "host": "db.example.com",
        "port": 5432,
        "dbname": "testdb",
        "user": "testuser",
        "password": "testpass",
    }
    defaults.update(overrides)
    return DatabaseConfig(**defaults)


def _expected_key(session_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}:{session_id}:db_config"


@pytest.fixture(autouse=True)
def clear_in_memory_cache():
    """Ensure _session_configs is empty before and after each test."""
    _session_configs.clear()
    yield
    _session_configs.clear()


# ---------------------------------------------------------------------------
# DatabaseConfig model tests
# ---------------------------------------------------------------------------

class TestDatabaseConfig:
    """Verify the Pydantic model behaves correctly."""

    def test_defaults(self):
        """Default values are populated when no args given."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.dbname == "schemasense"
        assert config.user == "schemasense"
        assert config.password == "schemasense_dev"

    def test_custom_values(self):
        """All fields are overridable."""
        config = _sample_config()
        assert config.host == "db.example.com"
        assert config.dbname == "testdb"

    def test_model_dump_round_trip(self):
        """model_dump() produces a dict that can reconstruct the same model."""
        original = _sample_config()
        dumped = original.model_dump()
        reconstructed = DatabaseConfig(**dumped)
        assert reconstructed == original

    def test_model_dump_keys(self):
        """model_dump() contains exactly the expected keys."""
        config = _sample_config()
        keys = set(config.model_dump().keys())
        assert keys == {"host", "port", "dbname", "user", "password"}


# ---------------------------------------------------------------------------
# set_database_config tests
# ---------------------------------------------------------------------------

class TestSetDatabaseConfig:
    """Test storing and deleting session DB config via Redis + fallback."""

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_stores_to_redis_with_correct_key(self, mock_settings, mock_redis):
        """Calls set_response with the namespaced key pattern."""
        mock_settings.session_max_age_days = 7
        mock_redis.set_response.return_value = {"status": 1}
        config = _sample_config()

        set_database_config(config, "sess-001")

        expected_key = _expected_key("sess-001")
        mock_redis.set_response.assert_called_once_with(
            expected_key, config.model_dump(), ttl_seconds=7 * 86400
        )

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_ttl_aligned_with_session_max_age(self, mock_settings, mock_redis):
        """TTL is session_max_age_days converted to seconds."""
        mock_settings.session_max_age_days = 30
        mock_redis.set_response.return_value = {"status": 1}

        set_database_config(_sample_config(), "sess-002")

        _, kwargs = mock_redis.set_response.call_args
        assert kwargs["ttl_seconds"] == 30 * 86400

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_stores_to_in_memory_fallback(self, mock_settings, mock_redis):
        """Config is always written to _session_configs as fallback."""
        mock_settings.session_max_age_days = 1
        mock_redis.set_response.return_value = {"status": 1}
        config = _sample_config()

        set_database_config(config, "sess-003")

        assert _session_configs["sess-003"] == config

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_redis_failure_still_stores_in_memory(self, mock_settings, mock_redis):
        """When Redis fails (status 0), config is still stored in memory."""
        mock_settings.session_max_age_days = 1
        mock_redis.set_response.return_value = {"status": 0}
        config = _sample_config()

        set_database_config(config, "sess-004")

        assert _session_configs["sess-004"] == config

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_serializes_via_model_dump(self, mock_settings, mock_redis):
        """The value stored in Redis is the model_dump() dict."""
        mock_settings.session_max_age_days = 1
        mock_redis.set_response.return_value = {"status": 1}
        config = _sample_config(host="custom-host", password="s3cret")

        set_database_config(config, "sess-005")

        stored_value = mock_redis.set_response.call_args[0][1]
        assert stored_value["host"] == "custom-host"
        assert stored_value["password"] == "s3cret"
        assert isinstance(stored_value, dict)

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_none_deletes_from_redis(self, mock_settings, mock_redis):
        """Passing config=None calls delete_key on Redis."""
        mock_settings.session_max_age_days = 1
        mock_redis.delete_key.return_value = {"status": 1}

        set_database_config(None, "sess-006")

        expected_key = _expected_key("sess-006")
        mock_redis.delete_key.assert_called_once_with(expected_key)

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_none_removes_from_in_memory(self, mock_settings, mock_redis):
        """Passing config=None also removes from _session_configs."""
        mock_settings.session_max_age_days = 1
        mock_redis.delete_key.return_value = {"status": 1}
        _session_configs["sess-007"] = _sample_config()

        set_database_config(None, "sess-007")

        assert "sess-007" not in _session_configs

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_none_nonexistent_session_no_error(self, mock_settings, mock_redis):
        """Deleting a session that doesn't exist in memory doesn't raise."""
        mock_settings.session_max_age_days = 1
        mock_redis.delete_key.return_value = {"status": 1}

        set_database_config(None, "nonexistent-session")

        assert "nonexistent-session" not in _session_configs

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_overwrites_existing_config(self, mock_settings, mock_redis):
        """Setting config for an existing session overwrites the old value."""
        mock_settings.session_max_age_days = 1
        mock_redis.set_response.return_value = {"status": 1}

        old_config = _sample_config(dbname="old_db")
        new_config = _sample_config(dbname="new_db")

        set_database_config(old_config, "sess-008")
        set_database_config(new_config, "sess-008")

        assert _session_configs["sess-008"].dbname == "new_db"


# ---------------------------------------------------------------------------
# get_database_config tests
# ---------------------------------------------------------------------------

class TestGetDatabaseConfig:
    """Test reading session DB config from Redis with in-memory fallback."""

    @patch("app.db.redis_client")
    def test_get_from_redis_cache_hit(self, mock_redis):
        """Returns DatabaseConfig from Redis when cache hit (status 1)."""
        config_data = _sample_config().model_dump()
        mock_redis.get_response.return_value = {"status": 1, "data": config_data}

        result = get_database_config("sess-010")

        assert isinstance(result, DatabaseConfig)
        assert result.host == "db.example.com"
        assert result.dbname == "testdb"

    @patch("app.db.redis_client")
    def test_get_uses_correct_key(self, mock_redis):
        """get_database_config queries Redis with the namespaced key."""
        mock_redis.get_response.return_value = {"status": 0}

        get_database_config("sess-011")

        expected_key = _expected_key("sess-011")
        mock_redis.get_response.assert_called_once_with(expected_key)

    @patch("app.db.redis_client")
    def test_get_returns_database_config_not_dict(self, mock_redis):
        """Return type is DatabaseConfig, not a raw dict."""
        config_data = _sample_config().model_dump()
        mock_redis.get_response.return_value = {"status": 1, "data": config_data}

        result = get_database_config("sess-012")

        assert isinstance(result, DatabaseConfig)
        assert not isinstance(result, dict)

    @patch("app.db.redis_client")
    def test_get_falls_back_to_memory_on_redis_miss(self, mock_redis):
        """Falls back to _session_configs when Redis returns status 0."""
        mock_redis.get_response.return_value = {"status": 0}
        fallback_config = _sample_config(dbname="fallback_db")
        _session_configs["sess-013"] = fallback_config

        result = get_database_config("sess-013")

        assert result == fallback_config
        assert result.dbname == "fallback_db"

    @patch("app.db.redis_client")
    def test_get_returns_none_when_no_redis_and_no_memory(self, mock_redis):
        """Returns None when both Redis miss and no in-memory entry."""
        mock_redis.get_response.return_value = {"status": 0}

        result = get_database_config("nonexistent-session")

        assert result is None

    @patch("app.db.redis_client")
    def test_get_prefers_redis_over_memory(self, mock_redis):
        """Redis value takes priority over in-memory fallback."""
        redis_config = _sample_config(dbname="redis_db").model_dump()
        mock_redis.get_response.return_value = {"status": 1, "data": redis_config}
        _session_configs["sess-014"] = _sample_config(dbname="memory_db")

        result = get_database_config("sess-014")

        assert result.dbname == "redis_db"

    @patch("app.db.redis_client")
    def test_get_reconstructs_all_fields(self, mock_redis):
        """All fields from Redis are correctly deserialized."""
        config_data = {
            "host": "prod.db.com",
            "port": 5433,
            "dbname": "production",
            "user": "admin",
            "password": "pr0d_p@ss!",
        }
        mock_redis.get_response.return_value = {"status": 1, "data": config_data}

        result = get_database_config("sess-015")

        assert result.host == "prod.db.com"
        assert result.port == 5433
        assert result.dbname == "production"
        assert result.user == "admin"
        assert result.password == "pr0d_p@ss!"

    @patch("app.db.redis_client")
    def test_get_different_sessions_return_different_configs(self, mock_redis):
        """Each session_id maps to its own config."""
        mock_redis.get_response.return_value = {"status": 0}
        _session_configs["sess-A"] = _sample_config(dbname="db_a")
        _session_configs["sess-B"] = _sample_config(dbname="db_b")

        result_a = get_database_config("sess-A")
        result_b = get_database_config("sess-B")

        assert result_a.dbname == "db_a"
        assert result_b.dbname == "db_b"


# ---------------------------------------------------------------------------
# set + get integration tests (mocked Redis)
# ---------------------------------------------------------------------------

class TestSetGetIntegration:
    """Test set_database_config -> get_database_config round trips."""

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_then_get_via_redis(self, mock_settings, mock_redis):
        """Config set via Redis is retrievable via Redis."""
        mock_settings.session_max_age_days = 1
        config = _sample_config(dbname="round_trip_db")

        mock_redis.set_response.return_value = {"status": 1}
        set_database_config(config, "sess-020")

        mock_redis.get_response.return_value = {
            "status": 1,
            "data": config.model_dump(),
        }
        result = get_database_config("sess-020")

        assert result == config

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_then_get_via_fallback_when_redis_down(self, mock_settings, mock_redis):
        """Config retrievable from memory when Redis is down for both set and get."""
        mock_settings.session_max_age_days = 1
        config = _sample_config(dbname="fallback_db")

        mock_redis.set_response.return_value = {"status": 0}
        set_database_config(config, "sess-021")

        mock_redis.get_response.return_value = {"status": 0}
        result = get_database_config("sess-021")

        assert result == config

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_none_then_get_returns_none(self, mock_settings, mock_redis):
        """After deleting config, get returns None."""
        mock_settings.session_max_age_days = 1
        config = _sample_config()

        mock_redis.set_response.return_value = {"status": 1}
        set_database_config(config, "sess-022")

        mock_redis.delete_key.return_value = {"status": 1}
        set_database_config(None, "sess-022")

        mock_redis.get_response.return_value = {"status": 0}
        result = get_database_config("sess-022")

        assert result is None

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_overwrite_config_returns_latest(self, mock_settings, mock_redis):
        """Overwriting a config returns the latest version."""
        mock_settings.session_max_age_days = 1
        mock_redis.set_response.return_value = {"status": 1}

        set_database_config(_sample_config(dbname="old"), "sess-023")
        new_config = _sample_config(dbname="new")
        set_database_config(new_config, "sess-023")

        mock_redis.get_response.return_value = {
            "status": 1,
            "data": new_config.model_dump(),
        }
        result = get_database_config("sess-023")

        assert result.dbname == "new"

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_multiple_sessions_isolated(self, mock_settings, mock_redis):
        """Different sessions have independent configs."""
        mock_settings.session_max_age_days = 1
        mock_redis.set_response.return_value = {"status": 1}

        config_a = _sample_config(dbname="db_a")
        config_b = _sample_config(dbname="db_b")
        set_database_config(config_a, "sess-A")
        set_database_config(config_b, "sess-B")

        mock_redis.get_response.return_value = {"status": 0}
        result_a = get_database_config("sess-A")
        result_b = get_database_config("sess-B")

        assert result_a.dbname == "db_a"
        assert result_b.dbname == "db_b"


# ---------------------------------------------------------------------------
# build_dsn tests
# ---------------------------------------------------------------------------

class TestBuildDsn:
    """Test DSN string construction from DatabaseConfig."""

    def test_basic_dsn(self):
        """Builds correct DSN from standard config."""
        config = _sample_config()
        dsn = build_dsn(config)

        assert dsn == "postgresql://testuser:testpass@db.example.com:5432/testdb"

    def test_dsn_with_default_config(self):
        """Builds correct DSN from default config values."""
        config = DatabaseConfig()
        dsn = build_dsn(config)

        assert dsn == "postgresql://schemasense:schemasense_dev@localhost:5432/schemasense"

    def test_dsn_encodes_special_chars_in_password(self):
        """Special characters in password are URL-encoded."""
        config = _sample_config(password="p@ss w0rd!#$")
        dsn = build_dsn(config)

        assert "p%40ss+w0rd%21%23%24" in dsn
        assert "p@ss" not in dsn

    def test_dsn_encodes_special_chars_in_user(self):
        """Special characters in username are URL-encoded."""
        config = _sample_config(user="user@domain")
        dsn = build_dsn(config)

        assert "user%40domain" in dsn

    def test_dsn_custom_port(self):
        """Custom port is reflected in DSN."""
        config = _sample_config(port=5433)
        dsn = build_dsn(config)

        assert "@db.example.com:5433/" in dsn

    def test_dsn_format_structure(self):
        """DSN follows postgresql://user:pass@host:port/dbname format."""
        config = _sample_config()
        dsn = build_dsn(config)

        assert dsn.startswith("postgresql://")
        assert "@" in dsn
        assert ":" in dsn.split("@")[1]  # host:port
        assert "/" in dsn.split("@")[1]  # /dbname


# ---------------------------------------------------------------------------
# get_connection tests
# ---------------------------------------------------------------------------

class TestGetConnection:
    """Test database connection retrieval."""

    @patch("app.db.psycopg2.connect")
    @patch("app.db.get_database_config")
    def test_returns_connection_on_success(self, mock_get_config, mock_connect):
        """Returns a connection object when config exists and connect succeeds."""
        config = _sample_config()
        mock_get_config.return_value = config
        fake_conn = MagicMock()
        mock_connect.return_value = fake_conn

        conn = get_connection("sess-030")

        assert conn is fake_conn
        mock_connect.assert_called_once()

    @patch("app.db.psycopg2.connect")
    @patch("app.db.get_database_config")
    def test_passes_correct_dsn_to_connect(self, mock_get_config, mock_connect):
        """The DSN built from config is passed to psycopg2.connect."""
        config = _sample_config()
        mock_get_config.return_value = config
        mock_connect.return_value = MagicMock()

        get_connection("sess-031")

        expected_dsn = build_dsn(config)
        mock_connect.assert_called_once_with(expected_dsn)

    @patch("app.db.get_database_config")
    def test_raises_runtime_error_when_no_config(self, mock_get_config):
        """Raises RuntimeError when no config exists for session."""
        mock_get_config.return_value = None

        with pytest.raises(RuntimeError, match="db config not set for this session"):
            get_connection("nonexistent-session")

    @patch("app.db.psycopg2.connect")
    @patch("app.db.get_database_config")
    def test_raises_runtime_error_on_operational_error(self, mock_get_config, mock_connect):
        """Wraps psycopg2.OperationalError in RuntimeError with host info."""
        import psycopg2
        config = _sample_config()
        mock_get_config.return_value = config
        mock_connect.side_effect = psycopg2.OperationalError("connection refused")

        with pytest.raises(RuntimeError, match="Failed to connect to database"):
            get_connection("sess-032")

    @patch("app.db.psycopg2.connect")
    @patch("app.db.get_database_config")
    def test_operational_error_includes_host_info(self, mock_get_config, mock_connect):
        """RuntimeError message includes host, port, and dbname."""
        import psycopg2
        config = _sample_config(host="prod.db.com", port=5433, dbname="mydb")
        mock_get_config.return_value = config
        mock_connect.side_effect = psycopg2.OperationalError("timeout")

        with pytest.raises(RuntimeError, match="prod.db.com:5433/mydb"):
            get_connection("sess-033")

    @patch("app.db.psycopg2.connect")
    @patch("app.db.get_database_config")
    def test_raises_runtime_error_on_unexpected_exception(self, mock_get_config, mock_connect):
        """Wraps unexpected exceptions in RuntimeError."""
        config = _sample_config()
        mock_get_config.return_value = config
        mock_connect.side_effect = OSError("network unreachable")

        with pytest.raises(RuntimeError, match="Unexpected error connecting to database"):
            get_connection("sess-034")

    @patch("app.db.psycopg2.connect")
    @patch("app.db.get_database_config")
    def test_unexpected_error_does_not_leak_details(self, mock_get_config, mock_connect):
        """Unexpected error message does not include internal details."""
        config = _sample_config()
        mock_get_config.return_value = config
        mock_connect.side_effect = ValueError("some internal detail")

        with pytest.raises(RuntimeError) as exc_info:
            get_connection("sess-035")

        assert "some internal detail" not in str(exc_info.value)
        assert "Unexpected error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Key pattern tests
# ---------------------------------------------------------------------------

class TestKeyPattern:
    """Verify Redis key patterns match the ToDo spec."""

    def test_key_prefix_value(self):
        """REDIS_KEY_PREFIX matches expected namespace."""
        assert REDIS_KEY_PREFIX == "schemasense:session"

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_set_key_format(self, mock_settings, mock_redis):
        """set_database_config uses schemasense:session:{id}:db_config."""
        mock_settings.session_max_age_days = 1
        mock_redis.set_response.return_value = {"status": 1}

        set_database_config(_sample_config(), "abc-123")

        actual_key = mock_redis.set_response.call_args[0][0]
        assert actual_key == "schemasense:session:abc-123:db_config"

    @patch("app.db.redis_client")
    def test_get_key_format(self, mock_redis):
        """get_database_config queries with schemasense:session:{id}:db_config."""
        mock_redis.get_response.return_value = {"status": 0}

        get_database_config("xyz-789")

        actual_key = mock_redis.get_response.call_args[0][0]
        assert actual_key == "schemasense:session:xyz-789:db_config"

    @patch("app.db.redis_client")
    @patch("app.db.settings")
    def test_delete_key_format(self, mock_settings, mock_redis):
        """set_database_config(None) deletes with schemasense:session:{id}:db_config."""
        mock_settings.session_max_age_days = 1
        mock_redis.delete_key.return_value = {"status": 1}

        set_database_config(None, "del-456")

        actual_key = mock_redis.delete_key.call_args[0][0]
        assert actual_key == "schemasense:session:del-456:db_config"
