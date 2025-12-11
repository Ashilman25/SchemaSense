from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import sql

from app.db import get_connection

router = APIRouter(prefix="/api/data", tags=["data"])

class InsertDataRequest(BaseModel):
    table: str = Field(..., description = "Fully qualified table name (schema.table)")
    rows: List[Dict[str, Any]] = Field(..., description = "List of row objects to insert")
    
    
class InsertDataResponse(BaseModel):
    success: bool
    rows_inserted: int
    message: str
    errors: Optional[List[str]] = None
    
