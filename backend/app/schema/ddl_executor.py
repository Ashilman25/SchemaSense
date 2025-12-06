from typing import List, Tuple, Optional, Dict, Any
import logging
from psycopg2.extensions import connection as PgConnection
from app.models.schema_model import CanonicalSchemaModel

logger = logging.getLogger(__name__)

class DDLExecutionError(Exception):
    pass



def generate_ddl_from_action(action_type: str, params: Dict[str, Any], schema_model: CanonicalSchemaModel) -> str:
    if action_type == "add_table":
        return _generate_create_table(params)

    elif action_type == "rename_table":
        return _generate_rename_table(params)

    elif action_type == "drop_table":
        return _generate_drop_table(params)

    elif action_type == "add_column":
        return _generate_add_column(params)

    elif action_type == "rename_column":
        return _generate_rename_column(params)

    elif action_type == "drop_column":
        return _generate_drop_column(params)

    elif action_type == "add_relationship":
        return _generate_add_foreign_key(params)

    elif action_type == "remove_relationship":
        return _generate_drop_foreign_key(params)

    else:
        raise ValueError(f"Unknown action type: {action_type}")
    
    
    
def _generate_create_table(params: Dict[str, Any]) -> str:
    name = params.get("name")
    schema = params.get("schema", "public")
    columns = params.get("columns", [])
    
    if not name:
        raise ValueError("Table name is required for add_table action")
    
    if not columns:
        return f'CREATE TABLE "{schema}".{name}" ()'
    
    col_defs = []
    pk_columns = []
    
    for col in columns:
        col_name = col.get("name")
        col_type = col.get("type", "text")
        nullable = col.get("nullable", True)
        is_pk = col.get("is_pk", False)
        
        parts = [f'"{col_name}"', col_type]
        
        if not nullable:
            parts.append("NOT NULL")
            
        col_defs.append(" ".join(parts))
        
        if is_pk:
            pk_columns.append(col_name)
            
    #add pk if has
    if pk_columns:
        pk_cols_quoted = ", ".join(f'"{c}"' for c in pk_columns)
        pk_constraint = f'CONSTRAINT "{name}_pkey" PRIMARY KEY ({pk_cols_quoted})'
        col_defs.append(pk_constraint)
        
    columns_sql = ",\n    ".join(col_defs)
    return f'CREATE TABLE "{schema}"."{name}" (\n    {columns_sql}\n)'