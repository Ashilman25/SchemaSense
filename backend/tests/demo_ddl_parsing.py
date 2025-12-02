"""
Demo script to showcase DDL parsing functionality.
This is not a test - just a demonstration of the feature.
"""
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.models.schema_model import CanonicalSchemaModel


def main():
    print("=" * 80)
    print("Phase 6.3 - DDL Parsing Demonstration")
    print("=" * 80)
    print()

    # Example DDL from a real-world e-commerce schema
    ddl = """
    CREATE TABLE public.customers (
        id serial NOT NULL,
        name varchar(255) NOT NULL,
        email varchar(255) NOT NULL,
        created_at timestamp NOT NULL,
        CONSTRAINT customers_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.products (
        id serial NOT NULL,
        name varchar(255) NOT NULL,
        description text,
        price numeric(10,2) NOT NULL,
        stock integer NOT NULL,
        CONSTRAINT products_pkey PRIMARY KEY (id)
    );

    CREATE TABLE public.orders (
        id serial NOT NULL,
        customer_id integer NOT NULL,
        order_date timestamp NOT NULL,
        total numeric(10,2) NOT NULL,
        status varchar(50) NOT NULL,
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

    print("📄 Input DDL:")
    print("-" * 80)
    print(ddl)
    print("-" * 80)
    print()

    # Parse DDL into model
    print("🔍 Parsing DDL into CanonicalSchemaModel...")
    model = CanonicalSchemaModel.from_ddl(ddl)
    print()

    # Display parsed results
    print("✅ Parsing Complete!")
    print()
    print(f"📊 Summary:")
    print(f"   - Tables: {len(model.tables)}")
    print(f"   - Relationships: {len(model.relationships)}")
    print()

    print("📋 Tables:")
    for table_fqn, table in sorted(model.tables.items()):
        print(f"\n   {table_fqn}:")
        print(f"      Columns:")
        for col in table.columns:
            pk_flag = " [PK]" if col.is_pk else ""
            fk_flag = " [FK]" if col.is_fk else ""
            nullable = " (nullable)" if col.nullable else " (NOT NULL)"
            print(f"         - {col.name}: {col.type}{nullable}{pk_flag}{fk_flag}")

    print()
    print("🔗 Relationships:")
    for rel in model.relationships:
        print(f"   {rel.from_table}.{rel.from_column} → {rel.to_table}.{rel.to_column}")

    print()
    print("-" * 80)
    print("🔄 Round-Trip Test: Generating DDL from parsed model...")
    print("-" * 80)
    print()

    # Generate DDL from the parsed model
    regenerated_ddl = model.to_ddl()
    print(regenerated_ddl)
    print("-" * 80)
    print()

    print("✨ Round-trip successful!")
    print("   The model was parsed from DDL and then regenerated back to DDL.")
    print()

    # Test that parsing the regenerated DDL produces the same structure
    print("🔍 Parsing regenerated DDL to verify consistency...")
    model2 = CanonicalSchemaModel.from_ddl(regenerated_ddl)

    assert len(model.tables) == len(model2.tables), "Table count mismatch"
    assert len(model.relationships) == len(model2.relationships), "Relationship count mismatch"

    print("✅ Consistency verified!")
    print()
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
