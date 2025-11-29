from app.models.schema_model import CanonicalSchemaModel
from app.nl_to_sql.openai_client import call_openai


def build_prompt(question: str, schema_model: CanonicalSchemaModel) -> str:
    schema_summary = _build_schema_summary(schema_model)

    prompt = f"""You are a PostgreSQL SQL query generator. Given a database schema and a natural language question, generate a valid PostgreSQL SQL query.

DATABASE SCHEMA:
{schema_summary}

STRICT RULES:
1. Only generate valid PostgreSQL SQL syntax
2. Only generate read-only SELECT queries
3. NEVER generate destructive commands: DROP, DELETE, UPDATE, TRUNCATE, ALTER, INSERT, CREATE
4. Prefer simple, clear queries that match the requested output
5. Use proper table and column names as shown in the schema
6. Include appropriate JOINs when querying multiple tables
7. Return ONLY the SQL query without explanation or markdown formatting

FEW-SHOT EXAMPLES:

Question: "Show me all customers"
SQL: SELECT * FROM customers;

Question: "What are the names and emails of all users?"
SQL: SELECT name, email FROM users;

Question: "List all orders with customer names"
SQL: SELECT orders.id, orders.order_date, customers.name
FROM orders
JOIN customers ON orders.customer_id = customers.id;

Question: "Count how many products we have"
SQL: SELECT COUNT(*) FROM products;

NOW GENERATE SQL FOR THIS QUESTION:
Question: "{question}"
SQL:"""

    return prompt


def _build_schema_summary(schema_model: CanonicalSchemaModel) -> str:
    summary_parts = []

    # Add table and column information
    for fully_qualified_name, table in schema_model.tables.items():
        table_info = f"\nTable: {fully_qualified_name}"
        summary_parts.append(table_info)

        # Add columns
        for col in table.columns:
            col_attrs = []
            
            if col.is_pk:
                col_attrs.append("PRIMARY KEY")
                
            if col.is_fk:
                col_attrs.append("FOREIGN KEY")
                
            if not col.nullable:
                col_attrs.append("NOT NULL")

            attrs_str = f" ({', '.join(col_attrs)})" if col_attrs else ""
            col_line = f"  - {col.name}: {col.type}{attrs_str}"
            summary_parts.append(col_line)

    # Add relationship information
    if schema_model.relationships:
        summary_parts.append("\nRELATIONSHIPS:")
        
        for rel in schema_model.relationships:
            rel_line = f"  - {rel.from_table}.{rel.from_column} -> {rel.to_table}.{rel.to_column}"
            summary_parts.append(rel_line)

    return "\n".join(summary_parts)


def generate_sql_from_nl(question: str, schema_model: CanonicalSchemaModel) -> str:
    prompt = build_prompt(question, schema_model)
    sql = call_openai(prompt)
    return sql
