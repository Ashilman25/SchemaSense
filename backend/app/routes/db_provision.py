import psycopg2
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, Header, Depends
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db_provisioner import provision_database, DatabaseConfig
from app.db import set_database_config
from app.utils.session import get_or_create_session_id
from app.utils.logging_utils import get_secure_logger
from app.middleware.rate_limit import check_provision_rate_limit
from app.utils import audit_log

logger = get_secure_logger(__name__)
router = APIRouter(prefix = "/api/db", tags=["provisioning"])


def verify_admin_key(x_admin_key: Optional[str] = Header(None)):
    settings = get_settings()

    if not x_admin_key:
        logger.warning("Admin endpoint access attempted without API key")
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": "unauthorized",
                "message": "Admin API key required. Provide X-Admin-Key header."
            }
        )

    if x_admin_key != settings.admin_api_key:
        logger.warning("Admin endpoint access attempted with invalid API key",
                      provided_key_prefix=x_admin_key[:8] if x_admin_key else None)
        raise HTTPException(
            status_code=403,
            detail={
                "success": False,
                "error": "forbidden",
                "message": "Invalid admin API key"
            }
        )

    return True


class ProvisionRequest(BaseModel):
    mode: Optional[str] = Field(default = None, description = "Provisioning mode: 'managed'")
    loadSampleData: bool = Field(default = False, description = "Whether to load sample sales data")
    
class ProvisionResponse(BaseModel):
    success: bool
    mode: str
    connection: DatabaseConfig
    
class ProvisionErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    
class DeprovisionRequest(BaseModel):
    db_name: Optional[str] = None
    id: Optional[int] = None
    
def _check_quotas(session_id: str) -> tuple[bool, Optional[str]]:
    settings = get_settings()
    admin_dsn = settings.managed_pg_admin_dsn
    
    conn = None
    
    try:
        conn = psycopg2.connect(admin_dsn)
        
        with conn.cursor() as cur:
            cur.execute("""
                        SELECT COUNT(*) FROM provisioned_dbs
                        WHERE session_id = %s AND status = 'active'
                        """, (session_id,))
            session_count = cur.fetchone()[0]
            
            if session_count >= settings.provision_max_dbs_per_session:
                return False, f"Session quota exceeded. Maximum {settings.provision_max_dbs_per_session} databases per session."
            
            #global quota
            cur.execute("""
                        SELECT COUNT(*) FROM provisioned_dbs
                        WHERE status = 'active'
                        """)
            global_count = cur.fetchone()[0]
            
            if global_count >= settings.provision_global_max_dbs:
                return False, f"Global quota exceeded. Please try again later."
            
        return True, None
    
    except Exception as e:
        logger.error("Quota check failed", error = str(e))
        return True, None
    
    finally:
        if conn:
            conn.close()



def _verify_connectivity(db_config: DatabaseConfig) -> bool:
    from urllib.parse import quote_plus

    encoded_password = quote_plus(db_config.password)
    dsn = f"postgresql://{db_config.user}:{encoded_password}@{db_config.host}:{db_config.port}/{db_config.dbname}"
    conn = None

    try:
        conn = psycopg2.connect(dsn)

        with conn.cursor() as cur:
            cur.execute("SELECT 1") #ping
            result = cur.fetchone()

            return result[0] == 1

    except Exception as e:
        logger.error("Connectivity verification failed", db_name = db_config.dbname, error = str(e))
        return False
    
    finally:
        if conn:
            conn.close()



#body: {"mode": str, "loadSampleData" : bool}
#returns: {"success" : bool, "mode": str, "connection" : {db_model with all 5 things, host, port, name...}}
@router.post("/provision")
async def provision_db(request: Request, response: Response, body: ProvisionRequest):
    settings = get_settings()

    session_id = get_or_create_session_id(request, response)
    client_ip = request.client.host if request.client else "unknown"
    logger.info("Provision request received", session_id = session_id, load_sample = body.loadSampleData)

    # SECURITY: Rate limit provision requests (50 per hour by default)
    check_provision_rate_limit(request, session_id, max_requests_per_hour = 50)

    mode = body.mode or settings.provision_mode_default
    quota_ok, quota_error = _check_quotas(session_id)

    if not quota_ok:
        logger.warning("Quota exceeded", session_id = session_id, reason = quota_error)
        # AUDIT: Log quota violation
        audit_log.log_quota_exceeded(
            session_id = session_id,
            user_ip = client_ip,
            quota_type = "session" if "Session" in quota_error else "global",
            current_count = 0,  # Would need to extract from quota check
            limit = settings.provision_max_dbs_per_session if "Session" in quota_error else settings.provision_global_max_dbs
        )
        raise HTTPException(
            status_code = 429,
            detail = {
                "success" : False,
                "error" : "quota_exceeded",
                "message" : quota_error
            }
        )
        
    #provision the db
    try:
        db_config = provision_database(
            mode = mode,
            session_id = session_id,
            load_sample = body.loadSampleData
        )
        logger.info("Database provisioned successfully", db_name = db_config.dbname, session_id = session_id)

        if not _verify_connectivity(db_config):
            logger.error("Connectivity verification failed", db_name = db_config.dbname)
            raise Exception("Database created but connectivity verification failed")

        set_database_config(db_config, session_id)
        logger.info("Database config set for session", session_id = session_id, db_name = db_config.dbname)


        audit_log.log_db_provision_success(
            session_id = session_id,
            user_ip = client_ip,
            db_name = db_config.dbname,
            mode = mode,
            load_sample = body.loadSampleData
        )

        return {
            "success" : True,
            "mode" : mode,
            "connection" : db_config.dict()
        }

        


    except NotImplementedError as e:
        logger.error("Unsupported provisioning mode", mode = mode, session_id = session_id)
        raise HTTPException(
            status_code = 400,
            detail = {
                "success" : False,
                "error" : "unsupported_mode",
                "message" : str(e)
            }
        )

    except Exception as e:
        logger.error("Provisioning failed", session_id = session_id, error = str(e), exc_info = True)
        
        audit_log.log_db_provision_failure(
            session_id = session_id,
            user_ip = client_ip,
            error = str(e),
            mode = mode
        )
        
        raise HTTPException(
            status_code = 500,
            detail = {
                "success" : False,
                "error" : "provision_failed",
                "message" : f"Failed to provision database: {str(e)}"
            }
        )

    
    
    
#body: {db_name: str, id: int}, most likely not both, one or other   
    
@router.post("/deprovision")
async def deprovision_db(request: Request, body: DeprovisionRequest):
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    session_id = "admin"  # Deprovision is admin-only for now

    if not body.db_name and not body.id:
        raise HTTPException(
            status_code = 400,
            detail = {
                "success" : False,
                "error" : "missing_identifier",
                "message" : "Either db_name or id must be provided"
            }
        )

    admin_dsn = settings.managed_pg_admin_dsn
    conn = None
    
    try:
        conn = psycopg2.connect(admin_dsn)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            if body.db_name:
                cur.execute("""
                            SELECT id, db_name, db_role, status
                            FROM provisioned_dbs
                            WHERE db_name = %s
                            """, (body.db_name,))
            else:
                cur.execute("""
                            SELECT id, db_name, db_role, status
                            FROM provisioned_dbs
                            WHERE id = %s
                            """, (body.id,))
                
            row = cur.fetchone()
            if not row:
                raise HTTPException(
                    status_code = 404,
                    detail = {
                        "success" : False,
                        "error" : "not_found",
                        "message" : "Database not found in provisioned_dbs"
                    }
                )
                
            db_id, db_name, db_role, status = row
            
            if status == "deleted":
                return {
                    "success" : True,
                    "message" : f"Database {db_name} already marked as deleted"
                }
                
        #drop db and role
        with conn.cursor() as cur:
            logger.info("Dropping database", db_name = db_name, db_id = db_id)

            cur.execute("""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = %s AND pid <> pg_backend_pid()
                        """, (db_name,))

            cur.execute(f"DROP DATABASE IF EXISTS {db_name}")
            cur.execute(f"DROP ROLE IF EXISTS {db_role}")

            logger.info("Dropped database and role", db_name = db_name, db_role = db_role)

        #update metadata
        with conn.cursor() as cur:
            cur.execute("""
                        UPDATE provisioned_dbs
                        SET status = 'deleted'
                        WHERE id = %s
                        """, (db_id,))

        logger.info("Deprovisioned database", db_name = db_name, db_id = db_id)

        audit_log.log_db_deprovision_success(
            session_id = session_id,
            user_ip = client_ip,
            db_name = db_name,
            db_id = db_id
        )

        return {
            "success" : True,
            "message" : f"Database {db_name} deprovisioned successfully"
        }
    
    
    except HTTPException:
        raise

    except Exception as e:
        logger.error("Deprovisioning failed", error = str(e), exc_info = True)

        audit_log.log_db_deprovision_failure(
            session_id = session_id,
            user_ip = client_ip,
            db_name = body.db_name,
            error = str(e)
        )
        raise HTTPException(
            status_code = 500,
            detail = {
                "success" : False,
                "error" : "deprovision_failed",
                "message" : f"Failed to deprovision database: {str(e)}"
            }
        )
    
    finally:
        if conn:
            conn.close()


@router.get("/admin/active-dbs")
async def list_active_dbs(authorized: bool = Depends(verify_admin_key)):
    settings = get_settings()
    admin_dsn = settings.managed_pg_admin_dsn
    
    conn = None
    
    try:
        conn = psycopg2.connect(admin_dsn)
        
        with conn.cursor() as cur:
            cur.execute("""
                        SELECT id, session_id, db_name, db_role, created_at, last_used_at, mode, status
                        FROM provisioned_dbs
                        WHERE status = 'active'
                        ORDER BY last_used_at DESC
                        """)
            rows = cur.fetchall()
            active_dbs = []
            
            for row in rows:
                active_dbs.append({
                    "id" : row[0],
                    "session_id" : row[1],
                    "db_name" : row[2],
                    "db_role" : row[3],
                    "created_at" : row[4].isoformat() if row[4] else None,
                    "last_used_at" : row[5].isoformat() if row[5] else None,
                    "mode" : row[6],
                    "status" : row[7]
                })
                
            #also get counts
            cur.execute("""
                        SELECT COUNT(*) as total_active, COUNT(DISTINCT session_id) as unique_sessions
                        FROM provisioned_dbs
                        WHERE status = 'active'
                        """)
            stats = cur.fetchone()
            
            return {
                "success" : True,
                "databases" : active_dbs,
                "stats" : {
                    "total_active" : stats[0],
                    "unique_sessions" : stats[1],
                    "max_per_session" : settings.provision_max_dbs_per_session,
                    "global_max" : settings.provision_global_max_dbs
                }
            }
    
    
    except Exception as e:
        logger.error("Failed to list active DBs", error = str(e))
        raise HTTPException(
            status_code = 500,
            detail = {
                "success" : False,
                "error" : "list_failed",
                "message" : f"Failed to list active databases: {str(e)}"
            }
        )
    
    
    finally:
        if conn:
            conn.close()