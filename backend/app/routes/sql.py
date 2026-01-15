from fastapi import APIRouter, Request, Response
from pydantic import BaseModel
from app.schema.cache import get_schema, refresh_schema
from app.nl_to_sql.validator import validate_and_normalize_sql, SQLValidationError
from app.db import get_connection, get_database_config
from app.db_provisioner import update_db_activity
from app.utils.session import get_or_create_session_id


router = APIRouter(prefix="/api/sql", tags=["sql"])


class SQLRequest(BaseModel):
    sql: str


# Parse and validate the SQL
# Returns normalization and any errors/warnings
@router.post("/validate")
def validate_sql(request: SQLRequest):
    try:
        schema_model = get_schema()
        normalized_sql_list, warnings = validate_and_normalize_sql(request.sql, schema_model)

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
            "normalized_sql": ";\n".join(normalized_sql_list),
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
def execute_sql(http_request: Request, http_response: Response, request: SQLRequest):
    session_id = get_or_create_session_id(http_request, http_response)
    conn = None
    cursor = None

    try:
        schema_model = get_schema()
        normalized_sql_list, warnings = validate_and_normalize_sql(request.sql, schema_model)

        if warnings:
            return {
                "error_type": "validation_error",
                "message": f"SQL validation failed: {'; '.join(warnings)}"
            }

        conn = get_connection(session_id)
        cursor = conn.cursor()


        cursor.execute("SET statement_timeout = '30s'")
        schema_refreshed = None
        
        last_result = {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "truncated": False
        }
        schema_changed = False

        for stmt in normalized_sql_list:
            is_select_like = stmt.lstrip().upper().startswith(("SELECT", "WITH"))
            stmt_to_run = stmt
            
            if is_select_like and "LIMIT" not in stmt.upper():
                stmt_to_run = f"{stmt} LIMIT 500"

            cursor.execute(stmt_to_run)

            if is_select_like and cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                row_count = len(rows)
                truncated = row_count >= 500
                last_result = {
                    "columns": columns,
                    "rows": rows,
                    "row_count": row_count,
                    "truncated": truncated
                }
                
            else:
                schema_changed = schema_changed or not is_select_like
                row_count = cursor.rowcount if cursor.rowcount is not None and cursor.rowcount != -1 else 0
                
                last_result = {
                    "columns": [],
                    "rows": [],
                    "row_count": row_count,
                    "truncated": False
                }

        if schema_changed:
            conn.commit()

            try:
                schema_refreshed = refresh_schema(conn)
                
            except Exception:
                schema_refreshed = None

        # Update activity tracking for managed DBs
        db_config = get_database_config(session_id)
        if db_config and db_config.dbname.startswith("schemasense_user_"):
            update_db_activity(db_config.dbname)

        return {
            "columns": last_result["columns"],
            "rows": last_result["rows"],
            "row_count": last_result["row_count"],
            "truncated": last_result["truncated"],
            "schema": schema_refreshed.to_dict_for_api() if schema_refreshed else None,
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
def plan_sql(http_request: Request, http_response: Response, request: SQLRequest):
    session_id = get_or_create_session_id(http_request, http_response)
    conn = None
    cursor = None

    try:
        conn = get_connection(session_id)
        cursor = conn.cursor()


        schema_model = get_schema()
        normalized_sql_list, warnings = validate_and_normalize_sql(request.sql, schema_model)

        if warnings:
            return {
                "error_type" : "validation_error",
                "message": f"SQL validation failed: {'; '.join(warnings)}"
            }

        if len(normalized_sql_list) != 1:
            return {
                "error_type": "validation_error",
                "message": "Query plans are only available for a single SELECT statement."
            }

        normalized_sql = normalized_sql_list[0]

        if not normalized_sql.lstrip().upper().startswith(("SELECT", "WITH")):
            return {
                "error_type": "validation_error",
                "message": "Query plans are only available for SELECT statements."
            }

        explain_sql = f"EXPLAIN (FORMAT JSON) {normalized_sql}"
        cursor.execute(explain_sql)
        plan_result = cursor.fetchone()

        if not plan_result or not plan_result[0]:
            return {
                "error_type": "plan_error",
                "message": "No plan data returned from EXPLAIN"
            }

        plan_json = plan_result[0][0] if isinstance(plan_result[0], list) else plan_result[0]
        root_plan = plan_json.get("Plan")

        if not root_plan:
            return {
                "error_type": "plan_error",
                "message": "Invalid plan structure returned from EXPLAIN"
            }


        nodes = []
        edges = []
        node_counter = [0] 

        def traverse_plan(plan_node, parent_id=None):
            node_id = str(node_counter[0])
            node_counter[0] += 1

            node_type = plan_node.get("Node Type", "Unknown")
            table = plan_node.get("Relation Name")
            rows = plan_node.get("Plan Rows", 0)
            total_cost = plan_node.get("Total Cost", 0)

            node = {
                "id": node_id,
                "type": node_type,
                "rows": rows,
                "cost": total_cost
            }

            if table:
                node["table"] = table

            nodes.append(node)

            if parent_id is not None:
                edges.append({
                    "from": node_id,
                    "to": parent_id
                })

            child_plans = plan_node.get("Plans", [])
            for child_plan in child_plans:
                traverse_plan(child_plan, node_id)

            return node_id

        traverse_plan(root_plan)

        # Update activity tracking for managed DBs
        db_config = get_database_config(session_id)
        if db_config and db_config.dbname.startswith("schemasense_user_"):
            update_db_activity(db_config.dbname)

        return {
            "nodes": nodes,
            "edges": edges
        }

    except SQLValidationError as e:
        return {
            "error_type": "validation_error",
            "message": str(e)
        }

    except Exception as e:
        return {
            "error_type": "db_error",
            "message": f"Query plan generation failed: {str(e)}"
        }

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()
        
        
    





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
