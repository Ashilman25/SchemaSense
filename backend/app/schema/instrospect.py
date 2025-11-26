import psycopg2



def introspect_tables_and_columns(conn):
    tables = {}

    try:
        curr = conn.cursor()

        curr.execute("""
                     SELECT table_schema, table_name, column_name, data_type, is_nullable
                     FROM information_schema.columns
                     WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                     ORDER BY table_schema, table_name, ordinal_position
                     """)
        columns_info = curr.fetchall()

        for table_schema, table_name, column_name, data_type, is_nullable in columns_info:
            key = (table_schema, table_name)

            if key not in tables:
                tables[key] = {
                    "schema": table_schema,
                    "table": table_name,
                    "columns": []
                }

            tables[key]["columns"].append({
                "name": column_name,
                "type": data_type,
                "nullable": is_nullable
            })

        return tables

    except Exception as e:
        raise Exception(f"Error introspecting tables and columns: {str(e)}") from e

    finally:
        try:
            curr.close()
        except Exception:
            pass

    
    
    
    
#return
# {
#   ("schema_name", "table_name"): ["pk_column_1", "pk_column_2", ...],
#   ...
# }
# Key = tuple identifying the table.
# Value = list of PK column names for that table.
# Usually the list has 1 item, but it may have multiple.
    
def introspect_primary_keys(conn):
    pks = {}
    
    try:
        curr = conn.cursor()

        # Use pg_catalog.pg_constraint joined with pg_class and pg_attribute to find PKs
        curr.execute("""
                     SELECT n.nspname AS table_schema,c.relname AS table_name, a.attname AS column_name
                     FROM pg_catalog.pg_constraint con
                     JOIN pg_catalog.pg_class c 
                     ON con.conrelid = c.oid
                     JOIN pg_catalog.pg_namespace n 
                     ON c.relnamespace = n.oid
                     JOIN pg_catalog.pg_attribute a 
                     ON a.attrelid = c.oid AND a.attnum = ANY(con.conkey)
                     WHERE con.contype = 'p' AND n.nspname NOT IN ('pg_catalog', 'information_schema')
                     ORDER BY n.nspname, c.relname, array_position(con.conkey, a.attnum)
                     """)
        pk_info = curr.fetchall()
        
        for each in pk_info:
            table_schema, table_name, col_name = each
            
            key = (table_schema, table_name)
            if key not in pks:
                pks[key] = []
                
            pks[key].append(col_name)
            
        return pks

    
    except Exception as e:
        raise Exception(f"Error introspecting primary keys: {str(e)}") from e
    
    finally:
        try:
            curr.close()
        except Exception:
            pass





def introspect_foreign_keys(conn):
    pass
#to get:

# source table (the table that has the FK)
# source column
# target table (the referenced table)
# target column
# [
#   {
#     "from_table": ("src_schema", "src_table"),
#     "from_column": "column_name",
#     "to_table": ("tgt_schema", "tgt_table"),
#     "to_column": "target_column",
#   },
#   ...
# ]