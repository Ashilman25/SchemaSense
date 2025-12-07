from typing import List, Tuple
import copy
import sqlglot
from sqlglot import exp
from app.models.schema_model import CanonicalSchemaModel, Table, Column


class SQLValidationError(Exception):
    pass


def validate_and_normalize_sql(sql: str, schema_model: CanonicalSchemaModel) -> Tuple[List[str], List[str]]:
    try:
        statements = sqlglot.parse(sql, read = "postgres")
        
    except sqlglot.errors.ParseError as e:
        raise SQLValidationError(f"SQL parsing failed: {str(e)}")

    if not statements:
        raise SQLValidationError("No SQL statement provided.")

    normalized_statements: List[str] = []
    warnings: List[str] = []
    temp_tables = copy.deepcopy(schema_model.tables)

    for statement in statements:
        _reject_destructive_operations(statement)
        _enforce_allowed_statement(statement)

        # track newly created or altered tables in this batch so subsequent statements validate correctly
        if isinstance(statement, exp.Create) and _is_safe_create(statement):
            table_info = _extract_table_from_create(statement)
            if table_info:
                schema_name, table_name, columns = table_info
                fqn = f"{schema_name}.{table_name}"
                temp_tables[fqn] = Table(
                    name=table_name,
                    schema=schema_name,
                    columns=columns or []
                )

        elif isinstance(statement, exp.Alter) and _is_safe_alter_table_non_destructive(statement):
            _apply_alter_to_temp_tables(statement, temp_tables)

        # build a transient schema model for validation that includes any created/altered tables from this batch
        temp_model = CanonicalSchemaModel(
            tables=temp_tables,
            relationships=[]
        )

        if isinstance(statement, (exp.Select, exp.Union, exp.With, exp.Subquery, exp.Insert)):
            schema_warnings = _validate_schema_references(statement, temp_model)
            warnings.extend(schema_warnings)
        
        try:
            normalized_statements.append(statement.sql(dialect = "postgres"))
        except Exception as e:
            raise SQLValidationError(f"SQL normalization failed: {str(e)}")

    return normalized_statements, warnings







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
    derived_columns = set()

    for fully_qualified_name, table in schema_model.tables.items():
        valid_tables.add(fully_qualified_name.lower())
        valid_tables.add(table.name.lower())

        table_columns = {col.name.lower() for col in table.columns}
        table_to_columns[table.name.lower()] = table_columns
        table_to_columns[fully_qualified_name.lower()] = table_columns

    #get col info from SELECT
    if isinstance(parsed, (exp.Select, exp.Union, exp.With, exp.Subquery)):
        if hasattr(parsed, "selects") and parsed.selects:
            select_expressions = parsed.selects
            
        else:
            select_expressions = parsed.expressions or []

        for expr in select_expressions:
            alias_name = None
            if isinstance(expr, exp.Alias):
                alias_name = expr.alias
                
            else:
                alias_expr = expr.args.get("alias")
                if alias_expr is not None:
                    alias_name = getattr(alias_expr, "name", None) or str(alias_expr)

            if alias_name:
                derived_columns.add(str(alias_name).lower())


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

        if not column_node.table and column_name in derived_columns:
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


def _extract_table_from_create(statement: exp.Create):
    target = statement.this
    schema_name = "public"
    table_name = None

    if isinstance(target, exp.Schema):
        if isinstance(target.this, exp.Table):
            table_name = target.this.name
            schema_name = target.this.db or target.name or schema_name
            
        else:
            table_name = target.name
            schema_name = target.db or schema_name
            
    elif isinstance(target, exp.Table):
        table_name = target.name
        schema_name = target.db or schema_name

    if not table_name:
        return None

    cols: List[Column] = []
    for col_def in statement.find_all(exp.ColumnDef):
        col_name = col_def.this.name if hasattr(col_def.this, "name") else str(col_def.this)
        kind_expr = col_def.args.get("kind")
        col_type = kind_expr.sql(dialect="postgres") if kind_expr is not None else "text"
        cols.append(Column(name=col_name, type=col_type, nullable=True, is_pk=False, is_fk=False))

    return schema_name, table_name, cols







def _apply_alter_to_temp_tables(statement: exp.Alter, temp_tables: dict):
    if not isinstance(statement.this, exp.Table):
        return

    schema_name = statement.this.db or "public"
    table_name = statement.this.name
    fqn = f"{schema_name}.{table_name}"
    table_obj = temp_tables.get(fqn)
    
    if not table_obj:
        return

    actions = (
        statement.args.get("actions")
        or statement.expressions
        or statement.args.get("expressions")
        or []
    )

    for action in actions:
        # ADD COLUMN
        if isinstance(action, exp.ColumnDef):
            col_name = action.this.name if hasattr(action.this, "name") else str(action.this)
            kind_expr = action.args.get("kind")
            col_type = kind_expr.sql(dialect = "postgres") if kind_expr is not None else "text"
            table_obj.columns.append(Column(name = col_name, type = col_type, nullable = True, is_pk = False, is_fk = False))
            continue

        action_sql = action.sql(dialect="postgres") if hasattr(action, "sql") else str(action)
        upper_sql = action_sql.upper()

        # RENAME COLUMN
        if "RENAME" in upper_sql and "COLUMN" in upper_sql:
            parts = action_sql.split()
            
            if "COLUMN" in parts and "TO" in parts:
                try:
                    idx_col = parts.index("COLUMN")
                    idx_to = parts.index("TO")
                    old_col = parts[idx_col + 1].strip('"')
                    new_col = parts[idx_to + 1].strip('"')
                    
                    for col in table_obj.columns:
                        if col.name == old_col:
                            col.name = new_col
                            break
                        
                except Exception:
                    pass
                
            continue

        # RENAME TABLE
        if "RENAME" in upper_sql and "TO" in upper_sql and "COLUMN" not in upper_sql:
            parts = action_sql.split()
            
            if "TO" in parts:
                try:
                    idx_to = parts.index("TO")
                    new_table = parts[idx_to + 1].strip('"')
                    new_fqn = f"{schema_name}.{new_table}"
                    table_obj.name = new_table
                    temp_tables[new_fqn] = table_obj
                    
                    if fqn in temp_tables:
                        del temp_tables[fqn]
                        
                    fqn = new_fqn
                    
                except Exception:
                    pass
                
            continue
