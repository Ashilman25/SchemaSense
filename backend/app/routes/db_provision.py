import logging
import psycopg2
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db_provisioner import provision_database, DatabaseConfig
from app.db import set_database_config
from app.utils.session import get_or_create_session_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix = "/api/db", tags=["provisioning"])


class ProvisionRequest(BaseModel):
    mode: Optional[str] = Field(default = None, description = "Provisioning mode: 'managed'")
    loadSampleData: bool = Field(default = False, description = "Whether to load sample sales data")
    
class ProvisionErrorResponse(BaseModel):
    success: bool
    mode: str
    connection: DatabaseConfig
    
class ProvisionErrorResponse(BaseModel):
    success: bool = False
    error: str
    messsage: str
    
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
        logger.error(f"Quota check failed: {str(e)}")
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
        logger.error(f"Connectivity verification failed: {str(e)}")
        return False
    
    finally:
        if conn:
            conn.close()
