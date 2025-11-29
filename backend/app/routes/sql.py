from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/sql", tags=["sql"])


class SQLRequest(BaseModel):
    sql: str


#parse and validate the sql
#return normalization and any errors
@router.post("/validate")
def validate_sql(request: SQLRequest):
    return {
        "valid" : True,
        "errors" : [],
        "normalized_sql" : request.sql
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