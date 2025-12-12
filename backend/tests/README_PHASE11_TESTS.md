# Phase 11 Data Insertion Tests

Comprehensive test suite for the Phase 11 data insertion feature covering proper user flows, security/malicious scenarios, validation, and end-to-end integration.

## Test Files Overview

### 1. `test_data_insert_proper_flow.py`
**Purpose:** Tests all happy-path scenarios for manual entry and file upload data insertion.

**Coverage:**
- ✅ Single row manual insert
- ✅ Multiple rows manual insert
- ✅ NULL value handling (empty strings, 'null', None)
- ✅ Data preview endpoint
- ✅ Preview with extra columns
- ✅ Partial insert success (some rows fail)
- ✅ Large batch insert (1000 rows at limit)
- ✅ Unicode and special characters
- ✅ Empty optional fields
- ✅ Mixed data types (int, float, string, boolean)
- ✅ Column order independence
- ✅ Transaction commit on success
- ✅ Connection cleanup
- ✅ Qualified table names (schema.table)

**Test Count:** 15 test cases

---

### 2. `test_data_insert_security.py`
**Purpose:** Tests all security scenarios, injection attempts, and malicious inputs.

**Coverage:**
- 🛡️ SQL injection via table name
- 🛡️ SQL injection via column names
- 🛡️ SQL injection via data values
- 🛡️ Row limit enforcement (DoS prevention)
- 🛡️ Row limit boundary testing (exactly 1000, 1001)
- 🛡️ System table protection (pg_catalog, information_schema)
- 🛡️ XSS prevention
- 🛡️ Path traversal attempts
- 🛡️ Command injection attempts
- 🛡️ LDAP injection attempts
- 🛡️ Oversized payload (individual field)
- 🛡️ NULL byte injection
- 🛡️ Integer overflow attempts
- 🛡️ Malformed data in preview
- 🛡️ Concurrent request DoS simulation
- 🛡️ Empty table name
- 🛡️ No database connection (state confusion)

**Test Count:** 17 test cases

---

### 3. `test_data_validation_edge_cases.py`
**Purpose:** Tests validation logic, error handling, and edge case scenarios.

**Coverage:**

#### Validation Tests
- ✅ Invalid table name formats
- ✅ Table does not exist
- ✅ No rows provided
- ✅ Row with no columns

#### Edge Cases
- ✅ All NULL values
- ✅ Very long table/schema names
- ✅ Column names with special characters
- ✅ Whitespace in values (preserved)
- ✅ Case sensitivity
- ✅ Boolean values (various formats)
- ✅ Numeric precision
- ✅ Zero and negative numbers
- ✅ Scientific notation
- ✅ Inconsistent column order across rows

#### Error Handling
- ✅ Database connection failure
- ✅ Database error during insert
- ✅ Constraint violations (PK, FK, CHECK, NOT NULL)
- ✅ Connection lost mid-transaction
- ✅ Timeout during insert

**Test Count:** 20 test cases

---

### 4. `test_data_integration_e2e.py`
**Purpose:** Tests complete user flows from start to finish, including multi-step operations.

**Coverage:**
- 🔄 Complete manual entry flow (preview → validate → insert)
- 🔄 CSV upload simulation
- 🔄 File upload with column remapping
- 🔄 Error recovery flow (fail → fix → retry)
- 🔄 Partial success workflow (handle errors, re-insert)
- 🔄 Large batch workflow (1000 rows)
- 🔄 Multiple table insert flow (related tables)
- 🔄 Preview → Edit → Preview → Insert flow
- 🔄 Connection state management

**Test Count:** 9 test cases

---

## Running the Tests

### Run All Phase 11 Tests
```bash
cd backend
pytest tests/test_data*.py -v
```

### Run Specific Test File
```bash
# Proper flow tests
pytest tests/test_data_insert_proper_flow.py -v

# Security tests
pytest tests/test_data_insert_security.py -v

# Validation and edge cases
pytest tests/test_data_validation_edge_cases.py -v

# Integration/E2E tests
pytest tests/test_data_integration_e2e.py -v
```

### Run Tests with Coverage
```bash
pytest tests/test_data*.py --cov=app.routes.data --cov-report=html
```

### Run Specific Test by Name
```bash
pytest tests/test_data_insert_security.py::test_sql_injection_via_table_name -v
```

### Run Tests in Parallel (faster)
```bash
pip install pytest-xdist
pytest tests/test_data*.py -n auto
```

---

## Test Statistics

### Total Coverage
- **Total Test Files:** 4
- **Total Test Cases:** 61
- **Lines of Test Code:** ~2,000+

### Test Distribution by Category
| Category | Tests | File |
|----------|-------|------|
| Proper Flow | 15 | test_data_insert_proper_flow.py |
| Security | 17 | test_data_insert_security.py |
| Validation/Edge Cases | 20 | test_data_validation_edge_cases.py |
| Integration/E2E | 9 | test_data_integration_e2e.py |

### Test Categories
- ✅ **Happy Path Tests:** 15
- 🛡️ **Security Tests:** 17
- ⚠️ **Validation Tests:** 10
- 🔀 **Edge Case Tests:** 10
- 🔄 **Integration Tests:** 9

---

## Security Testing Coverage

### Injection Prevention
- ✅ SQL Injection (table names, columns, values)
- ✅ XSS (script tags, event handlers)
- ✅ Command Injection (shell commands)
- ✅ LDAP Injection
- ✅ Path Traversal
- ✅ NULL Byte Injection

### DoS Prevention
- ✅ Row limit enforcement (1000 max)
- ✅ Oversized payloads
- ✅ Concurrent request handling
- ✅ Integer overflow

### Access Control
- ✅ System table protection
- ✅ Database connection validation
- ✅ Table existence verification

---

## Key Testing Patterns

### 1. Mock Connection Pattern
```python
def make_connection_with_table(table_exists=True):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (1 if table_exists else 0,)
    conn.cursor.return_value = cursor
    return conn, cursor
```

### 2. Parameterized Query Verification
```python
execute_calls = cursor.execute.call_args_list
for call in execute_calls:
    # Verify SQL uses placeholders, not string concatenation
    assert "%s" in sql or "Placeholder" in str(type(call[0][0]))
```

### 3. Transaction Verification
```python
assert response.success is True
conn.commit.assert_called_once()
conn.rollback.assert_not_called()
cursor.close.assert_called_once()
conn.close.assert_called_once()
```

---

## Expected Test Results

### All Tests Should Pass
When running the full test suite, you should see:
```
======================== test session starts =========================
collected 61 items

test_data_insert_proper_flow.py::test_single_row_manual_insert_success PASSED
test_data_insert_proper_flow.py::test_multiple_rows_manual_insert_success PASSED
...
test_data_integration_e2e.py::test_connection_state_management PASSED

======================== 61 passed in X.XXs ==========================
```

### Test Execution Time
- **Expected Time:** ~5-15 seconds (depending on machine)
- **Parallel Execution:** ~2-5 seconds with pytest-xdist

---

## Continuous Integration

### GitHub Actions Example
```yaml
name: Phase 11 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -e .[dev]
      - name: Run Phase 11 Tests
        run: |
          cd backend
          pytest tests/test_data*.py -v --cov=app.routes.data
```

---

## Manual Testing Checklist

After running automated tests, perform these manual tests in the UI:

### Manual Entry Flow
- [ ] Open Add Data modal
- [ ] Select a table
- [ ] Add a single row manually
- [ ] Validate inline errors appear for invalid data
- [ ] Clear validation errors when corrected
- [ ] Insert successfully

### CSV Upload Flow
- [ ] Upload a valid CSV file
- [ ] Verify auto-column matching
- [ ] Manually remap a column
- [ ] Preview shows correct row count
- [ ] Insert successfully

### Error Scenarios
- [ ] Try inserting duplicate primary key
- [ ] Try inserting invalid data types
- [ ] Try uploading file >5MB (should be rejected)
- [ ] Try uploading >1000 rows (should be truncated/rejected)
- [ ] Verify error messages are user-friendly

### Edge Cases
- [ ] Insert rows with NULL values
- [ ] Insert rows with Unicode characters (emoji, Chinese, etc.)
- [ ] Insert rows with special characters (quotes, apostrophes)
- [ ] Close modal with unsaved data (confirmation dialog)

---

## Test Maintenance

### Adding New Tests
1. Identify the category (proper flow, security, validation, integration)
2. Add test to appropriate file
3. Follow existing naming convention: `test_<description>`
4. Include docstring with test purpose and expected outcome
5. Update this README with test count

### Updating Tests
When updating data.py endpoints:
1. Review affected test files
2. Update mock behaviors if needed
3. Add new test cases for new features
4. Ensure backward compatibility

### Test Debugging
```bash
# Run with verbose output
pytest tests/test_data*.py -vv

# Run with print statements visible
pytest tests/test_data*.py -s

# Run with debugger on failure
pytest tests/test_data*.py --pdb

# Run specific test with full traceback
pytest tests/test_data_insert_security.py::test_sql_injection_via_table_name -vv --tb=long
```

---

## Known Limitations

### Tests Do Not Cover
- ❌ Actual database integration (uses mocks)
- ❌ Frontend JavaScript/React components
- ❌ Real file upload/parsing (frontend responsibility)
- ❌ Network layer (FastAPI routing)
- ❌ Authentication/authorization (not implemented in Phase 11)

These areas require separate integration tests or E2E tests with a real database.

---

## Future Test Enhancements

### Potential Additions
1. **Database Integration Tests**
   - Use testcontainers to spin up real Postgres
   - Test actual inserts and constraint enforcement

2. **Performance Tests**
   - Benchmark insert speed for large batches
   - Test concurrent request handling under load

3. **Frontend Tests**
   - React component unit tests (Jest)
   - E2E tests with Playwright/Cypress

4. **Property-Based Testing**
   - Use hypothesis for random data generation
   - Test edge cases automatically

---

## Contributing

When adding tests for Phase 11:

1. **Follow the Pattern:**
   - Use descriptive test names
   - Include docstrings
   - Mock dependencies appropriately

2. **Maintain Coverage:**
   - Aim for >90% code coverage
   - Test both success and failure paths

3. **Keep Tests Fast:**
   - Use mocks instead of real DB calls
   - Avoid sleep() or delays
   - Tests should run in milliseconds

4. **Document Well:**
   - Update this README
   - Add comments for complex test logic
   - Include expected behavior in docstrings

---

## Support

For questions or issues with Phase 11 tests:

1. Check test output for specific failures
2. Review test docstrings for expected behavior
3. Verify mock setup matches actual implementation
4. Consult `_docs/phase-11-qa-checklist.md` for manual testing

---

**Last Updated:** 2025-12-10
**Phase:** 11 Complete
**Test Suite Version:** 1.0
