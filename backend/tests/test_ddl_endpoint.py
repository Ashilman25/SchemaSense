import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.models.schema_model import CanonicalSchemaModel, Table, Column, Relationship


client = TestClient(app)


def test_ddl_endpoint_returns_ddl():
    """Test that /api/schema/ddl endpoint returns DDL text."""
    # Create a mock schema model
    mock_model = CanonicalSchemaModel()
    mock_model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="text", nullable=False)
    ])

    # Mock get_or_refresh_schema to return our model
    with patch('app.routes.schema.get_or_refresh_schema') as mock_refresh:
        with patch('app.routes.schema.get_connection') as mock_conn:
            mock_refresh.return_value = mock_model
            mock_conn.return_value = MagicMock()

            response = client.get("/api/schema/ddl")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "ddl" in data
    assert "table_count" in data
    assert "relationship_count" in data

    # Verify DDL content
    assert "CREATE TABLE public.users" in data["ddl"]
    assert "id integer NOT NULL" in data["ddl"]
    assert "CONSTRAINT users_pkey PRIMARY KEY (id)" in data["ddl"]

    # Verify metadata
    assert data["table_count"] == 1
    assert data["relationship_count"] == 0


def test_ddl_endpoint_with_relationships():
    """Test DDL endpoint with foreign key relationships."""
    mock_model = CanonicalSchemaModel()

    mock_model.add_table("users", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False)
    ])

    mock_model.add_table("orders", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="user_id", type="integer", nullable=False)
    ])

    mock_model.add_relationship("orders", "user_id", "users", "id")

    with patch('app.routes.schema.get_or_refresh_schema') as mock_refresh:
        with patch('app.routes.schema.get_connection') as mock_conn:
            mock_refresh.return_value = mock_model
            mock_conn.return_value = MagicMock()

            response = client.get("/api/schema/ddl")

    assert response.status_code == 200
    data = response.json()

    # Verify DDL contains foreign key
    assert "ALTER TABLE public.orders" in data["ddl"]
    assert "FOREIGN KEY (user_id)" in data["ddl"]
    assert "REFERENCES public.users (id)" in data["ddl"]

    # Verify metadata
    assert data["table_count"] == 2
    assert data["relationship_count"] == 1


def test_ddl_endpoint_empty_schema():
    """Test DDL endpoint with empty schema."""
    mock_model = CanonicalSchemaModel()

    with patch('app.routes.schema.get_or_refresh_schema') as mock_refresh:
        with patch('app.routes.schema.get_connection') as mock_conn:
            mock_refresh.return_value = mock_model
            mock_conn.return_value = MagicMock()

            response = client.get("/api/schema/ddl")

    assert response.status_code == 200
    data = response.json()

    # Verify empty schema
    assert data["ddl"] == ""
    assert data["table_count"] == 0
    assert data["relationship_count"] == 0


def test_ddl_endpoint_complex_schema():
    """Test DDL endpoint with complex multi-table schema."""
    mock_model = CanonicalSchemaModel()

    # Create a complex schema
    mock_model.add_table("customers", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="varchar(255)", nullable=False)
    ])

    mock_model.add_table("products", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="name", type="varchar(255)", nullable=False)
    ])

    mock_model.add_table("orders", schema="public", columns=[
        Column(name="id", type="integer", is_pk=True, nullable=False),
        Column(name="customer_id", type="integer", nullable=False)
    ])

    mock_model.add_table("order_items", schema="public", columns=[
        Column(name="order_id", type="integer", is_pk=True, nullable=False),
        Column(name="product_id", type="integer", is_pk=True, nullable=False),
        Column(name="quantity", type="integer", nullable=False)
    ])

    mock_model.add_relationship("orders", "customer_id", "customers", "id")
    mock_model.add_relationship("order_items", "order_id", "orders", "id")
    mock_model.add_relationship("order_items", "product_id", "products", "id")

    with patch('app.routes.schema.get_or_refresh_schema') as mock_refresh:
        with patch('app.routes.schema.get_connection') as mock_conn:
            mock_refresh.return_value = mock_model
            mock_conn.return_value = MagicMock()

            response = client.get("/api/schema/ddl")

    assert response.status_code == 200
    data = response.json()

    # Verify all tables are in DDL
    assert "CREATE TABLE public.customers" in data["ddl"]
    assert "CREATE TABLE public.products" in data["ddl"]
    assert "CREATE TABLE public.orders" in data["ddl"]
    assert "CREATE TABLE public.order_items" in data["ddl"]

    # Verify all foreign keys are in DDL
    assert "orders_customer_id_fkey" in data["ddl"]
    assert "order_items_order_id_fkey" in data["ddl"]
    assert "order_items_product_id_fkey" in data["ddl"]

    # Verify metadata
    assert data["table_count"] == 4
    assert data["relationship_count"] == 3


def test_ddl_endpoint_handles_db_error():
    """Test that DDL endpoint handles database connection errors gracefully."""
    with patch('app.routes.schema.get_connection') as mock_conn:
        mock_conn.side_effect = RuntimeError("Database connection failed")

        response = client.get("/api/schema/ddl")

    assert response.status_code == 503
    assert "Database connection unavailable" in response.json()["detail"]


def test_ddl_endpoint_handles_general_error():
    """Test that DDL endpoint handles general errors gracefully."""
    with patch('app.routes.schema.get_connection') as mock_conn:
        with patch('app.routes.schema.get_or_refresh_schema') as mock_refresh:
            mock_conn.return_value = MagicMock()
            mock_refresh.side_effect = Exception("Unexpected error")

            response = client.get("/api/schema/ddl")

    assert response.status_code == 500
    assert "Failed to generate DDL" in response.json()["detail"]
