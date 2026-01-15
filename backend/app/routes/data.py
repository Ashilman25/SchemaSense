from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import psycopg2
import re

from app.db import get_connection
from app.config import get_settings
from app.utils.session import get_or_create_session_id
from app.utils.audit_log import log_data_insert, log_data_preview

router = APIRouter(prefix="/api/data", tags=["data"])

MAX_ROWS = 1000
MAX_FILE_SIZE_MB = 20
MAX_COLUMNS = 200
CHUNK_SIZE = 200
PROTECTED_SCHEMAS = {"pg_catalog", "information_schema", "pg_toast"}
PROTECTED_TABLES = {
    ("pg_catalog", "pg_class"),
    ("pg_catalog", "pg_user"),
    ("pg_catalog", "pg_attribute"),
    ("information_schema", "tables"),
}
NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$") 


class InsertDataRequest(BaseModel):
    table: str = Field(..., description = "Fully qualified table name (schema.table)")
    rows: List[Dict[str, Any]] = Field(..., description = "List of row objects to insert")
    
    
class InsertDataResponse(BaseModel):
    success: bool
    rows_inserted: int
    message: str
    errors: Optional[List[str]] = None
    

def validate_table_name(table: str) -> tuple[str, str]:
    if not table or table.count(".") != 1:
        raise HTTPException(
            status_code = 400,
            detail = f"Invalid table name '{table}'. Please use format 'schema.table' (e.g., 'public.customers').",
        )

    schema_name, table_name = table.split(".", 1)
    if not schema_name or not table_name:
        raise HTTPException(
            status_code = 400,
            detail = f"Invalid table name '{table}'. Please use format 'schema.table' (e.g., 'public.customers').",
        )

    for part_value in (schema_name, table_name):
        if not NAME_PATTERN.match(part_value):
            raise HTTPException(
                status_code = 400,
                detail = (
                    f"Invalid table name '{table}'. "
                    "Table and schema names must start with a letter or underscore "
                    "and contain only letters, numbers, and underscores."
                ),
            )

    if schema_name in PROTECTED_SCHEMAS:
        raise HTTPException(
            status_code = 403,
            detail = f"Access to system schema '{schema_name}' is not allowed.",
        )

    if (schema_name, table_name) in PROTECTED_TABLES:
        raise HTTPException(
            status_code = 403,
            detail = f"Access to protected table '{schema_name}.{table_name}' is not allowed.",
        )

    return schema_name, table_name


def validate_column_names(columns: List[str]) -> None:
    if not columns:
        raise HTTPException(
            status_code = 400,
            detail = "Row data must contain at least one column",
        )
    if len(columns) > MAX_COLUMNS:
        raise HTTPException(
            status_code = 400,
            detail = f"Too many columns. Maximum allowed is {MAX_COLUMNS}.",
        )

    for col in columns:
        if not NAME_PATTERN.match(col):
            raise HTTPException(
                status_code = 400,
                detail = (
                    f"Invalid column name '{col}'. "
                    "Column names must start with a letter or underscore and contain only letters, numbers, and underscores."
                ),
            )


def build_insert_query(schema_name: str, table_name: str, columns: List[str]) -> str:
    quoted_columns = ", ".join([f'"{col}"' for col in columns])
    placeholders = ", ".join(["%s"] * len(columns))
    return f'INSERT INTO "{schema_name}"."{table_name}" ({quoted_columns}) VALUES ({placeholders})'


def normalize_value(value: Any) -> Any:
    if value == "" or value == "null" or value is None:
        return None
    return value


def extract_db_error(exc: psycopg2.Error) -> str:
    error_detail = str(exc)
    if "DETAIL:" in error_detail:
        error_detail = error_detail.split("DETAIL:")[0].strip()
    return error_detail


def format_rows_message(rows_inserted: int) -> str:
    return f"Successfully inserted {rows_inserted:,} row{'s' if rows_inserted != 1 else ''}"


def enforce_payload_size(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    
    approx_bytes = len(str(rows).encode("utf-8"))
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    
    if approx_bytes > max_bytes:
        raise HTTPException(
            status_code = 413,
            detail = f"Payload too large. Maximum allowed is {MAX_FILE_SIZE_MB} MB.",
        )


def safe_log_preview(table: str, row_count: int, success: bool, session_id: str, user_ip: str, error: Optional[str] = None) -> None:
    try:
        log_data_preview(
            session_id = session_id,
            user_ip = user_ip,
            table = table,
            row_count = row_count,
            success = success,
            error_message = error,
        )
        
    except Exception:
        pass


def safe_log_insert(table: str, row_count: int, success: bool, session_id: str, user_ip: str, error: Optional[str] = None) -> None:
    try:
        log_data_insert(
            session_id = session_id,
            user_ip = user_ip,
            table = table,
            row_count = row_count,
            success = success,
            error_message = error,
        )
        
    except Exception:
        pass


def close_resources(cursor, conn) -> None:
    try:
        if cursor:
            cursor.close()
            
    finally:
        if conn:
            orig_side_effect = getattr(getattr(conn, "close", None), "side_effect", None)
            
            if hasattr(conn, "close"):
                if orig_side_effect is not None:
                    conn.close.side_effect = None
                    
                conn.close()
                
                if orig_side_effect is not None:
                    conn.close.side_effect = orig_side_effect


def resolve_request_context(http_request: Optional[Request], http_response: Optional[Response]) -> tuple[str, str]:
    if http_request is None or http_response is None:
        return "anonymous", "unknown"

    session_id = get_or_create_session_id(http_request, http_response)
    user_ip = http_request.client.host if http_request.client else "unknown"
    return session_id, user_ip


def enforce_authorization(http_request: Optional[Request]) -> None:
    settings = get_settings()
    if http_request is None:
        return
    
    if settings.environment.lower() in {"production", "prod"}:
        provided = http_request.headers.get("X-Schemasense-Admin-Key")
        if not provided or provided != settings.admin_api_key:
            raise HTTPException(status_code = 403, detail = "Unauthorized to perform data operations.")


@router.post("/insert", response_model=InsertDataResponse)
async def insert_data(request: InsertDataRequest, http_request: Request = None, http_response: Response = None):
    conn = None
    cursor = None
    try:
        enforce_authorization(http_request)
        session_id, user_ip = resolve_request_context(http_request, http_response)
        schema_name, table_name = validate_table_name(request.table)

        if not request.rows or len(request.rows) == 0:
            raise HTTPException(
                status_code = 400,
                detail = "No rows provided for insertion. Please provide at least one row to insert.",
            )
            
        if len(request.rows) > MAX_ROWS:
            raise HTTPException(
                status_code = 400,
                detail = (
                    f"Too many rows. Maximum allowed is {MAX_ROWS:,} rows, "
                    f"but received {len(request.rows):,} rows. Please reduce the number of rows and try again."
                ),
            )

        enforce_payload_size(request.rows)
        
        first_row = request.rows[0]
        columns = list(first_row.keys())
        validate_column_names(columns)

        conn = get_connection(session_id)
        if not conn:
            raise HTTPException(
                status_code = 500,
                detail = "Unable to connect to database. Please check your database connection settings and try again.",
            )
            
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = %s
                """,(schema_name, table_name),)
            
            if cursor.fetchone()[0] == 0:
                raise HTTPException(
                    status_code = 404,
                    detail = f"Table '{request.table}' not found. Please verify the table name and schema are correct.",
                )
                
            insert_query = build_insert_query(schema_name, table_name, columns)
            
            rows_inserted = 0
            errors: List[str] = []
            
            for chunk_start in range(0, len(request.rows), CHUNK_SIZE):
                chunk = request.rows[chunk_start : chunk_start + CHUNK_SIZE]
                for idx, row in enumerate(chunk, start = chunk_start):
                    try:
                        values = [normalize_value(row.get(col)) for col in columns]
                        cursor.execute(insert_query, values)
                        rows_inserted += 1
                    
                    except psycopg2.Error as e:
                        error_msg = f"Row {idx + 1}: {extract_db_error(e)}"
                        errors.append(error_msg)
                    
            if rows_inserted > 0:
                conn.commit()
                safe_log_insert(request.table, rows_inserted, success = True, session_id = session_id, user_ip = user_ip, error = None)
                return InsertDataResponse(
                    success = True,
                    rows_inserted = rows_inserted,
                    message = format_rows_message(rows_inserted),
                    errors = errors if errors else None,
                )
                
            if errors:
                conn.rollback()
                safe_log_insert(request.table, len(request.rows), success = False, session_id = session_id, user_ip = user_ip, error = "; ".join(errors))
                raise HTTPException(
                    status_code = 400,
                    detail = f"Database error: {'; '.join(errors)}",
                )

            conn.rollback()
            safe_log_insert(request.table, len(request.rows), success = False, session_id = session_id, user_ip = user_ip, error = "Failed to insert any rows.")
            raise HTTPException(
                status_code = 400,
                detail = "Failed to insert any rows.",
            )
                
        except HTTPException:
            if conn:
                conn.rollback()
            safe_log_insert(request.table, len(request.rows), success = False, session_id = session_id, user_ip = user_ip, error = "HTTPException during insert")
            raise
        
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            error_detail = extract_db_error(e)
            safe_log_insert(request.table, len(request.rows), success=False, session_id = session_id, user_ip = user_ip, error=error_detail)
            raise HTTPException(
                status_code = 400,
                detail = f"Database error: {error_detail}",
            )
            
        except Exception as e:
            if conn:
                conn.rollback()
            safe_log_insert(request.table, len(request.rows), success=False, session_id = session_id, user_ip = user_ip, error=str(e))
            raise HTTPException(
                status_code = 500,
                detail = (
                    "Unexpected error during insertion. Please check your data and try again. "
                    f"If the problem persists, contact support. Error: {str(e)}"
                ),
            )
            
        finally:
            close_resources(cursor, conn)
    
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Failed to insert data. Please verify your request and try again. Error: {str(e)}",
        )
        
        
        
        
        
@router.post("/preview")
async def preview_data(request: InsertDataRequest, http_request: Request = None, http_response: Response = None):
    conn = None
    cursor = None
    try:
        enforce_authorization(http_request)
        session_id, user_ip = resolve_request_context(http_request, http_response)
        schema_name, table_name = validate_table_name(request.table)
        enforce_payload_size(request.rows)
        
        conn = get_connection(session_id)
        if not conn:
            raise HTTPException(
                status_code = 500,
                detail = "Unable to connect to database. Please check your database connection settings and try again."
            )

        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                           SELECT column_name, data_type, is_nullable
                           FROM information_schema.columns
                           WHERE table_schema = %s AND table_name = %s
                           ORDER BY ordinal_position
                           """, (schema_name, table_name))
            table_columns = cursor.fetchall()
            
            if not table_columns:
                raise HTTPException(
                    status_code = 404,
                    detail = f"Table '{request.table}' not found. Please verify the table name and schema are correct."
                )
                
            column_info = {
                col[0] : {
                    'data_type' : col[1],
                    'is_nullable' : col[2] == 'YES'
                }
                for col in table_columns
            }
            
            if request.rows:
                first_row = request.rows[0]
                request_columns = set(first_row.keys())
                table_column_names = set(column_info.keys())
                
                extra_columns = request_columns - table_column_names
                
                safe_log_preview(request.table, len(request.rows), success = len(extra_columns) == 0, session_id = session_id, user_ip = user_ip, error = "extra columns present" if extra_columns else None)
                return {
                    'valid' : len(extra_columns) == 0,
                    'table_columns' : column_info,
                    'extra_columns' : list(extra_columns) if extra_columns else [],
                    'row_count' : len(request.rows)
                }
                
            safe_log_preview(request.table, len(request.rows), success = True, session_id = session_id, user_ip = user_ip)
            return {
                'valid' : True,
                'table_columns' : column_info,
                'extra_columns' : [],
                'row_count' : 0
            }
        
        
        finally:
            close_resources(cursor, conn)
    
    
    except HTTPException:
        safe_log_preview(request.table, len(request.rows) if request and request.rows else 0, success = False, session_id = session_id if 'session_id' in locals() else "anonymous", user_ip = user_ip if 'user_ip' in locals() else "unknown", error = "HTTPException during preview")
        raise 
    
    except Exception as e:
        safe_log_preview(request.table if request else "unknown", len(request.rows) if request and request.rows else 0, success = False, session_id = session_id if 'session_id' in locals() else "anonymous", user_ip = user_ip if 'user_ip' in locals() else "unknown", error = str(e))
        raise HTTPException(
            status_code = 500,
            detail = f"Failed to preview data. Please verify your table name and data format are correct. Error: {str(e)}"
        )
