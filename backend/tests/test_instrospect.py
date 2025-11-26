import sys
from pathlib import Path
import pytest

# Ensure the backend package is importable when running tests from repo root.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app.schema.instrospect import introspect_tables_and_columns


class FakeCursor:
    def __init__(self, rows, fail: bool = False):
        self.rows = rows
        self.fail = fail
        self.closed = False
        self.executed_sql = None

    def execute(self, sql: str) -> None:
        self.executed_sql = sql
        if self.fail:
            raise RuntimeError("boom")

    def fetchall(self):
        return self.rows

    def close(self) -> None:
        self.closed = True


class FakeConn:
    def __init__(self, rows, fail: bool = False):
        self.rows = rows
        self.fail = fail
        self.last_cursor: FakeCursor | None = None

    def cursor(self) -> FakeCursor:
        self.last_cursor = FakeCursor(self.rows, self.fail)
        return self.last_cursor


def test_groups_columns_by_table_and_schema():
    rows = [
        ("public", "customers", "id", "integer", "NO"),
        ("public", "customers", "name", "text", "YES"),
        ("sales", "orders", "id", "integer", "NO"),
    ]
    conn = FakeConn(rows)

    result = introspect_tables_and_columns(conn)

    assert ("public", "customers") in result
    assert result[("public", "customers")]["columns"][0]["name"] == "id"
    assert result[("public", "customers")]["columns"][1]["nullable"] == "YES"
    assert result[("sales", "orders")]["columns"][0]["type"] == "integer"
    assert conn.last_cursor.closed is True


def test_raises_clean_error_on_failure():
    conn = FakeConn([], fail=True)

    with pytest.raises(Exception) as excinfo:
        introspect_tables_and_columns(conn)

    assert "Error introspecting tables and columns" in str(excinfo.value)
    assert conn.last_cursor.closed is True
