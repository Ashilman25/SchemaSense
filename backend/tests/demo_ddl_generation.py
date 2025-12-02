"""
Demo script to showcase DDL generation functionality.
This is not a test - just a demonstration of the feature.
"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.schema_model import CanonicalSchemaModel, Column


def main():
    print("=" * 80)
    print("Phase 6.2 - DDL Generation Demonstration")
    print("=" * 80)
    print()

    # Create a sample e-commerce schema
    model = CanonicalSchemaModel()

    # Create customers table
    model.add_table("customers", schema="public", columns=[
        Column(name="id", type="serial", is_pk=True, nullable=False),
        Column(name="name", type="varchar(255)", nullable=False),
        Column(name="email", type="varchar(255)", nullable=False),
        Column(name="created_at", type="timestamp", nullable=False)
    ])

    # Create products table
    model.add_table("products", schema="public", columns=[
        Column(name="id", type="serial", is_pk=True, nullable=False),
        Column(name="name", type="varchar(255)", nullable=False),
        Column(name="description", type="text", nullable=True),
        Column(name="price", type="numeric(10,2)", nullable=False),
        Column(name="stock", type="integer", nullable=False)
    ])

    # Create orders table
    model.add_table("orders", schema="public", columns=[
        Column(name="id", type="serial", is_pk=True, nullable=False),
        Column(name="customer_id", type="integer", nullable=False),
        Column(name="order_date", type="timestamp", nullable=False),
        Column(name="total", type="numeric(10,2)", nullable=False),
        Column(name="status", type="varchar(50)", nullable=False)
    ])

    # Create order_items table with composite PK
    model.add_table("order_items", schema="public", columns=[
        Column(name="order_id", type="integer", is_pk=True, nullable=False),
        Column(name="product_id", type="integer", is_pk=True, nullable=False),
        Column(name="quantity", type="integer", nullable=False),
        Column(name="price", type="numeric(10,2)", nullable=False)
    ])

    # Add foreign key relationships
    model.add_relationship("orders", "customer_id", "customers", "id")
    model.add_relationship("order_items", "order_id", "orders", "id")
    model.add_relationship("order_items", "product_id", "products", "id")

    # Generate DDL
    ddl = model.to_ddl()

    print("Generated DDL for E-Commerce Schema:")
    print("-" * 80)
    print(ddl)
    print("-" * 80)
    print()
    print(f"Tables: {len(model.tables)}")
    print(f"Relationships: {len(model.relationships)}")
    print()
    print("✅ DDL generation complete!")
    print()


if __name__ == "__main__":
    main()
