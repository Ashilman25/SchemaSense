"""
Tests for RedisClient functionality.
Uses unittest.mock to simulate Redis behavior without requiring a live Redis server.
Tests cover all methods, specific redis exception types, client-None guards,
return value shapes, and logging behavior.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest
import json
import redis as redis_lib

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.cache.redis_client import RedisClient


# ---------------------------------------------------------------------------
# Helpers: fake Settings objects for __init__ tests
# ---------------------------------------------------------------------------

def _make_settings(redis_enabled=True, redis_url="redis://localhost:6379"):
    s = MagicMock()
    s.redis_enabled = redis_enabled
    s.redis_url = redis_url
    return s


def _make_disabled_client():
    """Helper to create a RedisClient with client=None (Redis disabled)."""
    with patch("app.cache.redis_client.get_settings") as mock_settings:
        mock_settings.return_value = _make_settings(redis_enabled=False)
        return RedisClient()


# ---------------------------------------------------------------------------
# __init__ tests
# ---------------------------------------------------------------------------

class TestRedisClientInit:
    """Verify that RedisClient initializes correctly under all config combos."""

    @patch("app.cache.redis_client.redis.from_url")
    @patch("app.cache.redis_client.get_settings")
    def test_init_enabled_with_url(self, mock_settings, mock_from_url):
        """Client is created when redis_enabled=True and redis_url is set."""
        mock_settings.return_value = _make_settings(redis_enabled=True, redis_url="redis://localhost:6379")
        fake_redis = MagicMock()
        mock_from_url.return_value = fake_redis

        client = RedisClient()

        mock_from_url.assert_called_once_with("redis://localhost:6379")
        assert client.client is fake_redis

    @patch("app.cache.redis_client.redis.from_url")
    @patch("app.cache.redis_client.get_settings")
    def test_init_disabled(self, mock_settings, mock_from_url):
        """Client is None when redis_enabled=False."""
        mock_settings.return_value = _make_settings(redis_enabled=False, redis_url="redis://localhost:6379")

        client = RedisClient()

        mock_from_url.assert_not_called()
        assert client.client is None

    @patch("app.cache.redis_client.redis.from_url")
    @patch("app.cache.redis_client.get_settings")
    def test_init_no_url(self, mock_settings, mock_from_url):
        """Client is None when redis_url is None."""
        mock_settings.return_value = _make_settings(redis_enabled=True, redis_url=None)

        client = RedisClient()

        mock_from_url.assert_not_called()
        assert client.client is None

    @patch("app.cache.redis_client.redis.from_url")
    @patch("app.cache.redis_client.get_settings")
    def test_init_empty_url(self, mock_settings, mock_from_url):
        """Client is None when redis_url is empty string."""
        mock_settings.return_value = _make_settings(redis_enabled=True, redis_url="")

        client = RedisClient()

        mock_from_url.assert_not_called()
        assert client.client is None

    @patch("app.cache.redis_client.redis.from_url")
    @patch("app.cache.redis_client.get_settings")
    def test_init_disabled_and_no_url(self, mock_settings, mock_from_url):
        """Client is None when both disabled and no URL."""
        mock_settings.return_value = _make_settings(redis_enabled=False, redis_url=None)

        client = RedisClient()

        mock_from_url.assert_not_called()
        assert client.client is None

    @patch("app.cache.redis_client.redis.from_url")
    @patch("app.cache.redis_client.get_settings")
    def test_init_passes_full_url_to_from_url(self, mock_settings, mock_from_url):
        """The exact redis_url from settings is passed to redis.from_url."""
        url = "redis://default:secret@redis-11511.c14.us-east-1-2.ec2.cloud.redislabs.com:11511"
        mock_settings.return_value = _make_settings(redis_enabled=True, redis_url=url)
        mock_from_url.return_value = MagicMock()

        RedisClient()

        mock_from_url.assert_called_once_with(url)


# ---------------------------------------------------------------------------
# Fixture: build a RedisClient with a mocked internal Redis connection
# ---------------------------------------------------------------------------

@pytest.fixture
def redis_client():
    """Create a RedisClient with a mocked underlying redis connection."""
    with patch("app.cache.redis_client.get_settings") as mock_settings, \
         patch("app.cache.redis_client.redis.from_url") as mock_from_url:
        mock_settings.return_value = _make_settings()
        fake_redis = MagicMock()
        mock_from_url.return_value = fake_redis

        client = RedisClient()
        # Expose the fake so tests can configure return values
        client._fake = fake_redis
        return client


# ---------------------------------------------------------------------------
# get_response tests
# ---------------------------------------------------------------------------

class TestGetResponse:
    """Test cache read (get_response) behavior."""

    def test_cache_hit_returns_status_1_with_data(self, redis_client):
        """Returns status 1 and deserialized data on cache hit."""
        payload = {"query": "SELECT 1", "result": [1]}
        redis_client._fake.get.return_value = json.dumps(payload).encode()

        result = redis_client.get_response("test:key")

        assert result["status"] == 1
        assert result["data"] == payload
        redis_client._fake.get.assert_called_once_with("test:key")

    def test_cache_miss_returns_status_0_no_data_key(self, redis_client):
        """Returns status 0 and no 'data' key when key does not exist."""
        redis_client._fake.get.return_value = None

        result = redis_client.get_response("missing:key")

        assert result["status"] == 0
        assert "data" not in result

    def test_cache_hit_complex_nested_json(self, redis_client):
        """Handles deeply nested JSON payloads correctly."""
        payload = {
            "tables": {"public.users": {"columns": ["id", "name"]}},
            "relationships": [{"from": "orders", "to": "users"}],
            "metadata": {"count": 5, "nested": {"deep": True}},
        }
        redis_client._fake.get.return_value = json.dumps(payload).encode()

        result = redis_client.get_response("schema:abc123")

        assert result["status"] == 1
        assert result["data"]["tables"]["public.users"]["columns"] == ["id", "name"]
        assert result["data"]["metadata"]["nested"]["deep"] is True

    def test_redis_connection_error_returns_status_0(self, redis_client):
        """Fails safely on redis.ConnectionError."""
        redis_client._fake.get.side_effect = redis_lib.ConnectionError("Connection refused")

        result = redis_client.get_response("test:key")

        assert result["status"] == 0

    def test_redis_timeout_error_returns_status_0(self, redis_client):
        """Fails safely on redis.TimeoutError."""
        redis_client._fake.get.side_effect = redis_lib.TimeoutError("Read timed out")

        result = redis_client.get_response("test:key")

        assert result["status"] == 0

    def test_redis_response_error_is_not_caught(self, redis_client):
        """redis.ResponseError (bug in code) is NOT caught — should propagate."""
        redis_client._fake.get.side_effect = redis_lib.ResponseError("WRONGTYPE")

        with pytest.raises(redis_lib.ResponseError):
            redis_client.get_response("test:key")

    def test_redis_data_error_is_not_caught(self, redis_client):
        """redis.DataError (bad arguments) is NOT caught — should propagate."""
        redis_client._fake.get.side_effect = redis_lib.DataError("Invalid input")

        with pytest.raises(redis_lib.DataError):
            redis_client.get_response("test:key")

    def test_corrupted_json_returns_status_0(self, redis_client):
        """Fails safely when stored value is not valid JSON."""
        redis_client._fake.get.return_value = b"not-valid-json{{"

        result = redis_client.get_response("bad:json:key")

        assert result["status"] == 0

    def test_client_none_returns_status_0(self):
        """Fails safely when client is None (Redis disabled)."""
        client = _make_disabled_client()

        result = client.get_response("any:key")

        assert result["status"] == 0

    def test_client_none_does_not_call_redis(self):
        """When client is None, no Redis call is attempted."""
        client = _make_disabled_client()
        # If it tried to call self.client.get(), it would raise AttributeError
        # on None. The guard should prevent this.
        result = client.get_response("any:key")

        assert result == {"status": 0}

    @patch("app.cache.redis_client.logger")
    def test_connection_error_logs_warning(self, mock_logger, redis_client):
        """ConnectionError logs a warning (not error)."""
        redis_client._fake.get.side_effect = redis_lib.ConnectionError("refused")

        redis_client.get_response("test:key")

        mock_logger.warning.assert_called_once()
        assert "get_response" in str(mock_logger.warning.call_args)

    @patch("app.cache.redis_client.logger")
    def test_timeout_error_logs_warning(self, mock_logger, redis_client):
        """TimeoutError logs a warning (not error)."""
        redis_client._fake.get.side_effect = redis_lib.TimeoutError("timed out")

        redis_client.get_response("test:key")

        mock_logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# set_response tests
# ---------------------------------------------------------------------------

class TestSetResponse:
    """Test cache write (set_response) behavior."""

    def test_set_without_ttl(self, redis_client):
        """Stores JSON value with no expiry when ttl is None."""
        payload = {"sql": "SELECT * FROM users"}

        result = redis_client.set_response("test:key", payload)

        assert result["status"] == 1
        redis_client._fake.set.assert_called_once_with(
            "test:key", json.dumps(payload), ex=None
        )

    def test_set_with_ttl(self, redis_client):
        """Stores JSON value with the specified TTL."""
        payload = {"sql": "SELECT 1"}

        result = redis_client.set_response("test:key", payload, ttl_seconds=3600)

        assert result["status"] == 1
        redis_client._fake.set.assert_called_once_with(
            "test:key", json.dumps(payload), ex=3600
        )

    def test_set_with_zero_ttl(self, redis_client):
        """TTL of 0 is passed through (Redis treats 0 as immediate expiry)."""
        payload = {"data": "ephemeral"}

        result = redis_client.set_response("test:key", payload, ttl_seconds=0)

        assert result["status"] == 1
        redis_client._fake.set.assert_called_once_with(
            "test:key", json.dumps(payload), ex=0
        )

    def test_set_serializes_value_as_json(self, redis_client):
        """Value passed to Redis is a JSON string."""
        payload = {"nested": {"list": [1, 2, 3]}}

        redis_client.set_response("test:key", payload)

        actual_json_arg = redis_client._fake.set.call_args[0][1]
        assert json.loads(actual_json_arg) == payload

    def test_set_connection_error_returns_status_0(self, redis_client):
        """Fails safely on redis.ConnectionError."""
        redis_client._fake.set.side_effect = redis_lib.ConnectionError("Connection refused")

        result = redis_client.set_response("test:key", {"data": 1})

        assert result["status"] == 0

    def test_set_timeout_error_returns_status_0(self, redis_client):
        """Fails safely on redis.TimeoutError."""
        redis_client._fake.set.side_effect = redis_lib.TimeoutError("Write timed out")

        result = redis_client.set_response("test:key", {"data": 1})

        assert result["status"] == 0

    def test_set_response_error_is_not_caught(self, redis_client):
        """redis.ResponseError is NOT caught — should propagate."""
        redis_client._fake.set.side_effect = redis_lib.ResponseError("OOM")

        with pytest.raises(redis_lib.ResponseError):
            redis_client.set_response("test:key", {"data": 1})

    def test_set_then_get_round_trip(self, redis_client):
        """Verifies the serialized format from set is readable by get."""
        payload = {"answer": 42, "nested": {"a": [1, 2, 3]}}

        # Simulate: after set, get returns the same serialized bytes
        redis_client._fake.get.return_value = json.dumps(payload).encode()

        redis_client.set_response("round:trip", payload, ttl_seconds=60)
        result = redis_client.get_response("round:trip")

        assert result["status"] == 1
        assert result["data"] == payload

    def test_client_none_returns_status_0(self):
        """Fails safely when client is None (Redis disabled)."""
        client = _make_disabled_client()

        result = client.set_response("any:key", {"data": 1})

        assert result["status"] == 0

    @patch("app.cache.redis_client.logger")
    def test_connection_error_logs_warning(self, mock_logger, redis_client):
        """ConnectionError logs a warning (not error)."""
        redis_client._fake.set.side_effect = redis_lib.ConnectionError("refused")

        redis_client.set_response("test:key", {"data": 1})

        mock_logger.warning.assert_called_once()
        assert "set_response" in str(mock_logger.warning.call_args)


# ---------------------------------------------------------------------------
# delete_key tests
# ---------------------------------------------------------------------------

class TestDeleteKey:
    """Test single key deletion."""

    def test_delete_existing_key(self, redis_client):
        """Successfully deletes a key and returns status 1."""
        redis_client._fake.delete.return_value = 1

        result = redis_client.delete_key("test:key")

        assert result["status"] == 1
        redis_client._fake.delete.assert_called_once_with("test:key")

    def test_delete_nonexistent_key_still_status_1(self, redis_client):
        """Returns status 1 even if key didn't exist (Redis delete is idempotent)."""
        redis_client._fake.delete.return_value = 0

        result = redis_client.delete_key("missing:key")

        assert result["status"] == 1

    def test_delete_connection_error_returns_status_0(self, redis_client):
        """Fails safely on redis.ConnectionError."""
        redis_client._fake.delete.side_effect = redis_lib.ConnectionError("Connection refused")

        result = redis_client.delete_key("test:key")

        assert result["status"] == 0

    def test_delete_timeout_error_returns_status_0(self, redis_client):
        """Fails safely on redis.TimeoutError."""
        redis_client._fake.delete.side_effect = redis_lib.TimeoutError("Timed out")

        result = redis_client.delete_key("test:key")

        assert result["status"] == 0

    def test_delete_response_error_is_not_caught(self, redis_client):
        """redis.ResponseError is NOT caught — should propagate."""
        redis_client._fake.delete.side_effect = redis_lib.ResponseError("READONLY")

        with pytest.raises(redis_lib.ResponseError):
            redis_client.delete_key("test:key")

    def test_client_none_returns_status_0(self):
        """Fails safely when client is None (Redis disabled)."""
        client = _make_disabled_client()

        result = client.delete_key("any:key")

        assert result["status"] == 0

    @patch("app.cache.redis_client.logger")
    def test_connection_error_logs_warning(self, mock_logger, redis_client):
        """ConnectionError logs a warning (not error)."""
        redis_client._fake.delete.side_effect = redis_lib.ConnectionError("refused")

        redis_client.delete_key("test:key")

        mock_logger.warning.assert_called_once()
        assert "delete_key" in str(mock_logger.warning.call_args)


# ---------------------------------------------------------------------------
# delete_pattern tests
# ---------------------------------------------------------------------------

class TestDeletePattern:
    """Test pattern-based bulk deletion."""

    def test_delete_matching_keys(self, redis_client):
        """Deletes all keys matching the pattern."""
        redis_client._fake.scan_iter.return_value = [
            b"schemasense:session:abc:schema",
            b"schemasense:session:abc:config",
        ]

        result = redis_client.delete_pattern("schemasense:session:abc:*")

        assert result["status"] == 1
        redis_client._fake.scan_iter.assert_called_once_with("schemasense:session:abc:*")
        assert redis_client._fake.delete.call_count == 2

    def test_delete_pattern_calls_delete_for_each_key(self, redis_client):
        """Each matched key gets its own delete call."""
        keys = [b"key:1", b"key:2", b"key:3"]
        redis_client._fake.scan_iter.return_value = keys

        redis_client.delete_pattern("key:*")

        expected_calls = [call(k) for k in keys]
        redis_client._fake.delete.assert_has_calls(expected_calls, any_order=False)

    def test_delete_pattern_no_matches_returns_status_1(self, redis_client):
        """Returns status 1 when no keys match (nothing to delete is fine)."""
        redis_client._fake.scan_iter.return_value = []

        result = redis_client.delete_pattern("nonexistent:*")

        assert result["status"] == 1
        redis_client._fake.delete.assert_not_called()

    def test_delete_pattern_connection_error_on_scan(self, redis_client):
        """Fails safely when scan_iter raises redis.ConnectionError."""
        redis_client._fake.scan_iter.side_effect = redis_lib.ConnectionError("Connection refused")

        result = redis_client.delete_pattern("test:*")

        assert result["status"] == 0

    def test_delete_pattern_timeout_error_on_scan(self, redis_client):
        """Fails safely when scan_iter raises redis.TimeoutError."""
        redis_client._fake.scan_iter.side_effect = redis_lib.TimeoutError("Timed out")

        result = redis_client.delete_pattern("test:*")

        assert result["status"] == 0

    def test_delete_pattern_connection_error_on_delete(self, redis_client):
        """Fails safely when delete raises mid-iteration."""
        redis_client._fake.scan_iter.return_value = [b"key:1", b"key:2"]
        redis_client._fake.delete.side_effect = redis_lib.ConnectionError("Lost connection")

        result = redis_client.delete_pattern("key:*")

        assert result["status"] == 0

    def test_delete_pattern_response_error_is_not_caught(self, redis_client):
        """redis.ResponseError is NOT caught — should propagate."""
        redis_client._fake.scan_iter.side_effect = redis_lib.ResponseError("NOPERM")

        with pytest.raises(redis_lib.ResponseError):
            redis_client.delete_pattern("test:*")

    def test_client_none_returns_status_0(self):
        """Fails safely when client is None (Redis disabled)."""
        client = _make_disabled_client()

        result = client.delete_pattern("any:*")

        assert result["status"] == 0

    @patch("app.cache.redis_client.logger")
    def test_connection_error_logs_warning(self, mock_logger, redis_client):
        """ConnectionError logs a warning (not error)."""
        redis_client._fake.scan_iter.side_effect = redis_lib.ConnectionError("refused")

        redis_client.delete_pattern("test:*")

        mock_logger.warning.assert_called_once()
        assert "delete_pattern" in str(mock_logger.warning.call_args)


# ---------------------------------------------------------------------------
# health_check tests
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Test Redis health/ping behavior."""

    def test_healthy_returns_true(self, redis_client):
        """Returns True when Redis responds to PING."""
        redis_client._fake.ping.return_value = True

        assert redis_client.health_check() is True

    def test_connection_error_returns_false(self, redis_client):
        """Returns False on redis.ConnectionError."""
        redis_client._fake.ping.side_effect = redis_lib.ConnectionError("Connection refused")

        assert redis_client.health_check() is False

    def test_timeout_error_returns_false(self, redis_client):
        """Returns False on redis.TimeoutError."""
        redis_client._fake.ping.side_effect = redis_lib.TimeoutError("Timed out")

        assert redis_client.health_check() is False

    def test_response_error_is_not_caught(self, redis_client):
        """redis.ResponseError is NOT caught — should propagate."""
        redis_client._fake.ping.side_effect = redis_lib.ResponseError("NOAUTH")

        with pytest.raises(redis_lib.ResponseError):
            redis_client.health_check()

    def test_client_none_returns_false(self):
        """Returns False when client is None (Redis disabled)."""
        client = _make_disabled_client()

        assert client.health_check() is False

    @patch("app.cache.redis_client.logger")
    def test_connection_error_logs_warning(self, mock_logger, redis_client):
        """ConnectionError logs a warning (not error)."""
        redis_client._fake.ping.side_effect = redis_lib.ConnectionError("refused")

        redis_client.health_check()

        mock_logger.warning.assert_called_once()
        assert "health check" in str(mock_logger.warning.call_args)

    @patch("app.cache.redis_client.logger")
    def test_client_none_does_not_log_on_health_check(self, mock_logger):
        """No warning/error logged by health_check itself when client is None."""
        client = _make_disabled_client()
        # Reset after __init__ logging (which warns about disabled/no URL)
        mock_logger.reset_mock()

        client.health_check()

        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()


# ---------------------------------------------------------------------------
# get_redis_client singleton tests
# ---------------------------------------------------------------------------

class TestGetRedisClient:
    """Test the module-level singleton factory."""

    @patch("app.cache.redis_client.get_settings")
    def test_returns_same_instance(self, mock_settings):
        """get_redis_client always returns the same module-level instance."""
        from app.cache.redis_client import get_redis_client

        client_a = get_redis_client()
        client_b = get_redis_client()

        assert client_a is client_b

    @patch("app.cache.redis_client.get_settings")
    def test_returns_redis_client_type(self, mock_settings):
        """get_redis_client returns a RedisClient instance."""
        from app.cache.redis_client import get_redis_client

        client = get_redis_client()

        assert isinstance(client, RedisClient)
