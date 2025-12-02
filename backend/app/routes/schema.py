from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from app.models.schema_model import CanonicalSchemaModel, Column, SchemaValidationError
from app.schema.cache import get_or_refresh_schema, set_cached_schema
from app.db import get_connection

router = APIRouter(prefix="/api/schema", tags=["schema"])



class ERAction(BaseModel):
    type: str
    name: Optional[str] = None
    schema: Optional[str] = "public"
    table: Optional[str] = None
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


