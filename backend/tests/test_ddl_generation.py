import sys
from pathlib import Path
import pytest

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.schema_model import CanonicalSchemaModel, Table, Column, Relationship


# ========== Basic DDL Generation Tests ==========

def test_to_ddl_empty_schema():
    """Test DDL generation for an empty schema."""
    model = CanonicalSchemaModel()
    ddl = model.to_ddl()

    assert ddl == ""


def test_to_ddl_single_table_no_pk():
    """Test DDL generation for a single table without primary key."""
    model = CanonicalSchemaModel()
    model.add_table("logs", schema="public", columns=[
        Column(name="timestamp", type="timestamp", nullable=False),
        Column(name="message", type="text", nullable=True)
    ])

    ddl = model.to_ddl()

    # Verify DDL contains CREATE TABLE
    assert "CREATE TABLE public.logs" in ddl
    assert "timestamp timestamp NOT NULL" in ddl
    assert "message text" in ddl

    # Should not contain PRIMARY KEY constraint
    assert "PRIMARY KEY" not in ddl


def test_to_ddl_single_table_with_pk():
    """Test DDL generation for a single table with primary key."""
    model = CanonicalSchemaModel()
    model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="text", nullable=False)
    ])

    ddl = model.to_ddl()

    assert "CREATE TABLE public.users" in ddl
    assert "id integer NOT NULL" in ddl
    assert "name text NOT NULL" in ddl
    assert "CONSTRAINT users_pkey PRIMARY KEY (id)" in ddl


def test_to_ddl_composite_primary_key():
    """Test DDL generation for a table with composite primary key."""
    model = CanonicalSchemaModel()
    model.add_table("order_items", schema="public", columns=[
        Column(name="order_id", type="integer", is_pk=True, nullable=False),
        Column(name="product_id", type="integer", is_pk=True, nullable=False),
        Column(name="quantity", type="integer", nullable=False)
    ])

    ddl = model.to_ddl()

    assert "CREATE TABLE public.order_items" in ddl
    assert "order_id integer NOT NULL" in ddl
    assert "product_id integer NOT NULL" in ddl
    assert "quantity integer NOT NULL" in ddl
    assert "CONSTRAINT order_items_pkey PRIMARY KEY (order_id, product_id)" in ddl


def test_to_ddl_nullable_columns():
    """Test that nullable columns don't include NOT NULL constraint."""
    model = CanonicalSchemaModel()
    model.add_table("products", schema="public", columns=[
        Column(name="id", type="serial", is_pk=True, nullable=False),
        Column(name="name", type="text", nullable=False),
        Column(name="description", type="text", nullable=True),
        Column(name="price", type="numeric(10,2)", nullable=True)
    ])

    ddl = model.to_ddl()

    # Check NOT NULL is only on non-nullable columns
    assert "id serial NOT NULL" in ddl
    assert "name text NOT NULL" in ddl

    # Check nullable columns don't have NOT NULL
    lines = ddl.split('\n')
    description_line = [line for line in lines if 'description' in line][0]
    price_line = [line for line in lines if 'price' in line][0]

    assert "NOT NULL" not in description_line
    assert "NOT NULL" not in price_line


# ========== Foreign Key Tests ==========

def test_to_ddl_single_foreign_key():
    """Test DDL generation for a table with a foreign key."""
    model = CanonicalSchemaModel()

    model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="text", nullable=False)
    ])

    model.add_table("orders", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="user_id", type="integer", nullable=False),
        Column(name="total", type="numeric(10,2)", nullable=False)
    ])

    model.add_relationship("orders", "user_id", "users", "id")

    ddl = model.to_ddl()

    # Verify CREATE TABLE statements
    assert "CREATE TABLE public.users" in ddl
    assert "CREATE TABLE public.orders" in ddl

    # Verify ALTER TABLE foreign key statement
    assert "ALTER TABLE public.orders" in ddl
    assert "ADD CONSTRAINT orders_user_id_fkey" in ddl
    assert "FOREIGN KEY (user_id)" in ddl
    assert "REFERENCES public.users (id)" in ddl


def test_to_ddl_multiple_foreign_keys():
    """Test DDL generation for a table with multiple foreign keys."""
    model = CanonicalSchemaModel()

    model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("products", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("orders", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="user_id", type="integer", nullable=False),
        Column(name="product_id", type="integer", nullable=False)
    ])

    model.add_relationship("orders", "user_id", "users", "id")
    model.add_relationship("orders", "product_id", "products", "id")

    ddl = model.to_ddl()

    # Verify both foreign keys are present
    assert "orders_user_id_fkey" in ddl
    assert "orders_product_id_fkey" in ddl
    assert "REFERENCES public.users (id)" in ddl
    assert "REFERENCES public.products (id)" in ddl


def test_to_ddl_cross_schema_foreign_key():
    """Test DDL generation for foreign keys across different schemas."""
    model = CanonicalSchemaModel()

    model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("orders", schema="sales", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="user_id", type="integer", nullable=False)
    ])

    model.add_relationship("orders", "user_id", "users", "id",
                          from_schema="sales", to_schema="public")

    ddl = model.to_ddl()

    # Verify cross-schema references
    assert "CREATE TABLE public.users" in ddl
    assert "CREATE TABLE sales.orders" in ddl
    assert "ALTER TABLE sales.orders" in ddl
    assert "REFERENCES public.users (id)" in ddl


# ========== Complex Schema Tests ==========

def test_to_ddl_complex_schema():
    """Test DDL generation for a complex schema with multiple tables and relationships."""
    model = CanonicalSchemaModel()

    # Create customers table
    model.add_table("customers", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="varchar(255)", nullable=False),
        Column(name="email", type="varchar(255)", nullable=False)
    ])

    # Create products table
    model.add_table("products", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="varchar(255)", nullable=False),
        Column(name="price", type="numeric(10,2)", nullable=False)
    ])

    # Create orders table
    model.add_table("orders", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="customer_id", type="integer", nullable=False),
        Column(name="order_date", type="timestamp", nullable=False)
    ])

    # Create order_items table with composite PK
    model.add_table("order_items", schema="public", columns=[
        Column(name="order_id", type="integer", is_pk=True, nullable=False),
        Column(name="product_id", type="integer", is_pk=True, nullable=False),
        Column(name="quantity", type="integer", nullable=False),
        Column(name="price", type="numeric(10,2)", nullable=False)
    ])

    # Add relationships
    model.add_relationship("orders", "customer_id", "customers", "id")
    model.add_relationship("order_items", "order_id", "orders", "id")
    model.add_relationship("order_items", "product_id", "products", "id")

    ddl = model.to_ddl()

    # Verify all tables are present
    assert "CREATE TABLE public.customers" in ddl
    assert "CREATE TABLE public.products" in ddl
    assert "CREATE TABLE public.orders" in ddl
    assert "CREATE TABLE public.order_items" in ddl

    # Verify all foreign keys are present
    assert "orders_customer_id_fkey" in ddl
    assert "order_items_order_id_fkey" in ddl
    assert "order_items_product_id_fkey" in ddl

    # Verify composite PK
    assert "CONSTRAINT order_items_pkey PRIMARY KEY (order_id, product_id)" in ddl


def test_to_ddl_multiple_schemas():
    """Test DDL generation for tables across multiple schemas."""
    model = CanonicalSchemaModel()

    model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("invoices", schema="sales", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("products", schema="inventory", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    ddl = model.to_ddl()

    # Verify all schemas are present
    assert "CREATE TABLE public.users" in ddl
    assert "CREATE TABLE sales.invoices" in ddl
    assert "CREATE TABLE inventory.products" in ddl


# ========== Data Type Tests ==========

def test_to_ddl_various_data_types():
    """Test DDL generation with various PostgreSQL data types."""
    model = CanonicalSchemaModel()

    model.add_table("data_types_test", schema="public", columns=[
        Column(name="id", type="serial", is_pk=True, nullable=False),
        Column(name="int_col", type="integer", nullable=True),
        Column(name="bigint_col", type="bigint", nullable=True),
        Column(name="text_col", type="text", nullable=True),
        Column(name="varchar_col", type="varchar(100)", nullable=True),
        Column(name="numeric_col", type="numeric(10,2)", nullable=True),
        Column(name="bool_col", type="boolean", nullable=True),
        Column(name="timestamp_col", type="timestamp", nullable=True),
        Column(name="date_col", type="date", nullable=True),
        Column(name="json_col", type="jsonb", nullable=True),
        Column(name="uuid_col", type="uuid", nullable=True),
        Column(name="array_col", type="text[]", nullable=True)
    ])

    ddl = model.to_ddl()

    # Verify all data types are present
    assert "id serial NOT NULL" in ddl
    assert "int_col integer" in ddl
    assert "bigint_col bigint" in ddl
    assert "text_col text" in ddl
    assert "varchar_col varchar(100)" in ddl
    assert "numeric_col numeric(10,2)" in ddl
    assert "bool_col boolean" in ddl
    assert "timestamp_col timestamp" in ddl
    assert "date_col date" in ddl
    assert "json_col jsonb" in ddl
    assert "uuid_col uuid" in ddl
    assert "array_col text[]" in ddl


# ========== Formatting Tests ==========

def test_to_ddl_formatting_consistency():
    """Test that DDL output has consistent formatting."""
    model = CanonicalSchemaModel()

    model.add_table("test_table", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="text", nullable=False)
    ])

    ddl = model.to_ddl()

    # Check for proper indentation (4 spaces)
    lines = ddl.split('\n')
    column_lines = [line for line in lines if 'id integer' in line or 'name text' in line]

    for line in column_lines:
        # Column definitions should start with 4 spaces
        assert line.startswith('    ')


def test_to_ddl_statement_separation():
    """Test that DDL statements are properly separated."""
    model = CanonicalSchemaModel()

    model.add_table("table1", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("table2", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="table1_id", type="integer", nullable=False)
    ])

    model.add_relationship("table2", "table1_id", "table1", "id")

    ddl = model.to_ddl()

    # Statements should be separated by double newlines
    assert "\n\n" in ddl

    # Split by double newlines and verify we have 3 statements
    # (2 CREATE TABLE + 1 ALTER TABLE)
    statements = ddl.split("\n\n")
    assert len(statements) == 3


def test_to_ddl_table_ordering():
    """Test that tables are ordered consistently (alphabetically by fully qualified name)."""
    model = CanonicalSchemaModel()

    # Add tables in non-alphabetical order
    model.add_table("zebra", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("apple", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("banana", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    ddl = model.to_ddl()

    # Find positions of CREATE TABLE statements
    apple_pos = ddl.find("CREATE TABLE public.apple")
    banana_pos = ddl.find("CREATE TABLE public.banana")
    zebra_pos = ddl.find("CREATE TABLE public.zebra")

    # Verify alphabetical ordering
    assert apple_pos < banana_pos < zebra_pos


# ========== Edge Cases ==========

def test_to_ddl_table_with_reserved_keyword_column():
    """Test DDL generation with column names that might be reserved keywords."""
    model = CanonicalSchemaModel()

    model.add_table("test_table", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="user", type="text", nullable=True),
        Column(name="order", type="text", nullable=True)
    ])

    ddl = model.to_ddl()

    # Column names should be present (not quoted in this implementation)
    assert "user text" in ddl
    assert "order text" in ddl


def test_to_ddl_after_mutations():
    """Test that DDL correctly reflects schema after mutations."""
    model = CanonicalSchemaModel()

    # Create initial schema
    model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="text", nullable=False)
    ])

    model.add_table("orders", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="user_id", type="integer", nullable=False)
    ])

    model.add_relationship("orders", "user_id", "users", "id")

    # Perform mutations
    model.rename_table("users", "customers")
    model.add_column("customers", Column(name="email", type="varchar(255)", nullable=False))

    ddl = model.to_ddl()

    # Verify DDL reflects mutations
    assert "CREATE TABLE public.customers" in ddl
    assert "CREATE TABLE public.users" not in ddl
    assert "email varchar(255) NOT NULL" in ddl
    assert "REFERENCES public.customers (id)" in ddl


def test_to_ddl_constraint_naming():
    """Test that constraint names are generated consistently."""
    model = CanonicalSchemaModel()

    model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    model.add_table("orders", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="user_id", type="integer", nullable=False)
    ])

    model.add_relationship("orders", "user_id", "users", "id")

    ddl = model.to_ddl()

    # Verify PK constraint naming: tablename_pkey
    assert "CONSTRAINT users_pkey PRIMARY KEY" in ddl
    assert "CONSTRAINT orders_pkey PRIMARY KEY" in ddl

    # Verify FK constraint naming: tablename_columnname_fkey
    assert "CONSTRAINT orders_user_id_fkey" in ddl


def test_to_ddl_from_introspection():
    """Test DDL generation from a model built via from_introspection."""
    # Simulate introspection data
    tables_raw = {
        ("public", "customers"): {
            "schema": "public",
            "table": "customers",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "name", "type": "text", "nullable": "NO"},
            ]
        },
        ("public", "orders"): {
            "schema": "public",
            "table": "orders",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "customer_id", "type": "integer", "nullable": "NO"},
            ]
        }
    }

    pks_raw = {
        ("public", "customers"): ["id"],
        ("public", "orders"): ["id"]
    }

    fks_raw = [
        {
            "from_table": ("public", "orders"),
            "from_column": "customer_id",
            "to_table": ("public", "customers"),
            "to_column": "id"
        }
    ]

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)
    ddl = model.to_ddl()

    # Verify DDL generation works with introspected model
    assert "CREATE TABLE public.customers" in ddl
    assert "CREATE TABLE public.orders" in ddl
    assert "orders_customer_id_fkey" in ddl
    assert "REFERENCES public.customers (id)" in ddl
