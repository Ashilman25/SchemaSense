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
    
    

@router.post("", response_model = dict)
def add_history(item: HistoryItemCreate):
    try:
        _init_history_table()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
                       INSERT INTO schemasense.query_history (question, sql, status, execution_duration_ms)
                       VALUES (%s, %s, %s, %s)
                       RETURNING id
                       """, (item.question, item.sql, item.status, item.execution_duration_ms))
        
        history_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "saved" : True,
            "id" : history_id
        }
    
    
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Failed to save history: {str(e)}")
    
    
    
    
@router.get("", response_model = List[HistoryItemResponse])
def list_history(limit: int = 50):
    try:
        limit = min(limit, 200) #might change limit idk
        _init_history_table()
        
        conn = get_connection()
        cursor = conn.cursor(cursor_factory = RealDictCursor) #makes it return the rows as dicts instead of tuples
        
        cursor.execute("""
                       SELECT id, timestamp, question, sql, status, execution_duration_ms
                       FROM schemasense.query_history
                       ORDER BY timestamp DESC
                       LIMIT %s
                       """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        #convert to the history item response format
        history = []
        for each in rows:
            id = each["id"]
            timestamp = each["timestamp"]
            question = each["question"]
            sql = each["sql"]
            status = each["status"]
            execution_duration_ms = each["execution_duration_ms"]
            
            history.append(HistoryItemResponse(id, timestamp, question, sql, status, execution_duration_ms))
            
            
        return history
    
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Failed to retrieve history: {str(e)}")