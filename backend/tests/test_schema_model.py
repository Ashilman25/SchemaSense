import sys
from pathlib import Path
import pytest

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.schema_model import CanonicalSchemaModel, Table, Column, Relationship


def test_from_introspection_simple_schema():
    """Test building canonical model from simple schema with one table."""
    tables_raw = {
        ("public", "customers"): {
            "schema": "public",
            "table": "customers",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "name", "type": "text", "nullable": "YES"},
            ]
        }
    }
    pks_raw = {
        ("public", "customers"): ["id"]
    }
    fks_raw = []

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    assert len(model.tables) == 1
    assert "public.customers" in model.tables

    table = model.tables["public.customers"]
    assert table.name == "customers"
    assert table.schema == "public"
    assert len(table.columns) == 2

    # Check id column
    id_col = table.columns[0]
    assert id_col.name == "id"
    assert id_col.type == "integer"
    assert id_col.is_pk is True
    assert id_col.is_fk is False
    assert id_col.nullable is False  # "NO" -> False

    # Check name column
    name_col = table.columns[1]
    assert name_col.name == "name"
    assert name_col.type == "text"
    assert name_col.is_pk is False
    assert name_col.is_fk is False
    assert name_col.nullable is True  # "YES" -> True

    assert len(model.relationships) == 0


def test_from_introspection_with_foreign_keys():
    """Test building canonical model with foreign key relationships."""
    tables_raw = {
        ("public", "customers"): {
            "schema": "public",
            "table": "customers",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "name", "type": "text", "nullable": "YES"},
            ]
        },
        ("public", "orders"): {
            "schema": "public",
            "table": "orders",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "customer_id", "type": "integer", "nullable": "NO"},
                {"name": "total", "type": "numeric", "nullable": "YES"},
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

    assert len(model.tables) == 2
    assert "public.customers" in model.tables
    assert "public.orders" in model.tables

    # Check orders table has FK column marked
    orders_table = model.tables["public.orders"]
    customer_id_col = orders_table.columns[1]
    assert customer_id_col.name == "customer_id"
    assert customer_id_col.is_pk is False
    assert customer_id_col.is_fk is True  # Should be marked as FK

    # Check relationships
    assert len(model.relationships) == 1
    rel = model.relationships[0]
    assert rel.from_table == "public.orders"
    assert rel.from_column == "customer_id"
    assert rel.to_table == "public.customers"
    assert rel.to_column == "id"


def test_from_introspection_composite_primary_key():
    """Test table with composite (multi-column) primary key."""
    tables_raw = {
        ("public", "order_items"): {
            "schema": "public",
            "table": "order_items",
            "columns": [
                {"name": "order_id", "type": "integer", "nullable": "NO"},
                {"name": "product_id", "type": "integer", "nullable": "NO"},
                {"name": "quantity", "type": "integer", "nullable": "NO"},
            ]
        }
    }
    pks_raw = {
        ("public", "order_items"): ["order_id", "product_id"]
    }
    fks_raw = []

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    table = model.tables["public.order_items"]

    # Both order_id and product_id should be marked as PK
    assert table.columns[0].name == "order_id"
    assert table.columns[0].is_pk is True
    assert table.columns[1].name == "product_id"
    assert table.columns[1].is_pk is True
    assert table.columns[2].name == "quantity"
    assert table.columns[2].is_pk is False


def test_from_introspection_multiple_schemas():
    """Test tables across different schemas."""
    tables_raw = {
        ("public", "users"): {
            "schema": "public",
            "table": "users",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
            ]
        },
        ("sales", "invoices"): {
            "schema": "sales",
            "table": "invoices",
            "columns": [
                {"name": "invoice_id", "type": "integer", "nullable": "NO"},
            ]
        }
    }
    pks_raw = {
        ("public", "users"): ["id"],
        ("sales", "invoices"): ["invoice_id"]
    }
    fks_raw = []

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    assert len(model.tables) == 2
    assert "public.users" in model.tables
    assert "sales.invoices" in model.tables

    assert model.tables["public.users"].schema == "public"
    assert model.tables["sales.invoices"].schema == "sales"


def test_from_introspection_cross_schema_foreign_key():
    """Test foreign key relationship across different schemas."""
    tables_raw = {
        ("public", "customers"): {
            "schema": "public",
            "table": "customers",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
            ]
        },
        ("sales", "orders"): {
            "schema": "sales",
            "table": "orders",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "customer_id", "type": "integer", "nullable": "NO"},
            ]
        }
    }
    pks_raw = {
        ("public", "customers"): ["id"],
        ("sales", "orders"): ["id"]
    }
    fks_raw = [
        {
            "from_table": ("sales", "orders"),
            "from_column": "customer_id",
            "to_table": ("public", "customers"),
            "to_column": "id"
        }
    ]

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    assert len(model.relationships) == 1
    rel = model.relationships[0]
    assert rel.from_table == "sales.orders"
    assert rel.to_table == "public.customers"


def test_from_introspection_column_both_pk_and_fk():
    """Test column that is both primary key and foreign key."""
    tables_raw = {
        ("public", "parent"): {
            "schema": "public",
            "table": "parent",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
            ]
        },
        ("public", "child"): {
            "schema": "public",
            "table": "child",
            "columns": [
                {"name": "parent_id", "type": "integer", "nullable": "NO"},
            ]
        }
    }
    pks_raw = {
        ("public", "parent"): ["id"],
        ("public", "child"): ["parent_id"]  # PK that is also FK
    }
    fks_raw = [
        {
            "from_table": ("public", "child"),
            "from_column": "parent_id",
            "to_table": ("public", "parent"),
            "to_column": "id"
        }
    ]

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    child_table = model.tables["public.child"]
    parent_id_col = child_table.columns[0]

    # Column should be marked as both PK and FK
    assert parent_id_col.name == "parent_id"
    assert parent_id_col.is_pk is True
    assert parent_id_col.is_fk is True


def test_from_introspection_table_no_primary_key():
    """Test table without a primary key (edge case)."""
    tables_raw = {
        ("public", "logs"): {
            "schema": "public",
            "table": "logs",
            "columns": [
                {"name": "timestamp", "type": "timestamp", "nullable": "NO"},
                {"name": "message", "type": "text", "nullable": "YES"},
            ]
        }
    }
    pks_raw = {}  # No primary key
    fks_raw = []

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    table = model.tables["public.logs"]
    # All columns should have is_pk = False
    assert all(col.is_pk is False for col in table.columns)


def test_from_introspection_multiple_foreign_keys_same_table():
    """Test table with multiple foreign keys."""
    tables_raw = {
        ("public", "users"): {
            "schema": "public",
            "table": "users",
            "columns": [{"name": "id", "type": "integer", "nullable": "NO"}]
        },
        ("public", "products"): {
            "schema": "public",
            "table": "products",
            "columns": [{"name": "id", "type": "integer", "nullable": "NO"}]
        },
        ("public", "orders"): {
            "schema": "public",
            "table": "orders",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "user_id", "type": "integer", "nullable": "NO"},
                {"name": "product_id", "type": "integer", "nullable": "NO"},
            ]
        }
    }
    pks_raw = {
        ("public", "users"): ["id"],
        ("public", "products"): ["id"],
        ("public", "orders"): ["id"]
    }
    fks_raw = [
        {
            "from_table": ("public", "orders"),
            "from_column": "user_id",
            "to_table": ("public", "users"),
            "to_column": "id"
        },
        {
            "from_table": ("public", "orders"),
            "from_column": "product_id",
            "to_table": ("public", "products"),
            "to_column": "id"
        }
    ]

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    orders_table = model.tables["public.orders"]
    # Both user_id and product_id should be marked as FK
    user_id_col = orders_table.columns[1]
    product_id_col = orders_table.columns[2]

    assert user_id_col.name == "user_id"
    assert user_id_col.is_fk is True
    assert product_id_col.name == "product_id"
    assert product_id_col.is_fk is True

    # Should have 2 relationships
    assert len(model.relationships) == 2


def test_from_introspection_empty_database():
    """Test with empty database (no tables)."""
    tables_raw = {}
    pks_raw = {}
    fks_raw = []

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    assert len(model.tables) == 0
    assert len(model.relationships) == 0


def test_from_introspection_complex_schema():
    """Test a more complex schema with multiple interrelated tables."""
    tables_raw = {
        ("public", "customers"): {
            "schema": "public",
            "table": "customers",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "name", "type": "text", "nullable": "NO"},
            ]
        },
        ("public", "products"): {
            "schema": "public",
            "table": "products",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "category_id", "type": "integer", "nullable": "YES"},
            ]
        },
        ("public", "categories"): {
            "schema": "public",
            "table": "categories",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
            ]
        },
        ("public", "orders"): {
            "schema": "public",
            "table": "orders",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "customer_id", "type": "integer", "nullable": "NO"},
            ]
        },
        ("public", "order_items"): {
            "schema": "public",
            "table": "order_items",
            "columns": [
                {"name": "order_id", "type": "integer", "nullable": "NO"},
                {"name": "product_id", "type": "integer", "nullable": "NO"},
                {"name": "quantity", "type": "integer", "nullable": "NO"},
            ]
        }
    }
    pks_raw = {
        ("public", "customers"): ["id"],
        ("public", "products"): ["id"],
        ("public", "categories"): ["id"],
        ("public", "orders"): ["id"],
        ("public", "order_items"): ["order_id", "product_id"]
    }
    fks_raw = [
        {
            "from_table": ("public", "orders"),
            "from_column": "customer_id",
            "to_table": ("public", "customers"),
            "to_column": "id"
        },
        {
            "from_table": ("public", "order_items"),
            "from_column": "order_id",
            "to_table": ("public", "orders"),
            "to_column": "id"
        },
        {
            "from_table": ("public", "order_items"),
            "from_column": "product_id",
            "to_table": ("public", "products"),
            "to_column": "id"
        },
        {
            "from_table": ("public", "products"),
            "from_column": "category_id",
            "to_table": ("public", "categories"),
            "to_column": "id"
        }
    ]

    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    # Verify structure
    assert len(model.tables) == 5
    assert len(model.relationships) == 4

    # Verify order_items has composite PK
    order_items = model.tables["public.order_items"]
    assert order_items.columns[0].is_pk is True  # order_id
    assert order_items.columns[1].is_pk is True  # product_id
    assert order_items.columns[0].is_fk is True  # also FK
    assert order_items.columns[1].is_fk is True  # also FK

    # Verify products has nullable FK
    products = model.tables["public.products"]
    category_id_col = products.columns[1]
    assert category_id_col.name == "category_id"
    assert category_id_col.is_fk is True
    assert category_id_col.nullable is True  # "YES" -> True
