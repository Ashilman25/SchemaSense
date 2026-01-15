import psycopg2
import re
import time
import traceback
from fastapi import APIRouter, Request, Response, Depends
from app.db import DatabaseConfig, get_database_config, set_database_config, get_connection
from app.schema.cache import clear_schema_cache
from app.config import get_settings
from app.utils.session import get_or_create_session_id
from app.utils.logging_utils import get_secure_logger
from app.routes.db_provision import verify_admin_key

logger = get_secure_logger(__name__)
router = APIRouter(prefix="/api/config", tags=["config"])

USERNAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
def _validate_username(username: str) -> None:
    if not USERNAME_PATTERN.match(username):
        raise ValueError("Invalid username. Use letters, numbers, and underscores, starting with a letter or underscore.")


#just return db connection status
@router.get("/db")
def get_db_status(request: Request, response: Response):
    session_id = get_or_create_session_id(request, response)
    config = get_database_config(session_id)
    if config is None:
        return {"connected": False}

    try:
        conn = get_connection(session_id)
        cur = conn.cursor()

        cur.execute("SELECT 1;")
        cur.fetchone()

        cur.close()
        conn.close()

        return {
            "connected": True,
            "connection": {
                "host": config.host,
                "port": config.port,
                "dbname": config.dbname,
                "user": config.user,
                "password": config.password
            }
        }

    except Exception:
        return {"connected": False}


@router.get("/db/session")
def get_session_db_config(request: Request, response: Response, authorized: bool = Depends(verify_admin_key)):
    session_id = get_or_create_session_id(request, response)
    settings = get_settings()
    admin_dsn = settings.managed_pg_admin_dsn

    conn = None

    try:
        conn = psycopg2.connect(admin_dsn)

        with conn.cursor() as cur:
            cur.execute("""
                        SELECT db_name, db_role, created_at, last_used_at
                        FROM provisioned_dbs
                        WHERE session_id = %s AND status = 'active'
                        ORDER BY last_used_at DESC
                        LIMIT 1
                        """, (session_id,))

            row = cur.fetchone()

            if not row:
                return {
                    "success" : True,
                    "has_provisioned_db" : False,
                    "message" : "No active provisioned database found for this session"
                }

            db_name, db_role, created_at, last_used_at = row

            match = re.match(r'postgresql://[^@]+@([^:]+):(\d+)/', admin_dsn)
            
            if match:
                host = match.group(1)
                port = int(match.group(2))
                
            else:
                host = "localhost"
                port = 5432

            return {
                "success" : True,
                "has_provisioned_db" : True,
                "db_info" : {
                    "host" : host,
                    "port" : port,
                    "dbname" : db_name,
                    "user" : db_role,
                    "created_at" : created_at.isoformat() if created_at else None,
                    "last_used_at" : last_used_at.isoformat() if last_used_at else None
                },
                "note": "Password not included. Use sessionStorage credentials for reconnect."
            }

    except Exception as e:
        logger.error("Failed to fetch session DB config", session_id = session_id, error = str(e))
        
        return {
            "success" : False,
            "message" : f"Failed to retrieve session database config: {str(e)}"
        }

    finally:
        if conn:
            conn.close()


#disconnect from db
@router.delete("/db")
def disconnect_db(request: Request, response: Response):
    session_id = get_or_create_session_id(request, response)
    set_database_config(None, session_id)
    clear_schema_cache()

    return {
        "success" : True,
        "message" : "Disconnected from database"
    }
    
    
    
    
#update db credentials
#1. altering the password in PostgreSQL, if the user changes
#2. Creating a new user and dropping the old one, if username changes
#3. Saving hte new credentials in SchemaSense config
@router.patch("/db")
def update_db_credentials(request: Request, response: Response, config: DatabaseConfig):
    session_id = get_or_create_session_id(request, response)
    old_config = get_database_config(session_id)
    if not old_config:
        return {
            "success" : False,
            "message" : "No existing connection to update"
        }

    try:
        _validate_username(config.user)

        conn = get_connection(session_id)
        cur = conn.cursor()
        cur.execute("SELECT 1;") #ensures connected

        username_changed = old_config.user != config.user
        password_changed = old_config.password != config.password
        
        #password change
        if password_changed and not username_changed:
            cur.execute(f"ALTER USER {config.user} WITH PASSWORD %s;", (config.password,))
            conn.commit()
            
        
        #username change
        if username_changed:
            
            #create new user with same password
            cur.execute(f"CREATE USER {config.user} WITH PASSWORD %s;", (config.password,))
            
            #grant db privileges
            cur.execute(f"GRANT ALL PRIVILEGES ON DATABASE {config.dbname} TO {config.user};")
            
            #get all schemas in db
            cur.execute("""
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                        """)
            schemas = [row[0] for row in cur.fetchall()]
            
            #grant privileges on all schemas and their objs
            for schema in schemas:
                cur.execute(f"GRANT ALL PRIVILEGES ON SCHEMA {schema} TO {config.user};")
                
                #privilees on all
                cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} TO {config.user};")
                cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema} TO {config.user};")
                cur.execute(f"GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA {schema} TO {config.user};")
                
                #set default privileges
                cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON TABLES TO {config.user};")
                cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON SEQUENCES TO {config.user};")
                cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT ALL ON FUNCTIONS TO {config.user};")
                
            conn.commit()
            
        cur.close()
        conn.close()

        set_database_config(config, session_id)

        #test connect
        conn = get_connection(session_id)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        
        #if username changed, drop old user using admin connection
        if username_changed:
            try:
                settings = get_settings()
                admin_dsn = settings.managed_pg_admin_dsn
                
                match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', admin_dsn)
                if match:
                    admin_user, admin_pass, host, port, _ = match.groups()
                    
                    #connect to user with admin info
                    user_db_dsn = f"postgresql://{admin_user}:{admin_pass}@{host}:{port}/{config.dbname}"
                    
                else:
                    user_db_dsn = admin_dsn
                    
                admin_conn = psycopg2.connect(user_db_dsn)
                admin_conn.autocommit = True
                
                with admin_conn.cursor() as admin_cur:
                    #terminate any active connections from old user
                    admin_cur.execute("""
                                      SELECT pg_terminate_backend(pid)
                                      FROM pg_stat_activity
                                      WHERE usename = %s AND datname = %s AND pid <> pg_backend_pid()
                                      """, (old_config.user, config.dbname))
                    
                    time.sleep(0.1)
                    
                    #reassign ownership of objs from old to new user
                    admin_cur.execute(f"REASSIGN OWNED BY {old_config.user} TO {config.user}")
                    
                    #drop any remaining objs and privileges from previous user
                    admin_cur.execute(f"DROP OWNED BY {old_config.user};")
                    admin_cur.execute(f"DROP USER {old_config.user}")
                    
                    print(f"Successfully dropped old user: {old_config.user}")
                    
                admin_conn.close()
                
            
            except Exception as e:
                #if cant drop old user, jus log dont fail
                traceback.print_exc()
                
                if 'admin_conn' in locals() and admin_conn:
                    admin_conn.close()
                    
        cur.close()
        conn.close()
        
        clear_schema_cache()
        
        return {
            "success" : True,
            "message" : "Database credentials updated successfully"
        }
                
                
                    
    except Exception as e:
        set_database_config(old_config, session_id)

        error_msg = str(e)
        
        if "permission denied to create role" in error_msg.lower() or "createrole" in error_msg.lower():
            return {
                "success" : False,
                "message" : "Your database user doesn't have permission to create new users. To change your username, you'll need to provision a new database with updated permissions or only change your password (which doesn't require CREATEROLE privileges).",
                "error" : error_msg
            }
            
        return {
            "success" : False,
            "message" : f"Failed to update credentials: {error_msg}",
            "error" : error_msg
        }
    
    
    
    
    
    

#save db config
@router.post("/db")
def set_db(request: Request, response: Response, config: DatabaseConfig):
    session_id = get_or_create_session_id(request, response)

    try:
        old_config = get_database_config(session_id)
        set_database_config(config, session_id)

        conn = get_connection(session_id)
        cur = conn.cursor()

        cur.execute("SELECT 1;")
        cur.fetchone()

        cur.close()
        conn.close()

        # Clear schema cache since DB config changed
        clear_schema_cache()

    except RuntimeError as e:
        # Restore old config on failure
        if old_config:
            set_database_config(old_config, session_id)

        return {
            "success": False,
            "message": "Could not connect to database. Please verify your connection settings.",
            "error": str(e)
        }
    except Exception as e:
        # Restore old config on failure
        if old_config:
            set_database_config(old_config, session_id)

        return {
            "success": False,
            "message": "An unexpected error occurred while connecting to the database.",
            "error": str(e)
        }

    return {
        "success" : True,
        "message" : "db connected"
    }
        
