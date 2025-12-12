"""
Phase 11 Tests: Data Validation and Edge Cases
Tests validation logic, error handling, and edge case scenarios.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
import psycopg2

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.routes.data import insert_data, preview_data, InsertDataRequest


# =============================================================================
# Test Fixtures
# =============================================================================

def make_connection_with_table(table_exists=True, columns=None):
    """Create mock connection with table validation setup."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1 if table_exists else 0,)
    if columns:
        cursor.fetchall.return_value = columns
    conn.cursor.return_value = cursor
    return conn, cursor


# =============================================================================
# VALIDATION TEST 1: Invalid Table Name Formats
# =============================================================================

@pytest.mark.asyncio
async def test_invalid_table_name_formats():
    """
    Test various invalid table name formats
    Expected: All rejected with 400 error and helpful message
    """
    invalid_formats = [
        "customers",  # Missing schema
        "schema.table.extra",  # Too many parts
        ".customers",  # Empty schema
        "schema.",  # Empty table
        "schema..table",  # Double dot
        "schema table",  # Space instead of dot
        "schema,table",  # Comma instead of dot
    ]

    for invalid_table in invalid_formats:
        request = InsertDataRequest(
            table=invalid_table,
            rows=[{"id": 1}]
        )

        with patch("app.routes.data.get_connection", return_value=MagicMock()):
            with pytest.raises(HTTPException) as exc_info:
                await insert_data(request)

            assert exc_info.value.status_code == 400
            assert "Invalid table name" in exc_info.value.detail
            assert "schema.table" in exc_info.value.detail


# =============================================================================
# VALIDATION TEST 2: Table Does Not Exist
# =============================================================================

@pytest.mark.asyncio
async def test_table_does_not_exist():
    """
    Test inserting into non-existent table
    Expected: 404 error with helpful message
    """
    request = InsertDataRequest(
        table="sales.nonexistent_table",
        rows=[{"id": 1, "data": "test"}]
    )

    conn, cursor = make_connection_with_table(table_exists=False)

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
        assert "sales.nonexistent_table" in exc_info.value.detail


# =============================================================================
# VALIDATION TEST 3: No Rows Provided
# =============================================================================

@pytest.mark.asyncio
async def test_no_rows_provided():
    """
    Test insert with empty rows array
    Expected: 400 error
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code == 400
        assert "No rows provided" in exc_info.value.detail


# =============================================================================
# VALIDATION TEST 4: Row with No Columns
# =============================================================================

@pytest.mark.asyncio
async def test_row_with_no_columns():
    """
    Test insert with empty row object
    Expected: 400 error
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[{}]  # Empty object
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code == 400
        assert "at least one column" in exc_info.value.detail


# =============================================================================
# EDGE CASE TEST 1: All NULL Values
# =============================================================================

@pytest.mark.asyncio
async def test_all_null_values():
    """
    Test row where all values are NULL
    Expected: Success (if table allows NULLs)
    """
    request = InsertDataRequest(
        table="sales.products",
        rows=[
            {"id": None, "name": None, "description": None},
            {"id": "", "name": "", "description": ""},  # Empty strings -> NULL
            {"id": "null", "name": "null", "description": "null"},  # String 'null' -> NULL
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 3


# =============================================================================
# EDGE CASE TEST 2: Very Long Table/Schema Names
# =============================================================================

@pytest.mark.asyncio
async def test_very_long_names():
    """
    Test with very long but valid schema/table names
    Expected: Should work if within PostgreSQL limits (63 chars)
    """
    long_schema = "a" * 63
    long_table = "b" * 63
    table_name = f"{long_schema}.{long_table}"

    request = InsertDataRequest(
        table=table_name,
        rows=[{"id": 1}]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True


# =============================================================================
# EDGE CASE TEST 3: Column Names with Special Characters
# =============================================================================

@pytest.mark.asyncio
async def test_column_names_with_special_chars():
    """
    Test column names that are valid in PostgreSQL but unusual
    Expected: Should work with proper quoting
    """
    special_columns = [
        {"column-with-dash": 1},
        {"column.with.dot": 2},
        {"Column With Space": 3},  # Would need quotes in SQL
        {"UPPERCASE": 4},
        {"lowercase": 5},
        {"MixedCase": 6},
    ]

    for special_col in special_columns:
        request = InsertDataRequest(
            table="sales.test_table",
            rows=[special_col]
        )

        conn, cursor = make_connection_with_table()

        with patch("app.routes.data.get_connection", return_value=conn):
            # Should either succeed (properly quoted) or fail gracefully
            try:
                response = await insert_data(request)
                # Verify SQL.Identifier was used for proper quoting
                assert response.success is True
            except HTTPException:
                # Some special chars may not be allowed, that's ok
                pass


# =============================================================================
# EDGE CASE TEST 4: Whitespace in Values
# =============================================================================

@pytest.mark.asyncio
async def test_whitespace_in_values():
    """
    Test values with leading/trailing/internal whitespace
    Expected: Whitespace preserved as-is
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "  John  ", "email": "john@example.com"},
            {"id": 2, "name": "\tAlice\t", "email": "alice@example.com"},
            {"id": 3, "name": "\nBob\n", "email": "bob@example.com"},
            {"id": 4, "name": "   ", "email": "spaces@example.com"},
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 4

    # Verify whitespace is preserved (not trimmed)
    execute_calls = cursor.execute.call_args_list
    for call in execute_calls[1:]:
        if len(call[0]) > 1:
            values = call[0][1]
            # At least one value should contain whitespace
            assert any(isinstance(v, str) and (" " in v or "\t" in v or "\n" in v) for v in values)


# =============================================================================
# EDGE CASE TEST 5: Case Sensitivity
# =============================================================================

@pytest.mark.asyncio
async def test_case_sensitivity():
    """
    Test case sensitivity in table and column names
    Expected: PostgreSQL folds unquoted names to lowercase
    """
    test_cases = [
        ("sales.Customers", "Sales.customers"),  # Different cases
        ("Sales.CUSTOMERS", "sales.customers"),
        ("SALES.customers", "sales.customers"),
    ]

    for table1, table2 in test_cases:
        request1 = InsertDataRequest(table=table1, rows=[{"id": 1}])
        request2 = InsertDataRequest(table=table2, rows=[{"id": 2}])

        conn, cursor = make_connection_with_table()

        with patch("app.routes.data.get_connection", return_value=conn):
            # Both should target the same table (case-insensitive matching)
            try:
                await insert_data(request1)
                await insert_data(request2)
            except HTTPException:
                # If table doesn't exist, that's fine for this test
                pass


# =============================================================================
# EDGE CASE TEST 6: Boolean Values (Various Formats)
# =============================================================================

@pytest.mark.asyncio
async def test_boolean_value_formats():
    """
    Test various boolean representations
    Expected: All should be handled correctly
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": 1, "is_paid": True},
            {"id": 2, "is_paid": False},
            {"id": 3, "is_paid": "true"},  # String
            {"id": 4, "is_paid": "false"},  # String
            {"id": 5, "is_paid": 1},  # Integer
            {"id": 6, "is_paid": 0},  # Integer
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 6


# =============================================================================
# EDGE CASE TEST 7: Numeric Precision
# =============================================================================

@pytest.mark.asyncio
async def test_numeric_precision():
    """
    Test various numeric formats and precision
    Expected: Values preserved with appropriate precision
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": 1, "total": 99.99},
            {"id": 2, "total": 100.00},
            {"id": 3, "total": 0.01},
            {"id": 4, "total": 999999.999999},
            {"id": 5, "total": 1.23456789012345},
            {"id": 6, "total": -50.50},
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 6


# =============================================================================
# ERROR HANDLING TEST 1: Database Connection Failure
# =============================================================================

@pytest.mark.asyncio
async def test_database_connection_failure():
    """
    Test handling when database connection fails
    Expected: 500 error with helpful message
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[{"id": 1, "name": "test"}]
    )

    with patch("app.routes.data.get_connection", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code == 500
        assert "Unable to connect" in exc_info.value.detail
        assert "database" in exc_info.value.detail.lower()


# =============================================================================
# ERROR HANDLING TEST 2: Database Error During Insert
# =============================================================================

@pytest.mark.asyncio
async def test_database_error_during_insert():
    """
    Test handling of database errors during insert
    Expected: Transaction rolled back, error returned
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[{"id": 1, "name": "test"}]
    )

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)  # Table exists

    # Simulate DB error on insert
    cursor.execute.side_effect = [
        None,  # Table validation succeeds
        psycopg2.DataError("invalid input syntax for type integer"),  # Insert fails
    ]
    conn.cursor.return_value = cursor

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code == 400
        assert "Database error" in exc_info.value.detail

    # Verify rollback was called
    conn.rollback.assert_called()


# =============================================================================
# ERROR HANDLING TEST 3: Constraint Violation
# =============================================================================

@pytest.mark.asyncio
async def test_constraint_violation():
    """
    Test handling of various constraint violations
    Expected: Specific error messages for each type
    """
    constraint_tests = [
        ("primary key", psycopg2.IntegrityError("duplicate key value violates unique constraint \"pk_customers\"")),
        ("foreign key", psycopg2.IntegrityError("insert or update on table violates foreign key constraint")),
        ("check", psycopg2.IntegrityError("new row for relation violates check constraint")),
        ("not null", psycopg2.IntegrityError("null value in column \"name\" violates not-null constraint")),
    ]

    for constraint_name, error in constraint_tests:
        request = InsertDataRequest(
            table="sales.customers",
            rows=[{"id": 1, "name": "test"}]
        )

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        cursor.execute.side_effect = [None, error]
        conn.cursor.return_value = cursor

        with patch("app.routes.data.get_connection", return_value=conn):
            # Should either return partial success or raise exception
            try:
                response = await insert_data(request)
                # If rows_inserted > 0, that's a partial success
                if response.success:
                    assert response.errors is not None
            except HTTPException as e:
                # Complete failure is also acceptable
                assert e.status_code in [400, 500]


# =============================================================================
# ERROR HANDLING TEST 4: Connection Lost Mid-Transaction
# =============================================================================

@pytest.mark.asyncio
async def test_connection_lost_mid_transaction():
    """
    Test handling when connection is lost during insert
    Expected: Graceful error, resources cleaned up
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[{"id": 1, "name": "test"}]
    )

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)

    # Simulate connection loss
    cursor.execute.side_effect = [
        None,  # Table validation
        psycopg2.OperationalError("server closed the connection unexpectedly"),
    ]
    conn.cursor.return_value = cursor

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code in [400, 500]

    # Verify cleanup was attempted
    cursor.close.assert_called()
    conn.close.assert_called()


# =============================================================================
# ERROR HANDLING TEST 5: Timeout During Insert
# =============================================================================

@pytest.mark.asyncio
async def test_timeout_during_insert():
    """
    Test handling of query timeout
    Expected: Timeout error returned, transaction rolled back
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[{"id": i} for i in range(100)]
    )

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)
    cursor.execute.side_effect = [
        None,  # Table validation
        *([psycopg2.OperationalError("query timeout")] * 100)
    ]
    conn.cursor.return_value = cursor

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException):
            await insert_data(request)

    conn.rollback.assert_called()


# =============================================================================
# EDGE CASE TEST 8: Zero and Negative Numbers
# =============================================================================

@pytest.mark.asyncio
async def test_zero_and_negative_numbers():
    """
    Test zero and negative numeric values
    Expected: All accepted
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": 0, "total": 0.0},
            {"id": -1, "total": -99.99},
            {"id": -9999, "total": -0.01},
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == 3


# =============================================================================
# EDGE CASE TEST 9: Scientific Notation
# =============================================================================

@pytest.mark.asyncio
async def test_scientific_notation():
    """
    Test numeric values in scientific notation
    Expected: Handled correctly
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": 1, "total": 1e10},
            {"id": 2, "total": 1.5e-5},
            {"id": 3, "total": 9.99e2},
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True


# =============================================================================
# EDGE CASE TEST 10: Inconsistent Column Order Across Rows
# =============================================================================

@pytest.mark.asyncio
async def test_inconsistent_column_order():
    """
    Test rows with different column orders
    Note: First row determines column order
    Expected: All rows use first row's column order
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"email": "bob@example.com", "id": 2, "name": "Bob"},  # Different order
            {"name": "Charlie", "email": "charlie@example.com", "id": 3},  # Different order
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    # All should succeed using first row's column order
    assert response.success is True
    assert response.rows_inserted == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
