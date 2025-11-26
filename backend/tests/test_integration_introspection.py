"""
Integration test to verify introspection functions work with schema model.
"""
import sys
from pathlib import Path
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.schema_model import CanonicalSchemaModel


def test_integration_full_workflow_with_mock_data():
    """Test the full workflow: introspection results -> canonical model."""

    # Simulate results from introspect_tables_and_columns
    tables_raw = {
        ("public", "customers"): {
            "schema": "public",
            "table": "customers",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "name", "type": "text", "nullable": "NO"},
                {"name": "email", "type": "varchar", "nullable": "YES"},
            ]
        },
        ("public", "orders"): {
            "schema": "public",
            "table": "orders",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "customer_id", "type": "integer", "nullable": "NO"},
                {"name": "order_date", "type": "timestamp", "nullable": "NO"},
                {"name": "total", "type": "numeric", "nullable": "YES"},
            ]
        },
        ("public", "order_items"): {
            "schema": "public",
            "table": "order_items",
            "columns": [
                {"name": "order_id", "type": "integer", "nullable": "NO"},
                {"name": "product_id", "type": "integer", "nullable": "NO"},
                {"name": "quantity", "type": "integer", "nullable": "NO"},
                {"name": "price", "type": "numeric", "nullable": "NO"},
            ]
        },
        ("public", "products"): {
            "schema": "public",
            "table": "products",
            "columns": [
                {"name": "id", "type": "integer", "nullable": "NO"},
                {"name": "name", "type": "text", "nullable": "NO"},
                {"name": "price", "type": "numeric", "nullable": "NO"},
            ]
        }
    }

    # Simulate results from introspect_primary_keys
    pks_raw = {
        ("public", "customers"): ["id"],
        ("public", "orders"): ["id"],
        ("public", "order_items"): ["order_id", "product_id"],
        ("public", "products"): ["id"]
    }

    # Simulate results from introspect_foreign_keys
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
        }
    ]

    # Build canonical model
    model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    # Verify the model is correctly built
    assert len(model.tables) == 4
    assert len(model.relationships) == 3

    # Verify customers table
    customers = model.tables["public.customers"]
    assert customers.name == "customers"
    assert customers.schema == "public"
    assert len(customers.columns) == 3
    assert customers.columns[0].name == "id"
    assert customers.columns[0].is_pk is True
    assert customers.columns[0].is_fk is False
    assert customers.columns[2].name == "email"
    assert customers.columns[2].nullable is True

    # Verify orders table
    orders = model.tables["public.orders"]
    assert len(orders.columns) == 4
    customer_id_col = orders.columns[1]
    assert customer_id_col.name == "customer_id"
    assert customer_id_col.is_pk is False
    assert customer_id_col.is_fk is True  # FK to customers
    assert customer_id_col.nullable is False

    # Verify order_items table (composite PK)
    order_items = model.tables["public.order_items"]
    assert len(order_items.columns) == 4
    # Both order_id and product_id should be PK and FK
    assert order_items.columns[0].name == "order_id"
    assert order_items.columns[0].is_pk is True
    assert order_items.columns[0].is_fk is True
    assert order_items.columns[1].name == "product_id"
    assert order_items.columns[1].is_pk is True
    assert order_items.columns[1].is_fk is True

    # Verify relationships
    rel_from_orders = [r for r in model.relationships if r.from_table == "public.orders"][0]
    assert rel_from_orders.from_column == "customer_id"
    assert rel_from_orders.to_table == "public.customers"
    assert rel_from_orders.to_column == "id"

    rel_from_order_items = [r for r in model.relationships if r.from_table == "public.order_items"]
    assert len(rel_from_order_items) == 2

    print("✅ Integration test passed: Full workflow works correctly!")


if __name__ == "__main__":
    test_integration_full_workflow_with_mock_data()
