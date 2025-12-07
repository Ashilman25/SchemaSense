from typing import List, Tuple
import sqlglot
from sqlglot import exp
from app.models.schema_model import CanonicalSchemaModel


class SQLValidationError(Exception):
    pass


def validate_and_normalize_sql(sql: str, schema_model: CanonicalSchemaModel) -> Tuple[str, List[str]]:
    try:
        statements = sqlglot.parse(sql, read = "postgres")
        
    except sqlglot.errors.ParseError as e:
        raise SQLValidationError(f"SQL parsing failed: {str(e)}")

    if not statements:
        raise SQLValidationError("No SQL statement provided.")

    if len(statements) != 1:
        raise SQLValidationError("Only a single SQL statement is allowed per request.")

    statement = statements[0]

    _reject_destructive_operations(statement)
    _enforce_allowed_statement(statement)

    warnings: List[str] = []
    if isinstance(statement, (exp.Select, exp.Union, exp.With, exp.Subquery, exp.Insert)):
        schema_warnings = _validate_schema_references(statement, schema_model)
        warnings.extend(schema_warnings)
    
    try:
        normalized_sql = statement.sql(dialect = "postgres")
        
    except Exception as e:
        raise SQLValidationError(f"SQL normalization failed: {str(e)}")

    return normalized_sql, warnings







def _reject_destructive_operations(statement: exp.Expression) -> None:
    for node in statement.walk():
        if isinstance(node, (exp.Drop, exp.Delete, exp.Update, exp.TruncateTable)):
            raise SQLValidationError(f"Disallowed operation: {type(node).__name__}. Destructive statements are not permitted.")





#allows only select, union, with, insert, create table, create scheme, alter, add column, or rename
def _enforce_allowed_statement(statement: exp.Expression) -> None:
    if isinstance(statement, (exp.Select, exp.Union, exp.With, exp.Subquery)):
        return

    if isinstance(statement, exp.Insert):
        return

    if isinstance(statement, exp.Create):
        if _is_safe_create(statement):
            return
        
        raise SQLValidationError("Only CREATE TABLE or CREATE SCHEMA statements are allowed.")

    if isinstance(statement, exp.Alter):
        if _is_safe_alter_table_non_destructive(statement):
            return
        
        raise SQLValidationError("Only ALTER TABLE ... ADD COLUMN or RENAME is allowed.")

    raise SQLValidationError(
        f"Operation not allowed: {type(statement).__name__}. "
        "Only SELECT/INSERT/CREATE TABLE or SCHEMA/ALTER TABLE ADD COLUMN are permitted."
    )


#only allow create table or create schema
def _is_safe_create(statement: exp.Create) -> bool:
    target = statement.this
    kind = (statement.args.get("kind") or "").upper() if statement.args.get("kind") else None

    if kind == "SCHEMA":
        return True

    if isinstance(target, exp.Schema):
        return True

    if isinstance(target, exp.Table):
        return kind in (None, "TABLE")

    return False


#only allow alter table, add col, or rename
def _is_safe_alter_table_non_destructive(statement: exp.Alter) -> bool:
    if not isinstance(statement.this, exp.Table):
        return False

    actions = (
        statement.args.get("actions")
        or statement.expressions
        or statement.args.get("expressions")
        or []
    )
    if not actions:
        return False

    for action in actions:
        if isinstance(action, exp.ColumnDef):
            continue

        action_sql = action.sql(dialect = "postgres") if hasattr(action, "sql") else str(action)
        action_sql_upper = action_sql.upper()
        
        if ("ADD" in action_sql_upper and "COLUMN" in action_sql_upper) or ("RENAME" in action_sql_upper and "TO" in action_sql_upper):
            continue

        return False

    return True



def _validate_schema_references(parsed: exp.Expression, schema_model: CanonicalSchemaModel) -> List[str]:
    warnings = []


    valid_tables = set()
    table_to_columns = {}

    for fully_qualified_name, table in schema_model.tables.items():
        valid_tables.add(fully_qualified_name.lower())
        valid_tables.add(table.name.lower())

        table_columns = {col.name.lower() for col in table.columns}
        table_to_columns[table.name.lower()] = table_columns
        table_to_columns[fully_qualified_name.lower()] = table_columns


    referenced_tables = set()
    table_aliases = {}  

    for table_node in parsed.find_all(exp.Table):
        table_name = table_node.name.lower()

        if table_node.db:
            full_name = f"{table_node.db.lower()}.{table_name}"
            referenced_tables.add(full_name)
            actual_table = full_name
        else:
            referenced_tables.add(table_name)
            actual_table = table_name


        if table_node.alias:
            alias = table_node.alias.lower()
            table_aliases[alias] = actual_table

            if actual_table in table_to_columns:
                table_to_columns[alias] = table_to_columns[actual_table]


        if table_name not in valid_tables:
            if table_node.db:
                full_name = f"{table_node.db}.{table_name}"
                
                if full_name.lower() not in valid_tables:
                    warnings.append(f"Table '{full_name}' not found in schema")
                    
            else:
                warnings.append(f"Table '{table_name}' not found in schema")


    for column_node in parsed.find_all(exp.Column):
        column_name = column_node.name.lower()

        if column_name == "*":
            continue

        if column_node.table:
            table_name = column_node.table.lower()
            if table_name in table_to_columns:
                if column_name not in table_to_columns[table_name]:
                    warnings.append(f"Column '{column_name}' not found in table '{table_name}'")

        else:
            found = False
            
            for table_name in referenced_tables:
                if table_name in table_to_columns:
                    if column_name in table_to_columns[table_name]:
                        found = True
                        break

            if not found and referenced_tables:
                warnings.append(f"Column '{column_name}' not found in any referenced tables")

    return warnings
