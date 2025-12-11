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
    



@router.post("/insert", response_model = InsertDataResponse)
async def insert_data(request: InsertDataRequest):
    try:
        parts = request.table.split('.')
        if len(parts) != 2:
            raise HTTPException(
                status_code = 400,
                detail = "Table name must be in format 'schema.table'"
            )
            
        schema_name, table_name = parts
        
        if not request.rows or len(request.rows) == 0:
            raise HTTPException(
                status_code = 400,
                detail = "No rows provided for insertion"
            )
            
        conn = get_connection()
        if not conn:
            raise HTTPException(
                status_code = 500,
                detail = "Database connection not configured"
            )
            
        cursor = conn.cursor()
        try:
            #validate exists
            cursor.execute("""
                           SELECT COUNT(*)
                           FROM information_schema.tables
                           WHERE table_schema = %s AND table_name = %s
                           """, (schema_name, table_name))
            
            if cursor.fetchone()[0] == 0:
                raise HTTPException(
                    status_code = 404,
                    detail = f"Table {request.table} does not exist"
                )
                
            first_row = request.rows[0]
            columns = list(first_row.keys())
            
            if not columns:
                raise HTTPException(
                    status_code = 400,
                    detail = "Row data must contain at least one column"
                )
                
                
            insert_query = sql.SQL("INSERT INTO {schema}.{table} ({columns}) VALUES ({placeholders})").format(
                schema = sql.Identifier(schema_name),
                table = sql.Identifier(table_name),
                columns = sql.SQL(', ').join(map(sql.Identifier, columns)),
                placeholders = sql.SQL(', ').join([sql.Placeholder()] * len(columns))
            )
            
            rows_inserted = 0
            errors = []
            
            for idx, row in enumerate(request.rows):
                try:
                    values = []
                    
                    for col in columns:
                        val = row.get(col)
                        
                        if val == '' or val == 'null' or val is None:
                            values.append(None)
                        else:
                            values.append(val)
                            
                    cursor.execute(insert_query, values)
                    rows_inserted += 1
                
                except psycopg2.Error as e:
                    error_msg = f"Row {idx + 1}: {str(e).split('DETAIL:')[0].strip()}"
                    errors.append(error_msg)
                    
            if rows_inserted > 0:
                conn.commit()
                
                return InsertDataResponse(
                    success = True,
                    rows_inserted = rows_inserted,
                    message = f"Successfully inserted {rows_inserted} row{'s' if rows_inserted != 1 else ''}",
                    errors = errors if errors else None
                )
                
            else:
                conn.rollback()
                raise HTTPException(
                    status_code = 400,
                    detail = f"Failed to insert any rows. Errors: {'; '.join(errors)}"
                )
                
        except HTTPException:
            conn.rollback()
            raise
        
        except psycopg2.Error as e:
            conn.rollback()
            error_detail = str(e)
            
            if 'DETAIL:' in error_detail:
                error_detail = error_detail.split('DETAIL:')[0].strip()
                
            raise HTTPException(
                status_code = 400,
                detail = f"Database error: {error_detail}"
            )
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(
                status_code = 500,
                detail = f"Unexpected error during insertion: {str(e)}"
            )
            
        finally:
            cursor.close()
            conn.close()
    
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Failed to insert data: {str(e)}"
        )
        
        
        
        
        
        
@router.post("/preview")
async def preview_data(request: InsertDataRequest):
    try:
        parts = request.table.split('.')
        if len(parts) != 2:
            raise HTTPException(
                status_code = 400,
                detail = "Table name must be in format 'schema.table'"
            )
            
        schema_name, table_name = parts
        
        conn = get_connection()
        if not conn:
            raise HTTPException(
                status_code = 500,
                detail = "Database connection not configured"
            )
            
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                           SELECT column_name, data_type, is_nullable
                           FROM information_schema.columns
                           WHERE table_schema = %s AND table_name = %s
                           ORDER BY ordinal_position
                           """, (schema_name, table_name))
            table_columns = cursor.fetchall()
            
            if not table_columns:
                raise HTTPException(
                    status_code = 404,
                    detail = f"Table {request.table} does not exist"
                )
                
            column_info = {
                col[0] : {
                    'data_type' : col[1],
                    'is_nullable' : col[2] == 'YES'
                }
                for col in table_columns
            }
            
            if request.rows:
                first_row = request.rows[0]
                request_columns = set(first_row.keys())
                table_column_names = set(column_info.keys())
                
                extra_columns = request_columns - table_column_names
                
                return {
                    'valid' : len(extra_columns) == 0,
                    'table_columns' : column_info,
                    'extra_columns' : list(extra_columns) if extra_columns else [],
                    'row_count' : len(request.rows)
                }
                
            return {
                'valid' : True,
                'table_columns' : column_info,
                'extra_columns' : [],
                'row_count' : 0
            }
        
        
        finally:
            cursor.close()
            conn.close()
    
    
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Failed to preview data: {str(e)}"
        )