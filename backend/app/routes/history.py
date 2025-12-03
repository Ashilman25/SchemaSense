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
    
    

def _init_history_table():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("CREATE SCHEMA IF NOT EXISTS schemasense;")
        
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS schemasense.query_history(
                           id SERIAL PRIMARY KEY,
                           timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                           question TEXT NOT NULL,
                           sql TEXT,
                           status VARCHAR(50) NOT NULL DEFAULT 'pending',
                           execution_duration_ms INTEGER,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       );
                       """)
        
        cursor.execute("""
                       CREATE INDEX IF NOT EXISTS idx_query_history_timestamp
                       ON schemasense.query_history(timestamp DESC);
                       """)
        
        cursor.execute("""
                       CREATE INDEX IF NOT EXISTS idx_query_history_status
                       ON schemasense.query_history(status);
                       """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception:
        pass    
    
    





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
