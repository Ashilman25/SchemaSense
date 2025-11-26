from fastapi import APIRouter
from app.db import DatabaseConfig, get_database_config, set_database_config, get_connection


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

    except RuntimeError as e:
        # Restore old config on failure
        set_database_config(old_config) if old_config else None

        return {
            "success" : False,
            "message" : "Could not connect to database. Please verify your connection settings."
        }
    except Exception as e:
        # Restore old config on failure
        set_database_config(old_config) if old_config else None

        return {
            "success" : False,
            "message" : "An unexpected error occurred while connecting to the database."
        }

    return {
        "success" : True,
        "message" : "db connected"
    }
        


