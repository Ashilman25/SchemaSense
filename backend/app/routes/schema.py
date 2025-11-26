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
    


