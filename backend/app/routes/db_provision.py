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
    

