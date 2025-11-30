from fastapi import APIRouter
from pydantic import BaseModel
from app.schema.cache import get_schema
from app.nl_to_sql.validator import validate_and_normalize_sql, SQLValidationError


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
    
    
    



#run the validated sql against connect database
@router.post("/execute")
def execute_sql(request: SQLRequest):
    return {
        "columns": [], 
        "rows": [], 
        "row_count": 0, 
        "truncated": False
        }


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