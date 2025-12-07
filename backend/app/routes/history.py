from typing import List, Optional, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor
import psycopg2.errors

from app.db import get_connection

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoryItemCreate(BaseModel):
    question: str = Field(..., description = "The english question asked")
    sql: Optional[Union[str, List[str]]] = Field(None, description = "The generated SQL query")
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
    conn = None
    cursor = None
    
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

    except Exception as e:
        print(f"Warning: Failed to initialize history table: {str(e)}")
        
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass    
    
    

@router.post("", response_model = dict)
def add_history(item: HistoryItemCreate):
    try:
        _init_history_table()
        
        conn = get_connection()
        cursor = conn.cursor()

        sql_text = None
        if isinstance(item.sql, list):
            sql_text = ";\n".join(item.sql)
            
        else:
            sql_text = item.sql
        
        cursor.execute("""
                       INSERT INTO schemasense.query_history (question, sql, status, execution_duration_ms)
                       VALUES (%s, %s, %s, %s)
                       RETURNING id
                       """, (item.question, sql_text, item.status, item.execution_duration_ms))
        
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
    conn = None
    cursor = None
    
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

        #convert to the history item response format
        history = []
        for each in rows:
            history.append(HistoryItemResponse(
                id = each["id"],
                timestamp = each["timestamp"],
                question = each["question"],
                sql = each["sql"],
                status = each["status"],
                execution_duration_ms = each["execution_duration_ms"]
            ))

        return history

    except Exception as e:
        # If table doesn't exist, return empty history instead of error
        if isinstance(e, psycopg2.errors.UndefinedTable):
            return []
        
        raise HTTPException(status_code = 500, detail = f"Failed to retrieve history: {str(e)}")

    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass


@router.delete("/{history_id}", response_model = dict)
def delete_history(history_id: int):
    try:
        _init_history_table()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
                       DELETE FROM schemasense.query_history
                       WHERE id = %s
                       RETURNING id
                       """, (history_id,))

        deleted_row = cursor.fetchone()

        if not deleted_row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code = 404, detail = f"History item with id {history_id} not found")

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "success" : True,
            "id" : deleted_row[0],
            "message" : "History item deleted successfully"
        }

    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Failed to delete history: {str(e)}")
