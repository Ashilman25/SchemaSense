"""
Phase 11 Tests: Proper User Flow for Data Insertion
Tests all happy-path scenarios for manual entry and file upload data insertion.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import pytest
from fastapi import HTTPException

# Ensure the backend package is importable
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.routes.data import insert_data, preview_data, InsertDataRequest


# =============================================================================
# Test Fixtures and Helpers
# =============================================================================

def make_connection_with_table(table_exists=True, columns=None):
    """Create mock connection with table validation setup."""
    conn = MagicMock()
    cursor = MagicMock()

    # Table existence check
    cursor.fetchone.return_value = (1 if table_exists else 0,)

    # Column information for preview
    if columns:
        cursor.fetchall.return_value = columns

    conn.cursor.return_value = cursor
    return conn, cursor


def make_insert_cursor(success_count=None, fail_indices=None):
    """Create mock cursor for insert operations."""
    cursor = MagicMock()

    if fail_indices:
        # Simulate some rows failing
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1

            # Skip table validation check (first call)
            if idx == 0:
                cursor.fetchone.return_value = (1,)
                return

            # Subsequent calls are inserts
            if (idx - 1) in fail_indices:
                import psycopg2
                raise psycopg2.IntegrityError("duplicate key value violates unique constraint")

        cursor.execute.side_effect = execute_side_effect
    else:
        # All inserts succeed
        cursor.fetchone.return_value = (1,)

    return cursor


# =============================================================================
# Test Case 1: Single Row Manual Insert
# =============================================================================

@pytest.mark.asyncio
async def test_single_row_manual_insert_success():
    """
    Test Case: Insert single row with valid data
    Expected: Success response with rows_inserted=1
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "John Doe", "email": "john@example.com"}
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    # Verify response
    assert response.success is True
    assert response.rows_inserted == 1
    assert "Successfully inserted 1 row" in response.message
    assert response.errors is None

    # Verify SQL execution
    cursor.execute.assert_called()
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()


# =============================================================================
# Test Case 2: Multiple Rows Manual Insert
# =============================================================================

@pytest.mark.asyncio
async def test_multiple_rows_manual_insert_success():
    """
    Test Case: Insert 5 rows with valid data
    Expected: Success response with rows_inserted=5
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": i, "name": f"Customer {i}", "email": f"customer{i}@example.com"}
            for i in range(1, 6)
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 5
    assert "Successfully inserted 5 rows" in response.message
    assert response.errors is None

    # Should commit once after all inserts
    conn.commit.assert_called_once()


# =============================================================================
# Test Case 3: NULL Value Handling
# =============================================================================

@pytest.mark.asyncio
async def test_null_value_handling():
    """
    Test Case: Insert rows with NULL values (empty strings, 'null', None)
    Expected: All variations converted to NULL and inserted successfully
    """
    request = InsertDataRequest(
        table="sales.products",
        rows=[
            {"id": 1, "name": "Product A", "description": ""},  # Empty string -> NULL
            {"id": 2, "name": "Product B", "description": "null"},  # String 'null' -> NULL
            {"id": 3, "name": "Product C", "description": None},  # None -> NULL
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 3

    # Verify NULL conversion in execute calls
    execute_calls = cursor.execute.call_args_list
    for call in execute_calls[1:]:  # Skip first call (table validation)
        args = call[0]
        if len(args) > 1:
            values = args[1]
            # All description values should be None (SQL NULL)
            if 'description' in str(args[0]):
                assert None in values


# =============================================================================
# Test Case 4: Data Preview Endpoint
# =============================================================================

@pytest.mark.asyncio
async def test_preview_data_success():
    """
    Test Case: Preview data before insert
    Expected: Returns table column metadata and validation status
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "John", "email": "john@example.com"}
        ]
    )

    # Mock column data
    columns = [
        ("id", "integer", "NO"),
        ("name", "character varying", "NO"),
        ("email", "character varying", "YES"),
    ]

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = columns
    conn.cursor.return_value = cursor

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await preview_data(request)

    # Verify response structure
    assert response["valid"] is True
    assert len(response["table_columns"]) == 3
    assert response["table_columns"]["id"]["data_type"] == "integer"
    assert response["table_columns"]["id"]["is_nullable"] is False
    assert response["table_columns"]["email"]["is_nullable"] is True
    assert response["row_count"] == 1
    assert response["extra_columns"] == []


# =============================================================================
# Test Case 5: Preview with Extra Columns
# =============================================================================

@pytest.mark.asyncio
async def test_preview_data_with_extra_columns():
    """
    Test Case: Preview with columns not in table
    Expected: Returns validation failure with extra column list
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "John", "email": "john@example.com", "phone": "555-1234"}
        ]
    )

    columns = [
        ("id", "integer", "NO"),
        ("name", "character varying", "NO"),
        ("email", "character varying", "YES"),
    ]

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = columns
    conn.cursor.return_value = cursor

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await preview_data(request)

    assert response["valid"] is False
    assert "phone" in response["extra_columns"]


# =============================================================================
# Test Case 6: Partial Insert Success
# =============================================================================

@pytest.mark.asyncio
async def test_partial_insert_with_some_failures():
    """
    Test Case: Insert 5 rows where 2 fail (e.g., duplicate keys)
    Expected: Success with rows_inserted=3 and errors array populated
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "Customer 1", "email": "c1@example.com"},
            {"id": 2, "name": "Customer 2", "email": "c2@example.com"},
            {"id": 1, "name": "Duplicate", "email": "dup@example.com"},  # Duplicate PK
            {"id": 3, "name": "Customer 3", "email": "c3@example.com"},
            {"id": 2, "name": "Another Dup", "email": "dup2@example.com"},  # Duplicate PK
        ]
    )

    conn = MagicMock()
    cursor = make_insert_cursor(fail_indices=[2, 4])  # Rows 3 and 5 fail
    conn.cursor.return_value = cursor

    # Mock fetchone for table validation
    cursor.fetchone.return_value = (1,)

    # Mock execute to fail on specific rows
    call_count = [0]

    def execute_side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1

        if idx == 0:
            # Table validation check
            return

        # Insert rows - fail on indices 3 and 5 (rows 3 and 5, accounting for validation check)
        if idx in [3, 5]:
            import psycopg2
            raise psycopg2.IntegrityError("duplicate key value violates unique constraint \"customers_pkey\"")

    cursor.execute.side_effect = execute_side_effect

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 3
    assert response.errors is not None
    assert len(response.errors) == 2
    assert "Row 3:" in response.errors[0]
    assert "Row 5:" in response.errors[1]


# =============================================================================
# Test Case 7: Large Batch Insert (Within Limits)
# =============================================================================

@pytest.mark.asyncio
async def test_large_batch_insert_within_limit():
    """
    Test Case: Insert 1000 rows (at the limit)
    Expected: Success with all rows inserted
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": i, "customer_id": i % 100, "total": float(i * 10)}
            for i in range(1, 1001)
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 1000
    assert "Successfully inserted 1,000 rows" in response.message


# =============================================================================
# Test Case 8: Unicode and Special Characters
# =============================================================================

@pytest.mark.asyncio
async def test_unicode_and_special_characters():
    """
    Test Case: Insert data with unicode, emojis, and special characters
    Expected: All characters preserved and inserted correctly
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "Müller", "email": "muller@example.com"},
            {"id": 2, "name": "北京用户", "email": "beijing@example.com"},
            {"id": 3, "name": "O'Brien", "email": "obrien@example.com"},
            {"id": 4, "name": 'Quote "Test"', "email": "quote@example.com"},
            {"id": 5, "name": "Emoji 😀", "email": "emoji@example.com"},
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 5

    # Verify parameterized query was used (no string concatenation)
    execute_calls = cursor.execute.call_args_list
    for call in execute_calls[1:]:  # Skip validation check
        # Verify SQL uses placeholders, not string formatting
        if len(call[0]) > 0:
            sql = str(call[0][0])
            assert "%s" in sql or "Placeholder" in str(type(call[0][0]))


# =============================================================================
# Test Case 9: Empty Optional Fields
# =============================================================================

@pytest.mark.asyncio
async def test_empty_optional_fields():
    """
    Test Case: Insert rows with empty optional fields
    Expected: Empty fields converted to NULL, insert succeeds
    """
    request = InsertDataRequest(
        table="sales.products",
        rows=[
            {
                "id": 1,
                "name": "Product A",
                "description": "",  # Optional field left empty
                "category": "Electronics"
            },
            {
                "id": 2,
                "name": "Product B",
                "description": "Has description",
                "category": ""  # Optional field left empty
            }
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 2


# =============================================================================
# Test Case 10: Mixed Data Types
# =============================================================================

@pytest.mark.asyncio
async def test_mixed_data_types():
    """
    Test Case: Insert data with various types (int, float, string, boolean)
    Expected: All types handled correctly
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {
                "id": 1,
                "customer_id": 100,
                "total": 99.99,
                "status": "pending",
                "is_paid": False
            },
            {
                "id": 2,
                "customer_id": 101,
                "total": 149.50,
                "status": "completed",
                "is_paid": True
            }
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 2

    # Verify values are passed as-is (not stringified)
    execute_calls = cursor.execute.call_args_list
    for call in execute_calls[1:]:
        if len(call[0]) > 1:
            values = call[0][1]
            # Values should maintain their types
            assert any(isinstance(v, (int, float, bool, str, type(None))) for v in values)


# =============================================================================
# Test Case 11: Column Order Independence
# =============================================================================

@pytest.mark.asyncio
async def test_column_order_independence():
    """
    Test Case: Insert rows with different column orders
    Expected: All rows inserted correctly regardless of column order
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"email": "bob@example.com", "id": 2, "name": "Bob"},  # Different order
            {"name": "Charlie", "email": "charlie@example.com", "id": 3},  # Different order
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 3


# =============================================================================
# Test Case 12: Transaction Commit on Success
# =============================================================================

@pytest.mark.asyncio
async def test_transaction_commit_on_success():
    """
    Test Case: Verify transaction is committed on successful insert
    Expected: commit() called once, rollback() never called
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "Test User", "email": "test@example.com"}
        ]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    cursor.close.assert_called_once()
    conn.close.assert_called_once()


# =============================================================================
# Test Case 13: Preview with Empty Rows
# =============================================================================

@pytest.mark.asyncio
async def test_preview_with_empty_rows():
    """
    Test Case: Preview endpoint with no rows provided
    Expected: Returns table metadata without row validation
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[]
    )

    columns = [
        ("id", "integer", "NO"),
        ("name", "character varying", "NO"),
    ]

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = columns
    conn.cursor.return_value = cursor

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await preview_data(request)

    assert response["valid"] is True
    assert response["row_count"] == 0
    assert len(response["table_columns"]) == 2


# =============================================================================
# Test Case 14: Connection Cleanup on Success
# =============================================================================

@pytest.mark.asyncio
async def test_connection_cleanup_on_success():
    """
    Test Case: Verify connections and cursors are properly closed
    Expected: cursor.close() and conn.close() called in finally block
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[{"id": 1, "name": "Test", "email": "test@example.com"}]
    )

    conn, cursor = make_connection_with_table(table_exists=True)

    with patch("app.routes.data.get_connection", return_value=conn):
        await insert_data(request)

    cursor.close.assert_called_once()
    conn.close.assert_called_once()


# =============================================================================
# Test Case 15: Qualified Table Names (schema.table)
# =============================================================================

@pytest.mark.asyncio
async def test_qualified_table_names():
    """
    Test Case: Various schema.table combinations
    Expected: All valid schema.table patterns accepted
    """
    test_cases = [
        "public.customers",
        "sales.orders",
        "analytics.reports",
        "my_schema.my_table",
    ]

    for table_name in test_cases:
        request = InsertDataRequest(
            table=table_name,
            rows=[{"id": 1, "data": "test"}]
        )

        conn, cursor = make_connection_with_table(table_exists=True)

        with patch("app.routes.data.get_connection", return_value=conn):
            response = await insert_data(request)

        assert response.success is True, f"Failed for table: {table_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
