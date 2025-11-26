"""
Tests for schema caching functionality.
"""
import sys
from pathlib import Path
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.schema import cache
from app.models.schema_model import CanonicalSchemaModel


# Mock connection and cursor classes (similar to test_instrospect.py)
class FakeCursor:
    def __init__(self, tables_data, pks_data, fks_data, fail: bool = False):
        self.tables_data = tables_data
        self.pks_data = pks_data
        self.fks_data = fks_data
        self.fail = fail
        self.closed = False
        self.call_count = 0
        self.executed_sql = None

    def execute(self, sql: str) -> None:
        self.executed_sql = sql
        if self.fail:
            raise RuntimeError("Database error")
        self.call_count += 1

    def fetchall(self):
        # Return different data based on which introspection function called
        sql_lower = self.executed_sql.lower()
        if "information_schema.columns" in sql_lower:
            return self.tables_data
        elif "contype = 'p'" in sql_lower:
            return self.pks_data
        elif "contype = 'f'" in sql_lower:
            return self.fks_data
        return []

    def close(self) -> None:
        self.closed = True


class FakeConn:
    def __init__(self, tables_data, pks_data, fks_data, fail: bool = False):
        self.tables_data = tables_data
        self.pks_data = pks_data
        self.fks_data = fks_data
        self.fail = fail
        self.last_cursor: FakeCursor | None = None
        self.cursor_count = 0

    def cursor(self) -> FakeCursor:
        self.cursor_count += 1
        self.last_cursor = FakeCursor(
            self.tables_data,
            self.pks_data,
            self.fks_data,
            self.fail
        )
        return self.last_cursor


@pytest.fixture(autouse=True)
def clear_cache_before_each_test():
    """Clear cache before each test to ensure test isolation."""
    cache.clear_schema_cache()
    yield
    cache.clear_schema_cache()


def test_cache_starts_empty():
    """Test that cache is initially empty."""
    assert cache.get_cached_schema() is None


def test_set_and_get_cached_schema():
    """Test basic cache set and get operations."""
    # Create a simple schema model
    model = CanonicalSchemaModel(tables={}, relationships=[])

    # Set in cache
    cache.set_cached_schema(model)

    # Retrieve from cache
    cached = cache.get_cached_schema()
    assert cached is not None
    assert cached is model  # Should be the exact same instance


def test_clear_schema_cache():
    """Test that clear_schema_cache removes cached data."""
    # Set a model in cache
    model = CanonicalSchemaModel(tables={}, relationships=[])
    cache.set_cached_schema(model)
    assert cache.get_cached_schema() is not None

    # Clear cache
    cache.clear_schema_cache()
    assert cache.get_cached_schema() is None


def test_refresh_schema_clears_old_cache():
    """Test that refresh_schema clears existing cache before refreshing."""
    # Set an old model in cache
    old_model = CanonicalSchemaModel(tables={}, relationships=[])
    cache.set_cached_schema(old_model)

    # Create fake connection with data
    tables_data = [
        ("public", "users", "id", "integer", "NO"),
    ]
    pks_data = [("public", "users", "id")]
    fks_data = []

    conn = FakeConn(tables_data, pks_data, fks_data)

    # Refresh schema
    new_model = cache.refresh_schema(conn)

    # Should return a different model
    assert new_model is not old_model
    assert cache.get_cached_schema() is new_model


def test_refresh_schema_runs_all_introspection():
    """Test that refresh_schema runs all three introspection functions."""
    tables_data = [
        ("public", "customers", "id", "integer", "NO"),
        ("public", "customers", "name", "text", "YES"),
    ]
    pks_data = [("public", "customers", "id")]
    fks_data = []

    conn = FakeConn(tables_data, pks_data, fks_data)

    # Refresh schema
    model = cache.refresh_schema(conn)

    # Verify model was built correctly
    assert model is not None
    assert len(model.tables) == 1
    assert "public.customers" in model.tables

    table = model.tables["public.customers"]
    assert table.name == "customers"
    assert len(table.columns) == 2

    # Verify all introspection functions were called (3 cursor creations)
    assert conn.cursor_count == 3


def test_refresh_schema_with_foreign_keys():
    """Test refresh_schema with a schema containing foreign keys."""
    tables_data = [
        ("public", "customers", "id", "integer", "NO"),
        ("public", "orders", "id", "integer", "NO"),
        ("public", "orders", "customer_id", "integer", "NO"),
    ]
    pks_data = [
        ("public", "customers", "id"),
        ("public", "orders", "id"),
    ]
    fks_data = [
        ("public", "orders", "customer_id", "public", "customers", "id"),
    ]

    conn = FakeConn(tables_data, pks_data, fks_data)

    # Refresh schema
    model = cache.refresh_schema(conn)

    # Verify model
    assert len(model.tables) == 2
    assert len(model.relationships) == 1

    rel = model.relationships[0]
    assert rel.from_table == "public.orders"
    assert rel.from_column == "customer_id"
    assert rel.to_table == "public.customers"

    # Verify FK flag is set
    orders_table = model.tables["public.orders"]
    customer_id_col = orders_table.columns[1]
    assert customer_id_col.name == "customer_id"
    assert customer_id_col.is_fk is True


def test_refresh_schema_caches_result():
    """Test that refresh_schema stores result in cache."""
    tables_data = [("public", "users", "id", "integer", "NO")]
    pks_data = [("public", "users", "id")]
    fks_data = []

    conn = FakeConn(tables_data, pks_data, fks_data)

    # Cache should be empty initially
    assert cache.get_cached_schema() is None

    # Refresh schema
    model = cache.refresh_schema(conn)

    # Model should now be cached
    cached = cache.get_cached_schema()
    assert cached is not None
    assert cached is model


def test_refresh_schema_propagates_errors():
    """Test that errors from introspection are propagated."""
    conn = FakeConn([], [], [], fail=True)

    with pytest.raises(Exception) as excinfo:
        cache.refresh_schema(conn)

    assert "Error introspecting" in str(excinfo.value)


def test_get_or_refresh_schema_when_cache_empty():
    """Test get_or_refresh_schema runs introspection when cache is empty."""
    tables_data = [("public", "products", "id", "integer", "NO")]
    pks_data = [("public", "products", "id")]
    fks_data = []

    conn = FakeConn(tables_data, pks_data, fks_data)

    # Cache should be empty
    assert cache.get_cached_schema() is None

    # Get or refresh should run introspection
    model = cache.get_or_refresh_schema(conn)

    assert model is not None
    assert len(model.tables) == 1
    assert "public.products" in model.tables

    # Should now be cached
    assert cache.get_cached_schema() is model


def test_get_or_refresh_schema_when_cache_populated():
    """Test get_or_refresh_schema returns cached model without re-introspecting."""
    tables_data = [("public", "users", "id", "integer", "NO")]
    pks_data = [("public", "users", "id")]
    fks_data = []

    conn = FakeConn(tables_data, pks_data, fks_data)

    # First call: cache is empty, should introspect
    model1 = cache.get_or_refresh_schema(conn)
    call_count_1 = conn.cursor_count

    # Second call: cache is populated, should NOT introspect again
    model2 = cache.get_or_refresh_schema(conn)
    call_count_2 = conn.cursor_count

    # Should return same model instance
    assert model1 is model2

    # Should NOT have created more cursors (no new introspection)
    assert call_count_2 == call_count_1


def test_refresh_schema_empty_database():
    """Test refresh_schema with empty database."""
    tables_data = []
    pks_data = []
    fks_data = []

    conn = FakeConn(tables_data, pks_data, fks_data)

    model = cache.refresh_schema(conn)

    assert model is not None
    assert len(model.tables) == 0
    assert len(model.relationships) == 0


def test_refresh_schema_complex_schema():
    """Test refresh_schema with a complex multi-table schema."""
    tables_data = [
        ("public", "customers", "id", "integer", "NO"),
        ("public", "customers", "name", "text", "NO"),
        ("public", "orders", "id", "integer", "NO"),
        ("public", "orders", "customer_id", "integer", "NO"),
        ("public", "order_items", "order_id", "integer", "NO"),
        ("public", "order_items", "product_id", "integer", "NO"),
        ("public", "order_items", "quantity", "integer", "NO"),
        ("public", "products", "id", "integer", "NO"),
        ("public", "products", "name", "text", "NO"),
    ]
    pks_data = [
        ("public", "customers", "id"),
        ("public", "orders", "id"),
        ("public", "order_items", "order_id"),
        ("public", "order_items", "product_id"),
        ("public", "products", "id"),
    ]
    fks_data = [
        ("public", "orders", "customer_id", "public", "customers", "id"),
        ("public", "order_items", "order_id", "public", "orders", "id"),
        ("public", "order_items", "product_id", "public", "products", "id"),
    ]

    conn = FakeConn(tables_data, pks_data, fks_data)

    model = cache.refresh_schema(conn)

    # Verify structure
    assert len(model.tables) == 4
    assert len(model.relationships) == 3

    # Verify composite PK in order_items
    order_items = model.tables["public.order_items"]
    assert order_items.columns[0].is_pk is True  # order_id
    assert order_items.columns[1].is_pk is True  # product_id
    assert order_items.columns[0].is_fk is True  # also FK
    assert order_items.columns[1].is_fk is True  # also FK


def test_multiple_refresh_cycles():
    """Test multiple refresh cycles to ensure cache is properly updated."""
    # First schema
    tables_data_1 = [("public", "users", "id", "integer", "NO")]
    pks_data_1 = [("public", "users", "id")]
    fks_data_1 = []

    conn1 = FakeConn(tables_data_1, pks_data_1, fks_data_1)
    model1 = cache.refresh_schema(conn1)

    assert len(model1.tables) == 1
    assert "public.users" in model1.tables

    # Second schema (different data)
    tables_data_2 = [
        ("public", "products", "id", "integer", "NO"),
        ("public", "products", "name", "text", "YES"),
    ]
    pks_data_2 = [("public", "products", "id")]
    fks_data_2 = []

    conn2 = FakeConn(tables_data_2, pks_data_2, fks_data_2)
    model2 = cache.refresh_schema(conn2)

    assert len(model2.tables) == 1
    assert "public.products" in model2.tables
    assert "public.users" not in model2.tables  # Old data should be gone

    # Cache should contain the new model
    cached = cache.get_cached_schema()
    assert cached is model2
    assert cached is not model1
