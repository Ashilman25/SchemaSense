from fastapi import APIRouter
from app.db import DatabaseConfig, get_database_config, set_database_config, get_connection
from app.schema.cache import clear_schema_cache


router = APIRouter(prefix="/api/config", tags=["config"])


#just return db connection status
@router.get("/db")
def get_db_status():
    config = get_database_config()
    if config is None:
        return {"connected": False}

    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT 1;")
        cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {"connected": True}
    
    except Exception:
        return {"connected": False}


#save db config
@router.post("/db")
def set_db(config: DatabaseConfig):

    try:
        old_config = get_database_config()
        set_database_config(config)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1;")
        cur.fetchone()

        cur.close()
        conn.close()

        # Clear schema cache since DB config changed
        clear_schema_cache()

    except RuntimeError as e:
        # Restore old config on failure
        set_database_config(old_config) if old_config else None

        return {
            "success": False,
            "message": "Could not connect to database. Please verify your connection settings.",
            "error": str(e)
        }
    except Exception as e:
        # Restore old config on failure
        set_database_config(old_config) if old_config else None

        return {
            "success": False,
            "message": "An unexpected error occurred while connecting to the database.",
            "error": str(e)
        }

    return {
        "success" : True,
        "message" : "db connected"
    }
        


