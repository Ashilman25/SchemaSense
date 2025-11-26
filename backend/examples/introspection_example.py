import sys
from pathlib import Path

# Add backend to path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))


def example_direct_introspection():
    """Example: Direct introspection without caching."""
    print("=" * 60)
    print("Example 1: Direct Introspection")
    print("=" * 60)

    from app.schema.instrospect import (
        introspect_tables_and_columns,
        introspect_primary_keys,
        introspect_foreign_keys
    )
    from app.models.schema_model import CanonicalSchemaModel

    print("\nRunning introspection functions...")


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

    # Build canonical model
    schema_model = CanonicalSchemaModel.from_introspection(
        tables_raw, pks_raw, fks_raw
    )

    print(f"\n✓ Built schema model:")
    print(f"  - Tables: {len(schema_model.tables)}")
    print(f"  - Relationships: {len(schema_model.relationships)}")

    # Display tables
    print("\nTables:")
    for table_name, table in schema_model.tables.items():
        print(f"\n  {table_name}:")
        for col in table.columns:
            flags = []
            if col.is_pk:
                flags.append("PK")
            if col.is_fk:
                flags.append("FK")
            if not col.nullable:
                flags.append("NOT NULL")

            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(f"    - {col.name}: {col.type}{flag_str}")

    # Display relationships
    print("\nRelationships:")
    for rel in schema_model.relationships:
        print(f"  {rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}")


def example_with_caching():
    """Example: Using the caching layer."""
    print("\n\n" + "=" * 60)
    print("Example 2: Using Schema Cache")
    print("=" * 60)

    from app.schema import cache

    # Clear cache first
    cache.clear_schema_cache()
    print("\n✓ Cache cleared")

    # Check cache status
    cached = cache.get_cached_schema()
    print(f"✓ Cache empty: {cached is None}")

    # Simulate data for this example
    from app.models.schema_model import CanonicalSchemaModel, Table, Column, Relationship

    # Create a mock schema model
    customers_table = Table(
        name="customers",
        schema="public",
        columns=[
            Column(name="id", type="integer", is_pk=True, nullable=False),
            Column(name="name", type="text", nullable=False),
        ]
    )

    orders_table = Table(
        name="orders",
        schema="public",
        columns=[
            Column(name="id", type="integer", is_pk=True, nullable=False),
            Column(name="customer_id", type="integer", is_fk=True, nullable=False),
        ]
    )

    schema_model = CanonicalSchemaModel(
        tables={
            "public.customers": customers_table,
            "public.orders": orders_table
        },
        relationships=[
            Relationship(
                from_table="public.orders",
                from_column="customer_id",
                to_table="public.customers",
                to_column="id"
            )
        ]
    )

    # Set in cache
    cache.set_cached_schema(schema_model)
    print("✓ Schema cached")

    # Retrieve from cache
    cached = cache.get_cached_schema()
    print(f"✓ Retrieved from cache: {cached is not None}")
    print(f"  - Same instance: {cached is schema_model}")

    # Display cached schema
    print("\nCached Schema:")
    print(f"  - Tables: {len(cached.tables)}")
    print(f"  - Relationships: {len(cached.relationships)}")


def example_api_serialization():
    """Example: Serializing schema for API response."""
    print("\n\n" + "=" * 60)
    print("Example 3: API Serialization")
    print("=" * 60)

    from app.models.schema_model import CanonicalSchemaModel, Table, Column, Relationship

    # Create schema model
    schema_model = CanonicalSchemaModel(
        tables={
            "public.products": Table(
                name="products",
                schema="public",
                columns=[
                    Column(name="id", type="serial", is_pk=True, nullable=False),
                    Column(name="name", type="text", nullable=False),
                    Column(name="price", type="numeric", nullable=False),
                ]
            )
        },
        relationships=[]
    )

    # Serialize for API
    api_data = schema_model.to_dict_for_api()

    print("\nAPI Response:")
    import json
    print(json.dumps(api_data, indent=2))


if __name__ == "__main__":
    example_direct_introspection()
    example_with_caching()
    example_api_serialization()

    print("\n\n" + "=" * 60)
    print("✓ All examples completed successfully!")
    print("=" * 60)
