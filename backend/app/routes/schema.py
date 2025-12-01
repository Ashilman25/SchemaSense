from fastapi import APIRouter, HTTPException
from app.models.schema_model import CanonicalSchemaModel
from app.schema.cache import get_or_refresh_schema
from app.db import get_connection

router = APIRouter(prefix="/api/schema", tags=["schema"])


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


