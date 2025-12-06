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



#TABLE EDITING
def _generate_rename_table(params: Dict[str, Any]) -> str:
    old_name = params.get("old_name")
    new_name = params.get("new_name")
    schema = params.get("schema", "public")
    
    if not old_name or not new_name:
        raise ValueError("Both old_name and new_name are required for rename_table action")
    
    return f'ALTER TABLE "{schema}"."{old_name}" RENAME TO "{new_name}"'


def _generate_drop_table(params: Dict[str, Any]) -> str:
    name = params.get("name")
    schema = params.get("schema", "public")
    force = params.get("force", False)

    if not name:
        raise ValueError("Table name is required for drop_table action")

    cascade = " CASCADE" if force else ""
    return f'DROP TABLE "{schema}"."{name}"{cascade}'
    
    

#COLUMN EDITING
def _generate_add_column(params: Dict[str, Any]) -> str:
    table_name = params.get("table_name")
    schema = params.get("schema", "public")
    column = params.get("column")

    if not table_name or not column:
        raise ValueError("table_name and column are required for add_column action")

    col_name = column.get("name")
    col_type = column.get("type", "text")
    nullable = column.get("nullable", True)

    parts = [f'"{col_name}"', col_type]

    if not nullable:
        parts.append("NOT NULL")

    column_def = " ".join(parts)
    return f'ALTER TABLE "{schema}"."{table_name}" ADD COLUMN {column_def}'


def _generate_rename_column(params: Dict[str, Any]) -> str:
    table_name = params.get("table_name")
    schema = params.get("schema", "public")
    old_col = params.get("old_col")
    new_col = params.get("new_col")

    if not table_name or not old_col or not new_col:
        raise ValueError("table_name, old_col, and new_col are required for rename_column action")

    return f'ALTER TABLE "{schema}"."{table_name}" RENAME COLUMN "{old_col}" TO "{new_col}"'


def _generate_drop_column(params: Dict[str, Any]) -> str:
    table_name = params.get("table_name")
    schema = params.get("schema", "public")
    column_name = params.get("column_name")
    force = params.get("force", False)

    if not table_name or not column_name:
        raise ValueError("table_name and column_name are required for drop_column action")

    cascade = " CASCADE" if force else ""
    return f'ALTER TABLE "{schema}"."{table_name}" DROP COLUMN "{column_name}"{cascade}'
    
    
    
#FOREIGN KEYS
def _generate_add_foreign_key(params: Dict[str, Any]) -> str:
    from_table = params.get("from_table")
    from_schema = params.get("from_schema", "public")
    from_column = params.get("from_column")
    to_table = params.get("to_table")
    to_schema = params.get("to_schema", "public")
    to_column = params.get("to_column")

    if not all([from_table, from_column, to_table, to_column]):
        raise ValueError("from_table, from_column, to_table, and to_column are required for add_relationship action")

    constraint_name = f"{from_table}_{from_column}_fkey"

    return (
        f'ALTER TABLE "{from_schema}"."{from_table}" '
        f'ADD CONSTRAINT "{constraint_name}" '
        f'FOREIGN KEY ("{from_column}") '
        f'REFERENCES "{to_schema}"."{to_table}" ("{to_column}")'
    )


def _generate_drop_foreign_key(params: Dict[str, Any]) -> str:
    from_table = params.get("from_table")
    from_schema = params.get("from_schema", "public")
    from_column = params.get("from_column")

    if not all([from_table, from_column]):
        raise ValueError("from_table and from_column are required for remove_relationship action")

    constraint_name = f"{from_table}_{from_column}_fkey"

    return f'ALTER TABLE "{from_schema}"."{from_table}" DROP CONSTRAINT "{constraint_name}"'