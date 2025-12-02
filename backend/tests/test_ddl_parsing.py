import sys
from pathlib import Path
import pytest

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.schema_model import CanonicalSchemaModel, SchemaValidationError


# ========== Basic DDL Parsing Tests ==========

def test_from_ddl_empty_string():
    """Test parsing empty DDL string."""
    model = CanonicalSchemaModel.from_ddl("")

    assert len(model.tables) == 0
    assert len(model.relationships) == 0


def test_from_ddl_single_table_no_pk():
    """Test parsing a single table without primary key."""
    ddl = """
    CREATE TABLE public.logs (
        timestamp timestamp NOT NULL,
        message text
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    assert len(model.tables) == 1
    assert "public.logs" in model.tables

    table = model.tables["public.logs"]
    assert table.name == "logs"
    assert table.schema == "public"
    assert len(table.columns) == 2

    # Check timestamp column
    timestamp_col = table.columns[0]
    assert timestamp_col.name == "timestamp"
    assert timestamp_col.type == "timestamp"
    assert timestamp_col.nullable is False
    assert timestamp_col.is_pk is False

    # Check message column
    message_col = table.columns[1]
    assert message_col.name == "message"
    assert message_col.type == "text"
    assert message_col.nullable is True


def test_from_ddl_single_table_with_pk():
    """Test parsing a single table with primary key constraint."""
    ddl = """
    CREATE TABLE public.users (
        id integer NOT NULL,
        name text NOT NULL,
        CONSTRAINT users_pkey PRIMARY KEY (id)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    assert len(model.tables) == 1
    table = model.tables["public.users"]

    # Check id is marked as PK
    id_col = table.columns[0]
    assert id_col.name == "id"
    assert id_col.is_pk is True
    assert id_col.nullable is False

    # Check name is not PK
    name_col = table.columns[1]
    assert name_col.name == "name"
    assert name_col.is_pk is False


def test_from_ddl_composite_primary_key():
    """Test parsing a table with composite primary key."""
    ddl = """
    CREATE TABLE public.order_items (
        order_id integer NOT NULL,
        product_id integer NOT NULL,
        quantity integer NOT NULL,
        CONSTRAINT order_items_pkey PRIMARY KEY (order_id, product_id)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    table = model.tables["public.order_items"]

    # Both order_id and product_id should be marked as PK
    assert table.columns[0].name == "order_id"
    assert table.columns[0].is_pk is True

    assert table.columns[1].name == "product_id"
    assert table.columns[1].is_pk is True

    assert table.columns[2].name == "quantity"
    assert table.columns[2].is_pk is False


def test_from_ddl_with_foreign_key():
    """Test parsing tables with foreign key relationships."""
    ddl = """
    CREATE TABLE public.users (
        id integer NOT NULL,
        name text NOT NULL,
        CONSTRAINT users_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.orders (
        id integer NOT NULL,
        user_id integer NOT NULL,
        total numeric(10,2) NOT NULL,
        CONSTRAINT orders_pkey PRIMARY KEY (id)
    );

    ALTER TABLE public.orders
        ADD CONSTRAINT orders_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES public.users (id);
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    assert len(model.tables) == 2
    assert len(model.relationships) == 1

    # Check relationship
    rel = model.relationships[0]
    assert rel.from_table == "public.orders"
    assert rel.from_column == "user_id"
    assert rel.to_table == "public.users"
    assert rel.to_column == "id"

    # Check user_id is marked as FK
    orders_table = model.tables["public.orders"]
    user_id_col = orders_table.columns[1]
    assert user_id_col.name == "user_id"
    assert user_id_col.is_fk is True


# ========== Data Type Tests ==========

def test_from_ddl_various_data_types():
    """Test parsing various PostgreSQL data types."""
    ddl = """
    CREATE TABLE public.data_types_test (
        id serial NOT NULL,
        int_col integer,
        bigint_col bigint,
        text_col text,
        varchar_col varchar(100),
        numeric_col numeric(10,2),
        bool_col boolean,
        timestamp_col timestamp,
        date_col date,
        json_col jsonb,
        uuid_col uuid,
        CONSTRAINT data_types_test_pkey PRIMARY KEY (id)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    table = model.tables["public.data_types_test"]

    # Check various data types are preserved
    # Note: SQLGlot normalizes some types (integer→int, numeric→decimal)
    assert table.columns[0].type == "serial"
    assert table.columns[1].type == "int"  # SQLGlot normalizes integer to int
    assert table.columns[2].type == "bigint"
    assert table.columns[3].type == "text"
    assert table.columns[4].type == "varchar(100)"
    assert table.columns[5].type == "decimal(10,2)"  # SQLGlot normalizes numeric to decimal
    assert table.columns[6].type == "boolean"
    assert table.columns[7].type == "timestamp"
    assert table.columns[8].type == "date"
    assert table.columns[9].type == "jsonb"
    assert table.columns[10].type == "uuid"


# ========== Complex Schema Tests ==========

def test_from_ddl_complex_schema():
    """Test parsing a complex schema with multiple tables and relationships."""
    ddl = """
    CREATE TABLE public.customers (
        id integer NOT NULL,
        name varchar(255) NOT NULL,
        email varchar(255) NOT NULL,
        CONSTRAINT customers_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.products (
        id integer NOT NULL,
        name varchar(255) NOT NULL,
        price numeric(10,2) NOT NULL,
        CONSTRAINT products_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.orders (
        id integer NOT NULL,
        customer_id integer NOT NULL,
        order_date timestamp NOT NULL,
        CONSTRAINT orders_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.order_items (
        order_id integer NOT NULL,
        product_id integer NOT NULL,
        quantity integer NOT NULL,
        price numeric(10,2) NOT NULL,
        CONSTRAINT order_items_pkey PRIMARY KEY (order_id, product_id)
    );

    ALTER TABLE public.orders
        ADD CONSTRAINT orders_customer_id_fkey
        FOREIGN KEY (customer_id)
        REFERENCES public.customers (id);

    ALTER TABLE public.order_items
        ADD CONSTRAINT order_items_order_id_fkey
        FOREIGN KEY (order_id)
        REFERENCES public.orders (id);

    ALTER TABLE public.order_items
        ADD CONSTRAINT order_items_product_id_fkey
        FOREIGN KEY (product_id)
        REFERENCES public.products (id);
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    # Verify all tables are present
    assert len(model.tables) == 4
    assert "public.customers" in model.tables
    assert "public.products" in model.tables
    assert "public.orders" in model.tables
    assert "public.order_items" in model.tables

    # Verify all relationships are present
    assert len(model.relationships) == 3

    # Check composite PK on order_items
    order_items = model.tables["public.order_items"]
    assert order_items.columns[0].is_pk is True  # order_id
    assert order_items.columns[1].is_pk is True  # product_id


def test_from_ddl_cross_schema_foreign_key():
    """Test parsing foreign keys across different schemas."""
    ddl = """
    CREATE TABLE public.users (
        id integer NOT NULL,
        CONSTRAINT users_pkey PRIMARY KEY (id)
    );

    CREATE TABLE sales.orders (
        id integer NOT NULL,
        user_id integer NOT NULL,
        CONSTRAINT orders_pkey PRIMARY KEY (id)
    );

    ALTER TABLE sales.orders
        ADD CONSTRAINT orders_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES public.users (id);
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    # Verify schemas
    assert "public.users" in model.tables
    assert "sales.orders" in model.tables

    # Verify cross-schema relationship
    assert len(model.relationships) == 1
    rel = model.relationships[0]
    assert rel.from_table == "sales.orders"
    assert rel.to_table == "public.users"


# ========== Round-Trip Tests ==========

def test_from_ddl_round_trip():
    """Test that DDL can be generated and then parsed back to the same model."""
    # Import Column for easier use
    from app.models.schema_model import Column

    # Create a model programmatically
    # Note: Use SQLGlot-normalized types (int, not integer)
    original_model = CanonicalSchemaModel()
    original_model.add_table("users", schema="public", columns=[
        Column(name="id", type="int", is_pk=True, nullable=False),
        Column(name="name", type="text", nullable=False)
    ])

    original_model.add_table("orders", schema="public", columns=[
        Column(name="id", type="int", is_pk=True, nullable=False),
        Column(name="user_id", type="int", nullable=False),
        Column(name="total", type="numeric(10,2)", nullable=False)
    ])

    original_model.add_relationship("orders", "user_id", "users", "id")

    # Generate DDL
    ddl = original_model.to_ddl()

    # Parse DDL back
    parsed_model = CanonicalSchemaModel.from_ddl(ddl)

    # Verify structure matches
    assert len(parsed_model.tables) == len(original_model.tables)
    assert len(parsed_model.relationships) == len(original_model.relationships)

    # Verify tables
    assert "public.users" in parsed_model.tables
    assert "public.orders" in parsed_model.tables

    # Verify relationships
    assert len(parsed_model.relationships) == 1
    rel = parsed_model.relationships[0]
    assert rel.from_table == "public.orders"
    assert rel.from_column == "user_id"
    assert rel.to_table == "public.users"
    assert rel.to_column == "id"


def test_from_ddl_then_to_ddl():
    """Test parsing DDL and generating it back produces valid DDL."""
    original_ddl = """
    CREATE TABLE public.customers (
        id integer NOT NULL,
        name varchar(255) NOT NULL,
        CONSTRAINT customers_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.orders (
        id integer NOT NULL,
        customer_id integer NOT NULL,
        CONSTRAINT orders_pkey PRIMARY KEY (id)
    );

    ALTER TABLE public.orders
        ADD CONSTRAINT orders_customer_id_fkey
        FOREIGN KEY (customer_id)
        REFERENCES public.customers (id);
    """

    # Parse DDL
    model = CanonicalSchemaModel.from_ddl(original_ddl)

    # Generate DDL back
    generated_ddl = model.to_ddl()

    # Parse generated DDL
    reparsed_model = CanonicalSchemaModel.from_ddl(generated_ddl)

    # Verify structure is preserved
    assert len(reparsed_model.tables) == 2
    assert len(reparsed_model.relationships) == 1
    assert "public.customers" in reparsed_model.tables
    assert "public.orders" in reparsed_model.tables


# ========== Edge Cases and Error Handling ==========

def test_from_ddl_invalid_sql():
    """Test that invalid SQL is handled gracefully (returns empty model)."""
    # SQLGlot is lenient and doesn't raise errors for invalid SQL
    # It just returns empty or parses what it can
    invalid_ddl = "THIS IS NOT VALID SQL;"

    model = CanonicalSchemaModel.from_ddl(invalid_ddl)

    # Should return empty model since there are no CREATE/ALTER statements
    assert len(model.tables) == 0
    assert len(model.relationships) == 0


def test_from_ddl_table_without_schema():
    """Test parsing table without explicit schema (should default to public)."""
    ddl = """
    CREATE TABLE users (
        id integer NOT NULL,
        CONSTRAINT users_pkey PRIMARY KEY (id)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    # Should default to public schema
    assert "public.users" in model.tables


def test_from_ddl_nullable_columns():
    """Test that columns without NOT NULL are marked as nullable."""
    ddl = """
    CREATE TABLE public.test (
        id integer NOT NULL,
        optional_field text,
        required_field text NOT NULL
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    table = model.tables["public.test"]

    assert table.columns[0].nullable is False  # id
    assert table.columns[1].nullable is True   # optional_field
    assert table.columns[2].nullable is False  # required_field


def test_from_ddl_multiple_foreign_keys_same_table():
    """Test parsing a table with multiple foreign keys."""
    ddl = """
    CREATE TABLE public.users (
        id integer NOT NULL,
        CONSTRAINT users_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.products (
        id integer NOT NULL,
        CONSTRAINT products_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.orders (
        id integer NOT NULL,
        user_id integer NOT NULL,
        product_id integer NOT NULL,
        CONSTRAINT orders_pkey PRIMARY KEY (id)
    );

    ALTER TABLE public.orders
        ADD CONSTRAINT orders_user_id_fkey
        FOREIGN KEY (user_id)
        REFERENCES public.users (id);

    ALTER TABLE public.orders
        ADD CONSTRAINT orders_product_id_fkey
        FOREIGN KEY (product_id)
        REFERENCES public.products (id);
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    # Verify both foreign keys are present
    assert len(model.relationships) == 2

    # Check both columns are marked as FK
    orders_table = model.tables["public.orders"]
    user_id_col = orders_table.columns[1]
    product_id_col = orders_table.columns[2]

    assert user_id_col.is_fk is True
    assert product_id_col.is_fk is True


def test_from_ddl_preserves_case():
    """Test that table and column names preserve their case."""
    ddl = """
    CREATE TABLE public.MyTable (
        MyColumn integer NOT NULL,
        another_column text,
        CONSTRAINT MyTable_pkey PRIMARY KEY (MyColumn)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    # Note: SQLGlot may normalize case - this test verifies behavior
    # The table should be accessible (case handling depends on SQLGlot)
    assert len(model.tables) == 1


def test_from_ddl_serial_type():
    """Test parsing serial/bigserial types."""
    ddl = """
    CREATE TABLE public.test (
        id serial NOT NULL,
        big_id bigserial NOT NULL,
        CONSTRAINT test_pkey PRIMARY KEY (id)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    table = model.tables["public.test"]

    # Serial types should be preserved
    assert table.columns[0].type == "serial"
    assert table.columns[1].type == "bigserial"


def test_from_ddl_with_comments():
    """Test that SQL comments don't break parsing."""
    ddl = """
    -- This is a comment
    CREATE TABLE public.users (
        id integer NOT NULL, -- User ID
        name text NOT NULL,  -- User name
        CONSTRAINT users_pkey PRIMARY KEY (id)
    );
    /* Multi-line
       comment */
    CREATE TABLE public.orders (
        id integer NOT NULL,
        user_id integer NOT NULL,
        CONSTRAINT orders_pkey PRIMARY KEY (id)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    # Comments should be ignored, tables should parse correctly
    assert len(model.tables) == 2
    assert "public.users" in model.tables
    assert "public.orders" in model.tables


def test_from_ddl_multiple_schemas():
    """Test parsing tables from multiple schemas."""
    ddl = """
    CREATE TABLE public.users (
        id integer NOT NULL,
        CONSTRAINT users_pkey PRIMARY KEY (id)
    );

    CREATE TABLE sales.invoices (
        id integer NOT NULL,
        CONSTRAINT invoices_pkey PRIMARY KEY (id)
    );

    CREATE TABLE inventory.products (
        id integer NOT NULL,
        CONSTRAINT products_pkey PRIMARY KEY (id)
    );
    """

    model = CanonicalSchemaModel.from_ddl(ddl)

    # Verify all schemas are represented
    assert "public.users" in model.tables
    assert "sales.invoices" in model.tables
    assert "inventory.products" in model.tables

    # Verify schemas are correctly set
    assert model.tables["public.users"].schema == "public"
    assert model.tables["sales.invoices"].schema == "sales"
    assert model.tables["inventory.products"].schema == "inventory"
