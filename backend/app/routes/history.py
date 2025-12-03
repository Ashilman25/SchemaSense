from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor

from app.db import get_connection

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoryItemCreate(BaseModel):
    question: str = Field(..., description = "The english question asked")
    sql: Optional[str] = Field(None, description = "The generated SQL query")
    status: str = Field(..., description = "Query status: success, error, or pending")
    execution_duration_ms: Optional[int] = Field(None, description = "Query execution time in milliseconds")
    
    
class HistoryItemResponse(BaseModel):
    id: int
    timestamp: datetime
    question: str
    sql: Optional[str]
    status: str
    execution_duration_ms: Optional[int]




_history: List[HistoryItem] = []


#get in memory list of recorded history items
@router.get("")
def list_history():
    return _history


#add new history entry
@router.post("")
def add_history(item: HistoryItem):
    _history.append(item)
    return {
        "saved": True, 
        "count": len(_history)
        }
