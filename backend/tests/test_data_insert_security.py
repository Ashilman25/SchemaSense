"""
Phase 11 Tests: Security and Malicious User Flow
Tests all security scenarios, injection attempts, and malicious inputs.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.routes.data import insert_data, preview_data, InsertDataRequest, MAX_ROWS


# =============================================================================
# Test Fixtures
# =============================================================================

def make_connection_with_table(table_exists=True):
    """Create mock connection."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1 if table_exists else 0,)
    conn.cursor.return_value = cursor
    return conn, cursor


# =============================================================================
# SECURITY TEST 1: SQL Injection via Table Name
# =============================================================================

@pytest.mark.asyncio
async def test_sql_injection_via_table_name():
    """
    SECURITY TEST: Attempt SQL injection through table name
    Attack: "sales.customers; DROP TABLE users; --"
    Expected: Rejected by table name validation (must be schema.table format)
    """
    malicious_table_names = [
        "sales.customers; DROP TABLE users; --",
        "sales.customers' OR '1'='1",
        "sales.customers; DELETE FROM customers WHERE 1=1; --",
        "sales.customers\"; DROP TABLE customers; --",
        "public.users; TRUNCATE TABLE users CASCADE; --",
    ]

    for malicious_table in malicious_table_names:
        request = InsertDataRequest(
            table=malicious_table,
            rows=[{"id": 1, "name": "test"}]
        )

        conn, cursor = make_connection_with_table()

        with patch("app.routes.data.get_connection", return_value=conn):
            # Should raise HTTPException due to invalid table format
            with pytest.raises(HTTPException) as exc_info:
                await insert_data(request)

            # Verify it's a validation error, not successful execution
            assert exc_info.value.status_code in [400, 404]


# =============================================================================
# SECURITY TEST 2: SQL Injection via Column Names
# =============================================================================

@pytest.mark.asyncio
async def test_sql_injection_via_column_names():
    """
    SECURITY TEST: Attempt SQL injection through column names
    Attack: Use malicious column names in row data
    Expected: Parameterized queries prevent injection
    """
    malicious_columns = [
        {"id; DROP TABLE users; --": 1, "name": "test"},
        {"id": 1, "name' OR '1'='1": "test"},
        {"id\"; DROP TABLE customers; --": 1},
    ]

    for malicious_row in malicious_columns:
        request = InsertDataRequest(
            table="sales.customers",
            rows=[malicious_row]
        )

        conn, cursor = make_connection_with_table()

        with patch("app.routes.data.get_connection", return_value=conn):
            # Should either succeed (treating as column name) or fail safely
            # But should NEVER execute the malicious SQL
            try:
                response = await insert_data(request)
                # If it succeeds, verify parameterized query was used
                execute_calls = cursor.execute.call_args_list
                for call in execute_calls:
                    if len(call[0]) > 0:
                        # Verify SQL uses psycopg2.sql.Identifier (not string concat)
                        assert "DROP" not in str(call[0][0]).upper() or "Identifier" in str(type(call[0][0]))
            except HTTPException:
                # Failing safely is acceptable
                pass


# =============================================================================
# SECURITY TEST 3: SQL Injection via Data Values
# =============================================================================

@pytest.mark.asyncio
async def test_sql_injection_via_data_values():
    """
    SECURITY TEST: Attempt SQL injection through data values
    Attack: Insert malicious SQL as data values
    Expected: Values are parameterized, treated as literals
    """
    malicious_values = [
        {"id": "1; DROP TABLE users; --", "name": "test"},
        {"id": 1, "name": "'; DELETE FROM customers WHERE '1'='1"},
        {"id": 1, "name": "test'; DROP TABLE customers; --"},
        {"id": "1 OR 1=1", "name": "test"},
        {"id": 1, "description": "'; UPDATE users SET admin=true WHERE '1'='1"},
    ]

    for malicious_row in malicious_values:
        request = InsertDataRequest(
            table="sales.customers",
            rows=[malicious_row]
        )

        conn, cursor = make_connection_with_table()

        with patch("app.routes.data.get_connection", return_value=conn):
            response = await insert_data(request)

            # Should succeed - values are parameterized
            assert response.success is True

            # Verify parameterized query was used
            execute_calls = cursor.execute.call_args_list
            for call in execute_calls[1:]:  # Skip validation check
                if len(call[0]) > 1:
                    # Values should be in a separate parameter (not in SQL string)
                    sql_query = str(call[0][0])
                    values = call[0][1]
                    # SQL should not contain the actual malicious string
                    assert "DROP TABLE" not in sql_query
                    assert "DELETE FROM" not in sql_query


# =============================================================================
# SECURITY TEST 4: Row Limit Enforcement (DoS Prevention)
# =============================================================================

@pytest.mark.asyncio
async def test_row_limit_enforcement():
    """
    SECURITY TEST: Attempt to exceed row limit
    Attack: Send 2000 rows (limit is 1000)
    Expected: Rejected with 400 error before processing
    """
    # Attempt to insert 2000 rows (over the 1000 limit)
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": i, "customer_id": i % 100, "total": float(i)}
            for i in range(1, 2001)
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        # Should be a 400 Bad Request
        assert exc_info.value.status_code == 400
        assert "Too many rows" in exc_info.value.detail or "Maximum allowed" in exc_info.value.detail

        # Verify no data was inserted (connection not even attempted)
        cursor.execute.assert_not_called()


# =============================================================================
# SECURITY TEST 5: Exactly at Row Limit (Boundary Test)
# =============================================================================

@pytest.mark.asyncio
async def test_row_limit_boundary():
    """
    SECURITY TEST: Insert exactly MAX_ROWS (1000)
    Expected: Should succeed (at limit, not over)
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": i, "total": float(i)}
            for i in range(1, MAX_ROWS + 1)
        ]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True
    assert response.rows_inserted == MAX_ROWS


@pytest.mark.asyncio
async def test_row_limit_boundary_plus_one():
    """
    SECURITY TEST: Insert MAX_ROWS + 1 (1001)
    Expected: Should be rejected
    """
    request = InsertDataRequest(
        table="sales.orders",
        rows=[
            {"id": i, "total": float(i)}
            for i in range(1, MAX_ROWS + 2)
        ]
    )

    with patch("app.routes.data.get_connection", return_value=MagicMock()):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code == 400


# =============================================================================
# SECURITY TEST 6: System Table Protection
# =============================================================================

@pytest.mark.asyncio
async def test_system_table_protection():
    """
    SECURITY TEST: Attempt to insert into system tables
    Attack: Target pg_catalog, information_schema tables
    Expected: Should fail (table not found or rejected)
    """
    system_tables = [
        "pg_catalog.pg_class",
        "information_schema.tables",
        "pg_catalog.pg_user",
        "information_schema.columns",
    ]

    for system_table in system_tables:
        request = InsertDataRequest(
            table=system_table,
            rows=[{"fake_column": "fake_value"}]
        )

        # Mock table as not existing or protected
        conn, cursor = make_connection_with_table(table_exists=False)

        with patch("app.routes.data.get_connection", return_value=conn):
            with pytest.raises(HTTPException) as exc_info:
                await insert_data(request)

            # Should be 404 Not Found or similar
            assert exc_info.value.status_code in [404, 403, 400]


# =============================================================================
# SECURITY TEST 7: XSS Prevention
# =============================================================================

@pytest.mark.asyncio
async def test_xss_prevention():
    """
    SECURITY TEST: Insert XSS payloads as data
    Attack: <script>alert('XSS')</script> and similar
    Expected: Stored as-is, not executed (backend doesn't render)
    """
    xss_payloads = [
        {"id": 1, "name": "<script>alert('XSS')</script>"},
        {"id": 2, "name": "<img src=x onerror=alert('XSS')>"},
        {"id": 3, "name": "javascript:alert('XSS')"},
        {"id": 4, "name": "<svg/onload=alert('XSS')>"},
    ]

    request = InsertDataRequest(
        table="sales.customers",
        rows=xss_payloads
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    # Should succeed - XSS is stored as text (not executed by backend)
    assert response.success is True
    assert response.rows_inserted == 4

    # Note: Frontend (React) auto-escapes when rendering, so this is safe


# =============================================================================
# SECURITY TEST 8: Path Traversal Attempts
# =============================================================================

@pytest.mark.asyncio
async def test_path_traversal_attempts():
    """
    SECURITY TEST: Attempt path traversal in table names
    Attack: ../../../etc/passwd style attacks
    Expected: Rejected by table name format validation
    """
    path_traversal_attempts = [
        "../../etc/passwd",
        "../../../windows/system32",
        "sales/../admin/users",
        "./../../sensitive_data",
    ]

    for malicious_path in path_traversal_attempts:
        request = InsertDataRequest(
            table=malicious_path,
            rows=[{"id": 1}]
        )

        with patch("app.routes.data.get_connection", return_value=MagicMock()):
            with pytest.raises(HTTPException) as exc_info:
                await insert_data(request)

            # Should be rejected due to invalid format
            assert exc_info.value.status_code == 400


# =============================================================================
# SECURITY TEST 9: Command Injection Attempts
# =============================================================================

@pytest.mark.asyncio
async def test_command_injection_attempts():
    """
    SECURITY TEST: Attempt OS command injection
    Attack: ; rm -rf /, | cat /etc/passwd, etc.
    Expected: Treated as literal data, not executed
    """
    command_injection_payloads = [
        {"id": 1, "name": "; rm -rf /"},
        {"id": 2, "name": "| cat /etc/passwd"},
        {"id": 3, "name": "`whoami`"},
        {"id": 4, "name": "$(reboot)"},
        {"id": 5, "name": "&& shutdown -h now"},
    ]

    request = InsertDataRequest(
        table="sales.customers",
        rows=command_injection_payloads
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    # Should succeed - commands are stored as text, not executed
    assert response.success is True
    assert response.rows_inserted == 5


# =============================================================================
# SECURITY TEST 10: LDAP Injection Attempts
# =============================================================================

@pytest.mark.asyncio
async def test_ldap_injection_attempts():
    """
    SECURITY TEST: LDAP injection patterns
    Attack: *, )(, |(, etc.
    Expected: Stored as literals (no LDAP processing in this context)
    """
    ldap_payloads = [
        {"id": 1, "name": "*"},
        {"id": 2, "name": "admin)(cn=*))(|(cn=*"},
        {"id": 3, "name": "*)(&(objectClass=*"},
    ]

    request = InsertDataRequest(
        table="sales.customers",
        rows=ldap_payloads
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        response = await insert_data(request)

    assert response.success is True


# =============================================================================
# SECURITY TEST 11: Oversized Payload (Individual Field)
# =============================================================================

@pytest.mark.asyncio
async def test_oversized_individual_field():
    """
    SECURITY TEST: Extremely large individual field value
    Attack: 10MB string in a single field
    Expected: Database will reject based on column type, or insert if allowed
    """
    huge_string = "A" * (10 * 1024 * 1024)  # 10MB string

    request = InsertDataRequest(
        table="sales.customers",
        rows=[
            {"id": 1, "name": "test", "description": huge_string}
        ]
    )

    conn, cursor = make_connection_with_table()

    # Simulate database rejection
    import psycopg2

    def execute_with_size_check(*args, **kwargs):
        if len(args) > 1 and any(len(str(v)) > 1000000 for v in args[1]):
            raise psycopg2.DataError("value too long for type character varying")

    cursor.execute.side_effect = execute_with_size_check
    cursor.fetchone.return_value = (1,)

    with patch("app.routes.data.get_connection", return_value=conn):
        # Should either succeed or fail gracefully with DB error
        try:
            response = await insert_data(request)
            # If it succeeds, that's okay (database allowed it)
        except HTTPException as e:
            # Should be a 400 error with database constraint message
            assert e.status_code in [400, 500]


# =============================================================================
# SECURITY TEST 12: NULL Byte Injection
# =============================================================================

@pytest.mark.asyncio
async def test_null_byte_injection():
    """
    SECURITY TEST: NULL byte injection attempts
    Attack: embedded \x00 characters
    Expected: Handled safely (postgres may reject or accept)
    """
    null_byte_payloads = [
        {"id": 1, "name": "test\x00admin"},
        {"id": 2, "name": "user\x00.txt"},
    ]

    request = InsertDataRequest(
        table="sales.customers",
        rows=null_byte_payloads
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        # Either succeeds or fails gracefully
        try:
            response = await insert_data(request)
            # Success is acceptable
        except HTTPException:
            # Safe failure is acceptable
            pass


# =============================================================================
# SECURITY TEST 13: Integer Overflow Attempts
# =============================================================================

@pytest.mark.asyncio
async def test_integer_overflow_attempts():
    """
    SECURITY TEST: Extremely large integer values
    Attack: Values beyond PostgreSQL integer limits
    Expected: Database rejects with constraint error
    """
    overflow_values = [
        {"id": 2**63, "name": "overflow"},  # Larger than bigint max
        {"id": -2**63 - 1, "name": "underflow"},
        {"id": 9999999999999999999, "name": "huge"},
    ]

    request = InsertDataRequest(
        table="sales.customers",
        rows=overflow_values
    )

    conn, cursor = make_connection_with_table()

    # Simulate database rejection
    import psycopg2

    def execute_with_overflow_check(*args, **kwargs):
        if len(args) > 1:
            for v in args[1]:
                if isinstance(v, int) and abs(v) > 2**31:
                    raise psycopg2.DataError("integer out of range")

    cursor.execute.side_effect = execute_with_overflow_check
    cursor.fetchone.return_value = (1,)

    with patch("app.routes.data.get_connection", return_value=conn):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code in [400, 500]


# =============================================================================
# SECURITY TEST 14: Malformed JSON in Preview
# =============================================================================

@pytest.mark.asyncio
async def test_malformed_data_in_preview():
    """
    SECURITY TEST: Send malformed data to preview endpoint
    Expected: Graceful handling or validation error
    """
    # This would typically come from frontend validation, but test backend too
    malformed_requests = [
        {"table": "invalid", "rows": "not_a_list"},  # Wrong type
        {"table": "sales.customers", "rows": [{"id": {"nested": "object"}}]},  # Nested object
    ]

    for bad_data in malformed_requests:
        try:
            # Pydantic should reject this before it reaches the function
            request = InsertDataRequest(**bad_data)
            conn, cursor = make_connection_with_table()

            with patch("app.routes.data.get_connection", return_value=conn):
                await preview_data(request)
        except (ValueError, TypeError):
            # Pydantic validation failure is expected and acceptable
            pass


# =============================================================================
# SECURITY TEST 15: Concurrent Request DoS
# =============================================================================

@pytest.mark.asyncio
async def test_rapid_concurrent_requests():
    """
    SECURITY TEST: Simulate rapid concurrent requests
    Note: This is a simplified test; real DoS prevention requires rate limiting
    Expected: Each request processed independently
    """
    import asyncio

    request = InsertDataRequest(
        table="sales.customers",
        rows=[{"id": 1, "name": "test"}]
    )

    conn, cursor = make_connection_with_table()

    with patch("app.routes.data.get_connection", return_value=conn):
        # Simulate 10 concurrent requests
        tasks = [insert_data(request) for _ in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # All should succeed (no cross-contamination)
        successful = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful) == 10


# =============================================================================
# SECURITY TEST 16: Empty Table Name
# =============================================================================

@pytest.mark.asyncio
async def test_empty_table_name():
    """
    SECURITY TEST: Empty or whitespace table name
    Expected: Validation error
    """
    empty_names = ["", " ", "  ", "\t", "\n"]

    for empty_name in empty_names:
        request = InsertDataRequest(
            table=empty_name,
            rows=[{"id": 1}]
        )

        with patch("app.routes.data.get_connection", return_value=MagicMock()):
            with pytest.raises(HTTPException) as exc_info:
                await insert_data(request)

            assert exc_info.value.status_code == 400


# =============================================================================
# SECURITY TEST 17: No Database Connection (State Confusion)
# =============================================================================

@pytest.mark.asyncio
async def test_no_database_connection():
    """
    SECURITY TEST: Attempt insert when no DB connection configured
    Expected: Clear error message, no crash
    """
    request = InsertDataRequest(
        table="sales.customers",
        rows=[{"id": 1, "name": "test"}]
    )

    with patch("app.routes.data.get_connection", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await insert_data(request)

        assert exc_info.value.status_code == 500
        assert "database" in exc_info.value.detail.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
