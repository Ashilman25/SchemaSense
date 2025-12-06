from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from app.models.schema_model import CanonicalSchemaModel, Column, SchemaValidationError
from app.schema.cache import get_or_refresh_schema, refresh_schema
from app.db import get_connection, get_database_config
from app.db_provisioner import update_db_activity
from app.schema.ddl_executor import generate_ddl_from_action, execute_ddl_statements, execute_ddl_text
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schema", tags=["schema"])



class ERAction(BaseModel):
    type: str
    name: Optional[str] = None
    schema: Optional[str] = "public"
    table: Optional[str] = None
    columns: Optional[List[Dict[str, Any]]] = None
    column: Optional[Dict[str, Any]] = None
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    old_col: Optional[str] = None
    new_col: Optional[str] = None
    column_name: Optional[str] = None
    force: Optional[bool] = False
    from_table: Optional[str] = None
    from_column: Optional[str] = None
    to_table: Optional[str] = None
    to_column: Optional[str] = None
    from_schema: Optional[str] = "public"
    to_schema: Optional[str] = "public"


class EREditRequest(BaseModel):
    actions: List[ERAction]


class EREditResponse(BaseModel):
    success: bool
    schema: Optional[Dict] = None
    ddl: Optional[str] = None
    errors: Optional[List[str]] = None



class DDLEditRequest(BaseModel):
    ddl: str


class DDLEditResponse(BaseModel):
    success: bool
    schema: Optional[Dict] = None
    ddl: Optional[str] = None
    error: Optional[str] = None
    details: Optional[str] = None


#get schema model
@router.get("")
def get_schema():
    conn = None
    try:
        conn = get_connection()

        schema_model = get_or_refresh_schema(conn)
        api_payload = schema_model.to_dict_for_api()

        # Update activity tracking for managed DBs
        db_config = get_database_config()
        if db_config and db_config.dbname.startswith("schemasense_user_"):
            update_db_activity(db_config.dbname)

        return api_payload

    except RuntimeError as e:
        raise HTTPException(status_code = 503, detail = f"Database connection unavailable: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Failed to retrieve schema: {str(e)}")

    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
    

@router.get('/sample-rows')
def get_sample_rows(table: str, limit: int = 10):
    conn = None
    cursor = None

    if limit > 100:
        limit = 100

    try:
        conn = get_connection()
        cursor = conn.cursor()

        schema_model = get_or_refresh_schema(conn)

        if table not in schema_model.tables:
            raise HTTPException(status_code = 404, detail = f"Table '{table}' not found in schema.")

        table_obj = schema_model.tables[table]
        schema_name = table_obj.schema
        table_name = table_obj.name


        query = f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT %s'
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        row_data = [list(row) for row in rows]

        # Update activity tracking for managed DBs
        db_config = get_database_config()
        if db_config and db_config.dbname.startswith("schemasense_user_"):
            update_db_activity(db_config.dbname)

        return {
            "table": table,
            "columns": columns,
            "rows": row_data,
            "row_count": len(row_data)
        }

    except HTTPException:
        raise

    except RuntimeError as e:
        raise HTTPException(status_code = 503, detail = f"Database connection unavailable: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Failed to retrieve sample rows: {str(e)}")

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


@router.get('/ddl')
def get_schema_ddl():
    conn = None
    try:
        conn = get_connection()

        schema_model = get_or_refresh_schema(conn)
        ddl_text = schema_model.to_ddl()

        return {
            "ddl": ddl_text,
            "table_count": len(schema_model.tables),
            "relationship_count": len(schema_model.relationships)
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Database connection unavailable: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DDL: {str(e)}")

    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


@router.post('/er-edit')
def apply_er_edits(request: EREditRequest) -> EREditResponse:
    conn = None
    try:
        conn = get_connection()
        schema_model = get_or_refresh_schema(conn)

        ddl_statements = []
        errors = []

        for action in request.actions:
            try:
                _apply_single_action(schema_model, action)

                action_params = _extract_action_params(action)
                ddl = generate_ddl_from_action(action.type, action_params, schema_model)
                ddl_statements.append(ddl)

            except SchemaValidationError as e:
                errors.append(f"Action '{action.type}': {str(e)}")

            except Exception as e:
                errors.append(f"Action '{action.type}' failed: {str(e)}")

        if errors:
            return EREditResponse(success = False, errors = errors)

        success, error_msg = execute_ddl_statements(conn, ddl_statements)

        if not success:
            return EREditResponse(
                success = False,
                errors = [f"Database execution failed: {error_msg}"]
            )

        refreshed_schema = refresh_schema(conn)
        db_config = get_database_config()
        
        if db_config and db_config.dbname.startswith("schemasense_user_"):
            update_db_activity(db_config.dbname)


        return EREditResponse(
            success = True,
            schema = refreshed_schema.to_dict_for_api(),
            ddl = refreshed_schema.to_ddl(),
            errors = None
        )

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Database connection unavailable: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to apply ER edits: {str(e)}", exc_info = True)
        raise HTTPException(status_code = 500, detail = f"Failed to apply ER edits: {str(e)}")

    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _apply_single_action(schema_model: CanonicalSchemaModel, action: ERAction) -> None:

    action_type = action.type

    if action_type == "add_table":
        columns = None
        if action.columns:
            columns = [
                Column(
                    name = col_data.get("name"),
                    type = col_data.get("type"),
                    is_pk = col_data.get("is_pk", False),
                    is_fk = col_data.get("is_fk", False),
                    nullable = col_data.get("nullable", True)
                )
                for col_data in action.columns
            ]

        schema_model.add_table(
            name = action.name,
            schema = action.schema or "public",
            columns = columns
        )

    elif action_type == "rename_table":
        schema_model.rename_table(
            old_name = action.old_name,
            new_name = action.new_name,
            schema = action.schema or "public"
        )

    elif action_type == "drop_table":
        schema_model.drop_table(
            name = action.name,
            schema = action.schema or "public",
            force = action.force or False
        )

    elif action_type == "add_column":
        table_parts = action.table.split(".")
        if len(table_parts) == 2:
            schema_name, table_name = table_parts
            
        else:
            schema_name = action.schema or "public"
            table_name = action.table


        col_data = action.column
        column = Column(
            name = col_data.get("name"),
            type = col_data.get("type"),
            is_pk = col_data.get("is_pk", False),
            is_fk = col_data.get("is_fk", False),
            nullable = col_data.get("nullable", True)
        )

        schema_model.add_column(
            table_name = table_name,
            column = column,
            schema = schema_name
        )

    elif action_type == "rename_column":
        table_parts = action.table.split(".")
        if len(table_parts) == 2:
            schema_name, table_name = table_parts
            
        else:
            schema_name = action.schema or "public"
            table_name = action.table

        schema_model.rename_column(
            table_name = table_name,
            old_col = action.old_col,
            new_col = action.new_col,
            schema = schema_name
        )

    elif action_type == "drop_column":
        table_parts = action.table.split(".")
        if len(table_parts) == 2:
            schema_name, table_name = table_parts
            
        else:
            schema_name = action.schema or "public"
            table_name = action.table

        schema_model.drop_column(
            table_name = table_name,
            column_name = action.column_name,
            schema = schema_name,
            force = action.force or False
        )

    elif action_type == "add_relationship":
        from_parts = action.from_table.split(".")
        to_parts = action.to_table.split(".")

        from_schema = from_parts[0] if len(from_parts) == 2 else (action.from_schema or "public")
        from_table = from_parts[-1]

        to_schema = to_parts[0] if len(to_parts) == 2 else (action.to_schema or "public")
        to_table = to_parts[-1]

        schema_model.add_relationship(
            from_table = from_table,
            from_column = action.from_column,
            to_table = to_table,
            to_column = action.to_column,
            from_schema = from_schema,
            to_schema = to_schema
        )

    elif action_type == "remove_relationship":
        from_parts = action.from_table.split(".")
        to_parts = action.to_table.split(".")

        from_schema = from_parts[0] if len(from_parts) == 2 else (action.from_schema or "public")
        from_table = from_parts[-1]

        to_schema = to_parts[0] if len(to_parts) == 2 else (action.to_schema or "public")
        to_table = to_parts[-1]

        schema_model.remove_relationship(
            from_table = from_table,
            from_column = action.from_column,
            to_table = to_table,
            to_column = action.to_column,
            from_schema = from_schema,
            to_schema = to_schema
        )

    else:
        raise ValueError(f"Unknown action type: {action_type}")


def _extract_action_params(action: ERAction) -> Dict[str, Any]:
    params = {}
    
    if action.type == "add_table":
        params["name"] = action.name
        params["schema"] = action.schema or "public"
        params["columns"] = action.columns or []  

    elif action.type == "rename_table":
        params["old_name"] = action.old_name
        params["new_name"] = action.new_name
        params["schema"] = action.schema or "public"

    elif action.type == "drop_table":
        params["name"] = action.name
        params["schema"] = action.schema or "public"
        params["force"] = action.force or False

    elif action.type == "add_column":
        table_parts = action.table.split(".")
        
        if len(table_parts) == 2:
            params["schema"] = table_parts[0]
            params["table_name"] = table_parts[1]
            
        else:
            params["schema"] = action.schema or "public"
            params["table_name"] = action.table

        params["column"] = action.column

    elif action.type == "rename_column":
        table_parts = action.table.split(".")
        
        if len(table_parts) == 2:
            params["schema"] = table_parts[0]
            params["table_name"] = table_parts[1]
            
        else:
            params["schema"] = action.schema or "public"
            params["table_name"] = action.table

        params["old_col"] = action.old_col
        params["new_col"] = action.new_col

    elif action.type == "drop_column":
        table_parts = action.table.split(".")
        
        if len(table_parts) == 2:
            params["schema"] = table_parts[0]
            params["table_name"] = table_parts[1]
            
        else:
            params["schema"] = action.schema or "public"
            params["table_name"] = action.table

        params["column_name"] = action.column_name
        params["force"] = action.force or False

    elif action.type == "add_relationship":
        from_parts = action.from_table.split(".")
        to_parts = action.to_table.split(".")

        params["from_schema"] = from_parts[0] if len(from_parts) == 2 else (action.from_schema or "public")
        params["from_table"] = from_parts[-1]
        params["from_column"] = action.from_column

        params["to_schema"] = to_parts[0] if len(to_parts) == 2 else (action.to_schema or "public")
        params["to_table"] = to_parts[-1]
        params["to_column"] = action.to_column

    elif action.type == "remove_relationship":
        from_parts = action.from_table.split(".")

        params["from_schema"] = from_parts[0] if len(from_parts) == 2 else (action.from_schema or "public")
        params["from_table"] = from_parts[-1]
        params["from_column"] = action.from_column

    return params















@router.post('/ddl-edit')
def apply_ddl_edit(request: DDLEditRequest) -> DDLEditResponse:
    conn = None
    
    try:
        try:
            CanonicalSchemaModel.from_ddl(request.ddl)
            
        except SchemaValidationError as e:
            return DDLEditResponse(
                success = False,
                schema = None,
                ddl = None,
                error = "Schema validation error",
                details = str(e)
            )
            
        except Exception as e:
            return DDLEditResponse(
                success = False,
                schema = None,
                ddl = None,
                error = "DDL parsing failed",
                details = str(e)
            )
            
        conn = get_connection()
        success, error_msg = execute_ddl_text(conn, request.ddl)
        
        if not success:
            return DDLEditResponse(
                success = False,
                schema = None,
                ddl = None,
                error = "Database execution failed",
                details = error_msg
            )
            
        refreshed_schema = refresh_schema(conn)
        db_config = get_database_config()
        
        if db_config and db_config.dbname.startswith("schemasense_user_"):
            update_db_activity(db_config.dbname)
            
        return DDLEditResponse(
            success = True,
            schema = refreshed_schema.to_dict_for_api(),
            ddl = refreshed_schema.to_ddl(),
            error = None,
            details = None
        )
    
    
    
    except RuntimeError as e:
        return DDLEditResponse(
            success = False,
            schema = None,
            ddl = None,
            error = "Database connection unavailable",
            details = str(e)
        )
    
    except Exception as e:
        logger.error(f"Failed to apply DDL edits: {str(e)}", exc_info = True)
        return DDLEditResponse(
            success = False,
            schema = None,
            ddl = None,
            error = "Unexpected error",
            details = str(e)
        )
    
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
