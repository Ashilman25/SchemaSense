from typing import List, Tuple, Set
import sqlglot
from sqlglot import exp
from app.models.schema_model import CanonicalSchemaModel


#change later idk if i want all these not allowed
#create, insert should be good but will confirm later
DISALLOWED_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "TRUNCATE",
    "ALTER",
    "INSERT", 
    "CREATE", 
    "GRANT",
    "REVOKE",
    "EXECUTE",
    "CALL",
}


class SQLValidationError(Exception):
    pass


def validate_and_normalize_sql(sql: str, schema_model: CanonicalSchemaModel) -> Tuple[str, List[str]]:
    warnings = []
    try:
        parsed = sqlglot.parse_one(sql, dialect = "postgres")
        
    except sqlglot.errors.ParseError as e:
        raise SQLValidationError(f"SQL parsing failed: {str(e)}")


    _check_disallowed_operations(parsed)
    schema_warnings = _validate_schema_references(parsed, schema_model)
    warnings.extend(schema_warnings)
    
    try:
        normalized_sql = sqlglot.transpile(sql, read="postgres", write="postgres")[0]
        
    except Exception as e:
        raise SQLValidationError(f"SQL normalization failed: {str(e)}")

    return normalized_sql, warnings







def _check_disallowed_operations(parsed: exp.Expression) -> None:

    node_type = type(parsed).__name__.upper()


    if not isinstance(parsed, exp.Select):
        if not isinstance(parsed, (exp.Union, exp.With, exp.Subquery)):
            raise SQLValidationError(
                f"Only SELECT queries are allowed. Found: {node_type}"
            )


    for node in parsed.walk():
        node_type = type(node).__name__.upper()

        if node_type in DISALLOWED_KEYWORDS:
            raise SQLValidationError(
                f"Disallowed operation: {node_type}. Only read-only SELECT queries are permitted."
            )

        if isinstance(node, (exp.Drop, exp.Delete, exp.Update, exp.Insert, exp.Create)):
            raise SQLValidationError(
                f"Disallowed operation: {type(node).__name__}. Only read-only SELECT queries are permitted."
            )





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
    for table_node in parsed.find_all(exp.Table):
        table_name = table_node.name.lower()
        
        if table_node.db:
            full_name = f"{table_node.db.lower()}.{table_name}"
            referenced_tables.add(full_name)
            
        else:
            referenced_tables.add(table_name)


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
