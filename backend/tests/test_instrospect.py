import sys
from pathlib import Path
import pytest

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.schema.introspect import introspect_tables_and_columns, introspect_primary_keys, introspect_foreign_keys


class FakeCursor:
    def __init__(self, rows, fail: bool = False):
        self.rows = rows
        self.fail = fail
        self.closed = False
        self.executed_sql = None

    def execute(self, sql: str) -> None:
        self.executed_sql = sql
        if self.fail:
            raise RuntimeError("boom")

    def fetchall(self):
        return self.rows

    def close(self) -> None:
        self.closed = True


class FakeConn:
    def __init__(self, rows, fail: bool = False):
        self.rows = rows
        self.fail = fail
        self.last_cursor: FakeCursor | None = None

    def cursor(self) -> FakeCursor:
        self.last_cursor = FakeCursor(self.rows, self.fail)
        return self.last_cursor


def test_groups_columns_by_table_and_schema():
    rows = [
        ("public", "customers", "id", "integer", "NO"),
        ("public", "customers", "name", "text", "YES"),
        ("sales", "orders", "id", "integer", "NO"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    assert ("public", "customers") in result
    assert result[("public", "customers")]["columns"][0]["name"] == "id"
    assert result[("public", "customers")]["columns"][1]["nullable"] == "YES"
    assert result[("sales", "orders")]["columns"][0]["type"] == "integer"
    assert conn.last_cursor.closed is True


def test_raises_clean_error_on_failure():
    conn = FakeConn([], fail=True)

    with pytest.raises(Exception) as excinfo:
        introspect_tables_and_columns(conn)

    assert "Error introspecting tables and columns" in str(excinfo.value)
    assert conn.last_cursor.closed is True


def test_introspect_tables_empty_database():
    """Test when database has no user tables (edge case)."""
    rows = []
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    assert result == {}
    assert conn.last_cursor.closed is True


def test_introspect_tables_verifies_return_structure():
    """Test that each table has the expected structure with schema, table, and columns."""
    rows = [
        ("public", "users", "id", "integer", "NO"),
        ("public", "users", "email", "varchar", "NO"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    table_key = ("public", "users")
    assert table_key in result
    assert "schema" in result[table_key]
    assert "table" in result[table_key]
    assert "columns" in result[table_key]
    assert result[table_key]["schema"] == "public"
    assert result[table_key]["table"] == "users"
    assert isinstance(result[table_key]["columns"], list)
    assert len(result[table_key]["columns"]) == 2


def test_introspect_tables_captures_data_types():
    """Test that various PostgreSQL data types are correctly captured."""
    rows = [
        ("public", "test_table", "col_int", "integer", "NO"),
        ("public", "test_table", "col_text", "text", "YES"),
        ("public", "test_table", "col_varchar", "character varying", "YES"),
        ("public", "test_table", "col_timestamp", "timestamp without time zone", "NO"),
        ("public", "test_table", "col_bool", "boolean", "YES"),
        ("public", "test_table", "col_json", "jsonb", "YES"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    columns = result[("public", "test_table")]["columns"]
    assert columns[0]["type"] == "integer"
    assert columns[1]["type"] == "text"
    assert columns[2]["type"] == "character varying"
    assert columns[3]["type"] == "timestamp without time zone"
    assert columns[4]["type"] == "boolean"
    assert columns[5]["type"] == "jsonb"


def test_introspect_tables_captures_nullability():
    """Test that nullable and not-null constraints are correctly captured."""
    rows = [
        ("public", "products", "id", "integer", "NO"),
        ("public", "products", "name", "text", "NO"),
        ("public", "products", "description", "text", "YES"),
        ("public", "products", "price", "numeric", "NO"),
        ("public", "products", "notes", "text", "YES"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    columns = result[("public", "products")]["columns"]
    assert columns[0]["nullable"] == "NO"  # id
    assert columns[1]["nullable"] == "NO"  # name
    assert columns[2]["nullable"] == "YES"  # description
    assert columns[3]["nullable"] == "NO"  # price
    assert columns[4]["nullable"] == "YES"  # notes


def test_introspect_tables_preserves_column_order():
    """Test that columns are returned in their defined ordinal order."""
    # Columns intentionally not in alphabetical order
    rows = [
        ("public", "ordered_table", "zebra", "text", "YES"),
        ("public", "ordered_table", "apple", "text", "YES"),
        ("public", "ordered_table", "mango", "text", "YES"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    columns = result[("public", "ordered_table")]["columns"]
    # Should preserve the order from the query (which orders by ordinal_position)
    assert columns[0]["name"] == "zebra"
    assert columns[1]["name"] == "apple"
    assert columns[2]["name"] == "mango"


def test_introspect_tables_multiple_schemas():
    """Test introspection across multiple schemas."""
    rows = [
        ("public", "users", "id", "integer", "NO"),
        ("public", "users", "name", "text", "YES"),
        ("sales", "users", "user_id", "bigint", "NO"),  # Same table name, different schema
        ("sales", "orders", "order_id", "integer", "NO"),
        ("analytics", "events", "event_id", "uuid", "NO"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    assert len(result) == 4
    assert ("public", "users") in result
    assert ("sales", "users") in result
    assert ("sales", "orders") in result
    assert ("analytics", "events") in result
    # Verify different schemas are isolated
    assert result[("public", "users")]["columns"][0]["name"] == "id"
    assert result[("sales", "users")]["columns"][0]["name"] == "user_id"


def test_introspect_tables_single_column_table():
    """Test table with only one column (edge case)."""
    rows = [
        ("public", "simple_table", "id", "serial", "NO"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    assert len(result) == 1
    assert len(result[("public", "simple_table")]["columns"]) == 1
    assert result[("public", "simple_table")]["columns"][0]["name"] == "id"


def test_introspect_tables_many_columns():
    """Test table with many columns."""
    rows = [
        ("public", "wide_table", f"col_{i}", "text", "YES")
        for i in range(50)
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    assert len(result) == 1
    assert len(result[("public", "wide_table")]["columns"]) == 50
    # Verify first and last
    assert result[("public", "wide_table")]["columns"][0]["name"] == "col_0"
    assert result[("public", "wide_table")]["columns"][49]["name"] == "col_49"


def test_introspect_tables_verifies_sql_query():
    """Test that the function queries information_schema correctly."""
    rows = [("public", "test", "col", "text", "NO")]
    conn = FakeConn(rows)

    introspect_tables_and_columns(conn)

    executed_sql = conn.last_cursor.executed_sql.lower()
    # Verify it queries information_schema.columns
    assert "information_schema.columns" in executed_sql
    # Verify it excludes system schemas
    assert "pg_catalog" in executed_sql
    assert "information_schema" in executed_sql
    # Verify it orders by ordinal_position for correct column order
    assert "ordinal_position" in executed_sql


def test_introspect_tables_closes_cursor_on_success():
    """Test that cursor is properly closed after successful execution."""
    rows = [("public", "test", "col", "text", "NO")]
    conn = FakeConn(rows)

    introspect_tables_and_columns(conn)

    assert conn.last_cursor.closed is True


def test_introspect_tables_multiple_tables_same_schema():
    """Test multiple tables within the same schema."""
    rows = [
        ("public", "table_a", "id", "integer", "NO"),
        ("public", "table_a", "data", "text", "YES"),
        ("public", "table_b", "id", "integer", "NO"),
        ("public", "table_c", "id", "integer", "NO"),
        ("public", "table_c", "name", "text", "NO"),
        ("public", "table_c", "value", "numeric", "YES"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    assert len(result) == 3
    assert len(result[("public", "table_a")]["columns"]) == 2
    assert len(result[("public", "table_b")]["columns"]) == 1
    assert len(result[("public", "table_c")]["columns"]) == 3


# ============================================================================
# Tests for introspect_primary_keys(conn)
# ============================================================================
# Expected return format:
# {
#   ("schema_name", "table_name"): ["pk_column_1", "pk_column_2", ...],
#   ...
# }
def test_introspect_single_column_primary_keys():
    """Test tables with single-column primary keys."""
    # Rows format: (schema_name, table_name, column_name)
    rows = [
        ("public", "customers", "id"),
        ("public", "products", "product_id"),
        ("sales", "orders", "order_id"),
    ]
    conn = FakeConn(rows)

    result = introspect_primary_keys(conn)

    assert len(result) == 3
    assert result[("public", "customers")] == ["id"]
    assert result[("public", "products")] == ["product_id"]
    assert result[("sales", "orders")] == ["order_id"]
    assert conn.last_cursor.closed is True


def test_introspect_composite_primary_keys():
    """Test tables with composite (multi-column) primary keys."""
    # Composite primary keys: multiple rows for the same table
    rows = [
        ("public", "order_items", "order_id"),
        ("public", "order_items", "product_id"),
        ("sales", "user_roles", "user_id"),
        ("sales", "user_roles", "role_id"),
        ("public", "customers", "id"),  # Single PK for comparison
    ]
    conn = FakeConn(rows)

    result = introspect_primary_keys(conn)

    assert len(result) == 3
    # Composite PKs should have multiple columns in the list
    assert result[("public", "order_items")] == ["order_id", "product_id"]
    assert result[("sales", "user_roles")] == ["user_id", "role_id"]
    # Single PK should have one column
    assert result[("public", "customers")] == ["id"]
    assert conn.last_cursor.closed is True


def test_introspect_primary_keys_empty_database():
    """Test when no tables have primary keys (edge case)."""
    rows = []
    conn = FakeConn(rows)

    result = introspect_primary_keys(conn)

    assert result == {}
    assert conn.last_cursor.closed is True


def test_introspect_primary_keys_preserves_column_order():
    """Test that PK columns are returned in the correct ordinal order."""
    # PostgreSQL constraint columns have an ordinal position
    # The query should ORDER BY this to preserve definition order
    rows = [
        ("public", "composite_table", "col_b"),  # Intentionally out of alphabetical order
        ("public", "composite_table", "col_a"),
        ("public", "composite_table", "col_c"),
    ]
    conn = FakeConn(rows)

    result = introspect_primary_keys(conn)

    # The result should preserve the order as returned by the query
    assert result[("public", "composite_table")] == ["col_b", "col_a", "col_c"]
    assert conn.last_cursor.closed is True


def test_introspect_primary_keys_multiple_schemas():
    """Test primary keys across multiple schemas."""
    rows = [
        ("public", "users", "user_id"),
        ("sales", "users", "id"),  # Different table in different schema
        ("analytics", "events", "event_id"),
        ("analytics", "events", "timestamp"),  # Composite PK
    ]
    conn = FakeConn(rows)

    result = introspect_primary_keys(conn)

    assert len(result) == 3
    assert result[("public", "users")] == ["user_id"]
    assert result[("sales", "users")] == ["id"]
    assert result[("analytics", "events")] == ["event_id", "timestamp"]
    assert conn.last_cursor.closed is True


def test_introspect_primary_keys_verifies_sql_query():
    """Test that the function queries pg_catalog correctly."""
    rows = [("public", "test_table", "id")]
    conn = FakeConn(rows)

    introspect_primary_keys(conn)

    executed_sql = conn.last_cursor.executed_sql.lower()
    # Verify it queries the right catalog tables as per plan.md requirements
    assert "pg_constraint" in executed_sql or "pg_catalog.pg_constraint" in executed_sql
    assert "pg_class" in executed_sql or "pg_catalog.pg_class" in executed_sql
    assert "pg_attribute" in executed_sql or "pg_catalog.pg_attribute" in executed_sql
    # Verify it filters for primary key constraints (contype = 'p')
    assert "'p'" in executed_sql or '"p"' in executed_sql


def test_introspect_primary_keys_raises_clean_error_on_failure():
    """Test error handling when database query fails."""
    conn = FakeConn([], fail=True)

    with pytest.raises(Exception) as excinfo:
        introspect_primary_keys(conn)

    assert "Error introspecting primary keys" in str(excinfo.value)
    assert conn.last_cursor.closed is True


def test_introspect_primary_keys_closes_cursor_even_on_error():
    """Test that cursor is properly closed even when an error occurs."""
    conn = FakeConn([], fail=True)

    try:
        introspect_primary_keys(conn)
    except Exception:
        pass  # Expected to fail

    assert conn.last_cursor is not None
    assert conn.last_cursor.closed is True


# ============================================================================
# Tests for introspect_foreign_keys(conn)
# ============================================================================
# Expected return format:
# [
#   {
#     "from_table": ("src_schema", "src_table"),
#     "from_column": "column_name",
#     "to_table": ("tgt_schema", "tgt_table"),
#     "to_column": "target_column",
#   },
#   ...
# ]


def test_introspect_simple_foreign_keys():
    """Test basic single-column foreign keys."""
    # Rows format: (from_schema, from_table, from_column, to_schema, to_table, to_column)
    rows = [
        ("public", "orders", "customer_id", "public", "customers", "id"),
        ("public", "order_items", "order_id", "public", "orders", "id"),
        ("sales", "invoices", "customer_id", "public", "customers", "id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 3
    assert result[0] == {
        "from_table": ("public", "orders"),
        "from_column": "customer_id",
        "to_table": ("public", "customers"),
        "to_column": "id",
    }
    assert result[1] == {
        "from_table": ("public", "order_items"),
        "from_column": "order_id",
        "to_table": ("public", "orders"),
        "to_column": "id",
    }
    assert result[2] == {
        "from_table": ("sales", "invoices"),
        "from_column": "customer_id",
        "to_table": ("public", "customers"),
        "to_column": "id",
    }
    assert conn.last_cursor.closed is True


def test_introspect_composite_foreign_keys():
    """Test composite (multi-column) foreign keys."""
    # A composite FK has multiple columns referencing multiple columns in target table
    rows = [
        ("public", "order_items", "order_id", "public", "orders", "id"),
        ("public", "order_items", "product_id", "public", "orders", "product_id"),
        ("sales", "line_items", "invoice_num", "sales", "invoices", "invoice_num"),
        ("sales", "line_items", "item_seq", "sales", "invoices", "item_seq"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 4
    # Verify composite FK from order_items to orders
    assert result[0]["from_table"] == ("public", "order_items")
    assert result[0]["from_column"] == "order_id"
    assert result[1]["from_table"] == ("public", "order_items")
    assert result[1]["from_column"] == "product_id"
    assert conn.last_cursor.closed is True


def test_introspect_foreign_keys_empty_database():
    """Test when no foreign keys exist (edge case)."""
    rows = []
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert result == []
    assert conn.last_cursor.closed is True


def test_introspect_foreign_keys_verifies_return_structure():
    """Test that each FK has the expected dictionary structure."""
    rows = [
        ("public", "orders", "customer_id", "public", "customers", "id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 1
    fk = result[0]
    assert "from_table" in fk
    assert "from_column" in fk
    assert "to_table" in fk
    assert "to_column" in fk
    # Verify from_table and to_table are tuples
    assert isinstance(fk["from_table"], tuple)
    assert isinstance(fk["to_table"], tuple)
    assert len(fk["from_table"]) == 2  # (schema, table)
    assert len(fk["to_table"]) == 2


def test_introspect_foreign_keys_cross_schema():
    """Test foreign keys that reference tables in different schemas."""
    rows = [
        ("sales", "orders", "customer_id", "public", "customers", "id"),
        ("analytics", "events", "user_id", "public", "users", "id"),
        ("public", "posts", "author_id", "auth", "users", "user_id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 3
    # sales.orders -> public.customers
    assert result[0]["from_table"] == ("sales", "orders")
    assert result[0]["to_table"] == ("public", "customers")
    # analytics.events -> public.users
    assert result[1]["from_table"] == ("analytics", "events")
    assert result[1]["to_table"] == ("public", "users")
    # public.posts -> auth.users
    assert result[2]["from_table"] == ("public", "posts")
    assert result[2]["to_table"] == ("auth", "users")


def test_introspect_foreign_keys_self_referential():
    """Test self-referential foreign keys (table references itself)."""
    rows = [
        ("public", "employees", "manager_id", "public", "employees", "id"),
        ("public", "categories", "parent_id", "public", "categories", "id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 2
    # employees.manager_id -> employees.id
    assert result[0]["from_table"] == ("public", "employees")
    assert result[0]["to_table"] == ("public", "employees")
    assert result[0]["from_column"] == "manager_id"
    assert result[0]["to_column"] == "id"
    # categories.parent_id -> categories.id
    assert result[1]["from_table"] == ("public", "categories")
    assert result[1]["to_table"] == ("public", "categories")


def test_introspect_foreign_keys_multiple_fks_same_table():
    """Test table with multiple different foreign keys."""
    rows = [
        ("public", "orders", "customer_id", "public", "customers", "id"),
        ("public", "orders", "salesperson_id", "public", "employees", "id"),
        ("public", "orders", "shipping_address_id", "public", "addresses", "id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 3
    # All from same table but to different tables
    assert all(fk["from_table"] == ("public", "orders") for fk in result)
    # Verify different target tables
    target_tables = [fk["to_table"] for fk in result]
    assert ("public", "customers") in target_tables
    assert ("public", "employees") in target_tables
    assert ("public", "addresses") in target_tables


def test_introspect_foreign_keys_same_target_different_sources():
    """Test multiple tables referencing the same target table."""
    rows = [
        ("public", "orders", "customer_id", "public", "customers", "id"),
        ("public", "invoices", "customer_id", "public", "customers", "id"),
        ("public", "support_tickets", "customer_id", "public", "customers", "id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 3
    # All reference same target table
    assert all(fk["to_table"] == ("public", "customers") for fk in result)
    assert all(fk["to_column"] == "id" for fk in result)
    # But from different source tables
    source_tables = [fk["from_table"] for fk in result]
    assert ("public", "orders") in source_tables
    assert ("public", "invoices") in source_tables
    assert ("public", "support_tickets") in source_tables


def test_introspect_foreign_keys_verifies_sql_query():
    """Test that the function queries pg_catalog correctly."""
    rows = [("public", "orders", "customer_id", "public", "customers", "id")]
    conn = FakeConn(rows)

    introspect_foreign_keys(conn)

    executed_sql = conn.last_cursor.executed_sql.lower()
    # Verify it queries pg_catalog.pg_constraint as per plan.md requirements
    assert "pg_constraint" in executed_sql or "pg_catalog.pg_constraint" in executed_sql
    # Verify it filters for foreign key constraints (contype = 'f')
    assert "'f'" in executed_sql or '"f"' in executed_sql
    # Should also join with pg_class and pg_attribute to get table/column info
    assert "pg_class" in executed_sql or "pg_catalog.pg_class" in executed_sql
    assert "pg_attribute" in executed_sql or "pg_catalog.pg_attribute" in executed_sql


def test_introspect_foreign_keys_preserves_order():
    """Test that foreign keys are returned in a consistent order."""
    # Multiple FKs to verify ordering is stable
    rows = [
        ("public", "z_table", "a_col", "public", "ref_table", "id"),
        ("public", "a_table", "z_col", "public", "ref_table", "id"),
        ("public", "m_table", "m_col", "public", "ref_table", "id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 3
    # Should preserve the order from the query result
    assert result[0]["from_table"] == ("public", "z_table")
    assert result[1]["from_table"] == ("public", "a_table")
    assert result[2]["from_table"] == ("public", "m_table")


def test_introspect_foreign_keys_raises_clean_error_on_failure():
    """Test error handling when database query fails."""
    conn = FakeConn([], fail=True)

    with pytest.raises(Exception) as excinfo:
        introspect_foreign_keys(conn)

    assert "Error introspecting foreign keys" in str(excinfo.value)
    assert conn.last_cursor.closed is True


def test_introspect_foreign_keys_closes_cursor_even_on_error():
    """Test that cursor is properly closed even when an error occurs."""
    conn = FakeConn([], fail=True)

    try:
        introspect_foreign_keys(conn)
    except Exception:
        pass  # Expected to fail

    assert conn.last_cursor is not None
    assert conn.last_cursor.closed is True


def test_introspect_foreign_keys_closes_cursor_on_success():
    """Test that cursor is properly closed after successful execution."""
    rows = [("public", "orders", "customer_id", "public", "customers", "id")]
    conn = FakeConn(rows)

    introspect_foreign_keys(conn)

    assert conn.last_cursor.closed is True


def test_introspect_foreign_keys_complex_scenario():
    """Test a realistic complex database schema with multiple FK relationships."""
    rows = [
        # E-commerce schema
        ("public", "orders", "customer_id", "public", "customers", "id"),
        ("public", "order_items", "order_id", "public", "orders", "id"),
        ("public", "order_items", "product_id", "public", "products", "id"),
        ("public", "products", "category_id", "public", "categories", "id"),
        ("public", "products", "supplier_id", "public", "suppliers", "id"),
        # Self-referential
        ("public", "categories", "parent_id", "public", "categories", "id"),
        # Cross-schema
        ("sales", "invoices", "order_id", "public", "orders", "id"),
    ]
    conn = FakeConn(rows)

    result = introspect_foreign_keys(conn)

    assert len(result) == 7
    # Verify we have FKs from different tables
    from_tables = [fk["from_table"] for fk in result]
    assert ("public", "orders") in from_tables
    assert ("public", "order_items") in from_tables
    assert ("public", "products") in from_tables
    assert ("public", "categories") in from_tables
    assert ("sales", "invoices") in from_tables
    # Verify self-referential FK exists
    self_ref_fks = [fk for fk in result if fk["from_table"] == fk["to_table"]]
    assert len(self_ref_fks) == 1
    assert self_ref_fks[0]["from_table"] == ("public", "categories")
