"""
Phase 11 Tests: End-to-End Integration Tests
Tests complete user flows from start to finish, including multi-step operations.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.routes.data import insert_data, preview_data, InsertDataRequest


# =============================================================================
# Test Fixtures
# =============================================================================

def make_complete_connection_mock():
    """Create a complete mock connection with all expected behaviors."""
    conn = MagicMock()
    cursor = MagicMock()

    # Track state
    state = {
        "rows_inserted": 0,
        "committed": False,
        "rolled_back": False,
        "closed": False
    }

    def execute_side_effect(*args, **kwargs):
        # Table validation query
        if "information_schema.tables" in str(args[0]):
            cursor.fetchone.return_value = (1,)  # Table exists
            return

        # Column info query for preview
        if "information_schema.columns" in str(args[0]):
            cursor.fetchall.return_value = [
                ("id", "integer", "NO"),
                ("name", "character varying", "NO"),
                ("email", "character varying", "YES"),
            ]
            return

        # Insert query
        state["rows_inserted"] += 1

    cursor.execute.side_effect = execute_side_effect

    def commit_side_effect():
        state["committed"] = True

    def rollback_side_effect():
        state["rolled_back"] = True

    def close_side_effect():
        state["closed"] = True

    conn.cursor.return_value = cursor
    conn.commit.side_effect = commit_side_effect
    conn.rollback.side_effect = rollback_side_effect
    cursor.close.side_effect = close_side_effect
    conn.close.side_effect = close_side_effect

    return conn, cursor, state


# =============================================================================
# INTEGRATION TEST 1: Complete Manual Entry Flow
# =============================================================================

@pytest.mark.asyncio
async def test_complete_manual_entry_flow():
    """
    E2E Test: Complete flow for manual data entry
    Steps:
      1. Preview table structure
      2. Validate data
      3. Insert data
      4. Verify success
    """
    table_name = "sales.customers"

    # Step 1: Preview table structure
    preview_request = InsertDataRequest(
        table=table_name,
        rows=[]
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        preview_response = await preview_data(preview_request)

    # Verify preview response
    assert preview_response["valid"] is True
    assert "id" in preview_response["table_columns"]
    assert "name" in preview_response["table_columns"]
    assert "email" in preview_response["table_columns"]

    # Step 2: User enters data (simulated)
    insert_request = InsertDataRequest(
        table=table_name,
        rows=[
            {"id": 1, "name": "John Doe", "email": "john@example.com"},
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
        ]
    )

    # Step 3: Preview with actual data
    with patch("app.routes.data.get_connection", return_value=conn):
        preview_with_data = await preview_data(insert_request)

    assert preview_with_data["valid"] is True
    assert preview_with_data["row_count"] == 2
    assert len(preview_with_data["extra_columns"]) == 0

    # Step 4: Insert data
    conn, cursor, state = make_complete_connection_mock()  # Fresh connection

    with patch("app.routes.data.get_connection", return_value=conn):
        insert_response = await insert_data(insert_request)

    # Verify insert success
    assert insert_response.success is True
    assert insert_response.rows_inserted == 2
    assert insert_response.errors is None
    assert state["committed"] is True
    assert state["rolled_back"] is False
    assert state["closed"] is True


# =============================================================================
# INTEGRATION TEST 2: File Upload Simulation (CSV)
# =============================================================================

@pytest.mark.asyncio
async def test_csv_upload_simulation():
    """
    E2E Test: Simulate CSV file upload flow
    Steps:
      1. Parse CSV (simulated - frontend responsibility)
      2. Preview parsed data
      3. Validate column mapping
      4. Insert data
    """
    table_name = "sales.customers"

    # Simulated CSV parse result (this would come from frontend)
    parsed_csv_data = [
        {"id": 1, "name": "Alice Brown", "email": "alice@example.com"},
        {"id": 2, "name": "Bob Johnson", "email": "bob@example.com"},
        {"id": 3, "name": "Carol White", "email": "carol@example.com"},
    ]

    # Step 1 & 2: Preview the parsed data
    preview_request = InsertDataRequest(
        table=table_name,
        rows=parsed_csv_data
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        preview_response = await preview_data(preview_request)

    # Verify all columns match
    assert preview_response["valid"] is True
    assert len(preview_response["extra_columns"]) == 0
    assert preview_response["row_count"] == 3

    # Step 3 & 4: Insert the data
    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        insert_response = await insert_data(preview_request)

    assert insert_response.success is True
    assert insert_response.rows_inserted == 3
    assert state["committed"] is True


# =============================================================================
# INTEGRATION TEST 3: File Upload with Column Remapping
# =============================================================================

@pytest.mark.asyncio
async def test_file_upload_with_column_remapping():
    """
    E2E Test: Upload with mismatched column names requiring remapping
    Steps:
      1. Upload file with different column names
      2. Preview shows mismatches
      3. User remaps columns (simulated)
      4. Insert with correct mapping
    """
    table_name = "sales.customers"

    # Original uploaded data (wrong column names)
    original_data = [
        {"customer_id": 1, "full_name": "John Doe", "email_address": "john@example.com"},
    ]

    # Step 1: Preview original data
    preview_request = InsertDataRequest(
        table=table_name,
        rows=original_data
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        preview_response = await preview_data(preview_request)

    # Should show extra columns
    assert preview_response["valid"] is False
    assert "customer_id" in preview_response["extra_columns"]
    assert "full_name" in preview_response["extra_columns"]
    assert "email_address" in preview_response["extra_columns"]

    # Step 2: User remaps columns (frontend maps: customer_id->id, full_name->name, email_address->email)
    remapped_data = [
        {"id": 1, "name": "John Doe", "email": "john@example.com"},
    ]

    # Step 3: Preview with remapped data
    remapped_request = InsertDataRequest(
        table=table_name,
        rows=remapped_data
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        remapped_preview = await preview_data(remapped_request)

    assert remapped_preview["valid"] is True
    assert len(remapped_preview["extra_columns"]) == 0

    # Step 4: Insert remapped data
    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        insert_response = await insert_data(remapped_request)

    assert insert_response.success is True
    assert insert_response.rows_inserted == 1


# =============================================================================
# INTEGRATION TEST 4: Error Recovery Flow
# =============================================================================

@pytest.mark.asyncio
async def test_error_recovery_flow():
    """
    E2E Test: User encounters error and recovers
    Steps:
      1. Attempt insert with invalid data
      2. Receive error
      3. Fix data
      4. Retry successfully
    """
    table_name = "sales.customers"

    # Step 1: First attempt with duplicate PK
    import psycopg2

    def make_failing_connection():
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        cursor.execute.side_effect = [
            None,  # Table validation
            psycopg2.IntegrityError("duplicate key value"),  # First insert fails
        ]
        conn.cursor.return_value = cursor
        return conn

    first_attempt = InsertDataRequest(
        table=table_name,
        rows=[
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
        ]
    )

    with patch("app.routes.data.get_connection", return_value=make_failing_connection()):
        # Should fail
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(first_attempt)

        # Verify it's an appropriate error
        assert exc_info.value.status_code in [400, 500]

    # Step 2: User fixes the data (changes ID)
    corrected_attempt = InsertDataRequest(
        table=table_name,
        rows=[
            {"id": 2, "name": "Alice", "email": "alice@example.com"},
        ]
    )

    # Step 3: Retry with corrected data
    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        retry_response = await insert_data(corrected_attempt)

    # Should succeed
    assert retry_response.success is True
    assert retry_response.rows_inserted == 1


# =============================================================================
# INTEGRATION TEST 5: Partial Success Workflow
# =============================================================================

@pytest.mark.asyncio
async def test_partial_success_workflow():
    """
    E2E Test: Some rows succeed, some fail
    Steps:
      1. Insert batch with mix of valid/invalid rows
      2. Get partial success response
      3. User reviews errors
      4. User re-inserts only failed rows (corrected)
    """
    table_name = "sales.customers"

    # Step 1: Insert batch where some rows will fail
    import psycopg2

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1,)

    call_count = [0]

    def execute_with_failures(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1

        if idx == 0:  # Table validation
            return

        # Rows 2 and 4 fail (indices 2 and 4 after validation)
        if idx in [2, 4]:
            raise psycopg2.IntegrityError("duplicate key")

    cursor.execute.side_effect = execute_with_failures
    conn.cursor.return_value = cursor

    batch_request = InsertDataRequest(
        table=table_name,
        rows=[
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},  # Fails
            {"id": 3, "name": "Carol", "email": "carol@example.com"},
            {"id": 4, "name": "Dave", "email": "dave@example.com"},  # Fails
            {"id": 5, "name": "Eve", "email": "eve@example.com"},
        ]
    )

    with patch("app.routes.data.get_connection", return_value=conn):
        partial_response = await insert_data(batch_request)

    # Step 2: Verify partial success
    assert partial_response.success is True
    assert partial_response.rows_inserted == 3  # 3 out of 5 succeeded
    assert partial_response.errors is not None
    assert len(partial_response.errors) == 2

    # Step 3: User identifies failed rows from error messages
    # Errors should indicate "Row 2:" and "Row 4:"
    assert any("Row 2:" in err for err in partial_response.errors)
    assert any("Row 4:" in err for err in partial_response.errors)

    # Step 4: User corrects and re-inserts failed rows
    conn, cursor, state = make_complete_connection_mock()

    retry_request = InsertDataRequest(
        table=table_name,
        rows=[
            {"id": 20, "name": "Bob Fixed", "email": "bob2@example.com"},
            {"id": 40, "name": "Dave Fixed", "email": "dave2@example.com"},
        ]
    )

    with patch("app.routes.data.get_connection", return_value=conn):
        retry_response = await insert_data(retry_request)

    assert retry_response.success is True
    assert retry_response.rows_inserted == 2


# =============================================================================
# INTEGRATION TEST 6: Large Batch Workflow
# =============================================================================

@pytest.mark.asyncio
async def test_large_batch_workflow():
    """
    E2E Test: Upload and insert large batch (at limit)
    Steps:
      1. Upload 1000 rows
      2. Preview shows 1000 rows
      3. Insert succeeds with all rows
    """
    table_name = "sales.orders"

    # Generate 1000 rows
    large_batch = [
        {"id": i, "customer_id": i % 100, "total": float(i * 10)}
        for i in range(1, 1001)
    ]

    # Step 1: Preview
    preview_request = InsertDataRequest(
        table=table_name,
        rows=large_batch
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        preview_response = await preview_data(preview_request)

    assert preview_response["row_count"] == 1000

    # Step 2: Insert
    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        insert_response = await insert_data(preview_request)

    assert insert_response.success is True
    assert insert_response.rows_inserted == 1000


# =============================================================================
# INTEGRATION TEST 7: Multiple Table Insert Flow
# =============================================================================

@pytest.mark.asyncio
async def test_multiple_table_insert_flow():
    """
    E2E Test: User inserts data into multiple tables in sequence
    Steps:
      1. Insert into customers table
      2. Insert into orders table (references customers)
      3. Insert into order_items table (references orders)
    """
    # Step 1: Insert customers
    customers_request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "Customer A", "email": "a@example.com"},
            {"id": 2, "name": "Customer B", "email": "b@example.com"},
        ]
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        customers_response = await insert_data(customers_request)

    assert customers_response.success is True
    assert customers_response.rows_inserted == 2

    # Step 2: Insert orders
    orders_request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": 101, "customer_id": 1, "total": 99.99},
            {"id": 102, "customer_id": 2, "total": 149.50},
        ]
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        orders_response = await insert_data(orders_request)

    assert orders_response.success is True
    assert orders_response.rows_inserted == 2

    # Step 3: Insert order_items
    items_request = InsertDataRequest(
        table="sales.order_items",
        rows=[
            {"id": 1001, "order_id": 101, "product_id": 5, "quantity": 2},
            {"id": 1002, "order_id": 102, "product_id": 3, "quantity": 1},
        ]
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        items_response = await insert_data(items_request)

    assert items_response.success is True
    assert items_response.rows_inserted == 2


# =============================================================================
# INTEGRATION TEST 8: Preview -> Edit -> Preview -> Insert Flow
# =============================================================================

@pytest.mark.asyncio
async def test_preview_edit_preview_insert_flow():
    """
    E2E Test: User previews, edits data, previews again, then inserts
    Steps:
      1. Initial preview
      2. User notices issue in preview
      3. Edits data
      4. Preview again
      5. Insert
    """
    table_name = "sales.customers"

    # Step 1: Initial preview with problematic data
    initial_request = InsertDataRequest(
        table=table_name,
        rows=[
            {"id": 1, "name": "John", "email": "invalid-email"},  # Invalid email
        ]
    )

    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        initial_preview = await preview_data(initial_request)

    assert initial_preview["row_count"] == 1

    # Step 2: User edits the email
    edited_request = InsertDataRequest(
        table=table_name,
        rows=[
            {"id": 1, "name": "John", "email": "john@example.com"},  # Fixed
        ]
    )

    # Step 3: Preview edited data
    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        edited_preview = await preview_data(edited_request)

    assert edited_preview["valid"] is True

    # Step 4: Insert
    conn, cursor, state = make_complete_connection_mock()

    with patch("app.routes.data.get_connection", return_value=conn):
        final_response = await insert_data(edited_request)

    assert final_response.success is True
    assert final_response.rows_inserted == 1


# =============================================================================
# INTEGRATION TEST 9: Connection State Management
# =============================================================================

@pytest.mark.asyncio
async def test_connection_state_management():
    """
    E2E Test: Verify connections are properly managed across operations
    Steps:
      1. Multiple preview calls
      2. Multiple insert calls
      3. Verify each operation cleans up properly
    """
    table_name = "sales.customers"
    request = InsertDataRequest(
        table=table_name,
        rows=[{"id": 1, "name": "Test", "email": "test@example.com"}]
    )

    # Track all connection closures
    close_counts = {"preview": 0, "insert": 0}

    def make_tracking_connection(operation):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        cursor.fetchall.return_value = [("id", "integer", "NO")]

        def close_side_effect():
            close_counts[operation] += 1

        cursor.close.side_effect = close_side_effect
        conn.close.side_effect = close_side_effect
        conn.cursor.return_value = cursor
        return conn

    # Multiple preview operations
    for i in range(3):
        conn = make_tracking_connection("preview")
        with patch("app.routes.data.get_connection", return_value=conn):
            await preview_data(request)

    assert close_counts["preview"] == 3  # Each preview closed its connection

    # Multiple insert operations
    for i in range(3):
        conn = make_tracking_connection("insert")
        with patch("app.routes.data.get_connection", return_value=conn):
            await insert_data(request)

    assert close_counts["insert"] == 3  # Each insert closed its connection


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
