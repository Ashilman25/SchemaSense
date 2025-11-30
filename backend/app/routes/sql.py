from fastapi import APIRouter
from pydantic import BaseModel
from app.schema.cache import get_schema
from app.nl_to_sql.validator import validate_and_normalize_sql, SQLValidationError
from app.db import get_connection


router = APIRouter(prefix="/api/sql", tags=["sql"])


class SQLRequest(BaseModel):
    sql: str


# Parse and validate the SQL
# Returns normalization and any errors/warnings
@router.post("/validate")
def validate_sql(request: SQLRequest):
    try:
        schema_model = get_schema()
        normalized_sql, warnings = validate_and_normalize_sql(request.sql, schema_model)

        #if warnings, invalid
        if warnings:
            return {
                "valid": False,
                "errors": warnings,
                "normalized_sql": None
            }

        return {
            "valid": True,
            "errors": [],
            "normalized_sql": normalized_sql,
        }

    except SQLValidationError as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "normalized_sql": None
        }

    except Exception as e:
        return {
            "valid": False,
            "errors": [f"Validation failed: {str(e)}"],
            "normalized_sql": None
        }
    
    
    



# Run the validated SQL against connected database
@router.post("/execute")
def execute_sql(request: SQLRequest):
    conn = None
    cursor = None

    try:
        schema_model = get_schema()
        normalized_sql, warnings = validate_and_normalize_sql(request.sql, schema_model)

        if warnings:
            return {
                "error_type": "validation_error",
                "message": f"SQL validation failed: {'; '.join(warnings)}"
            }

        if "LIMIT" not in normalized_sql.upper():
            normalized_sql += " LIMIT 500"

        conn = get_connection()
        cursor = conn.cursor()


        cursor.execute("SET statement_timeout = '30s'")
        cursor.execute(normalized_sql)


        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        row_count = len(rows)
        truncated = row_count >= 500

        return {
            "columns": columns,
            "rows": rows,
            "row_count": row_count,
            "truncated": truncated
        }

    except SQLValidationError as e:
        return {
            "error_type": "validation_error",
            "message": str(e)
        }

    except Exception as e:
        return {
            "error_type": "db_error",
            "message": f"Query execution failed: {str(e)}"
        }

    finally:
        if cursor:
            cursor.close()
            
        if conn:
            conn.close()


#run a simplified explain plan structure for given sql
@router.post("/plan")
def plan_sql(request: SQLRequest):
    return {
        "nodes": [], 
        "edges": []
        }




# from app.nl_to_sql.validator import validate_and_normalize_sql, SQLValidationError

# try:
#     normalized_sql, warnings = validate_and_normalize_sql(
#         "SELECT * FROM users WHERE id = 1",
#         schema_model
#     )
    
#     if warnings:
#         print(f"Warnings: {warnings}")
    
#     # Use normalized_sql for execution
# except SQLValidationError as e:
#     print(f"Validation failed: {e}")