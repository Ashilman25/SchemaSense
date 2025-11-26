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
def introspect_foreign_keys(conn):
    fks = []

    try:
        curr = conn.cursor()

        curr.execute("""
                     SELECT src_ns.nspname AS from_schema, src_class.relname AS from_table, src_attr.attname AS from_column, tgt_ns.nspname AS to_schema, tgt_class.relname AS to_table, tgt_attr.attname AS to_column
                     FROM pg_catalog.pg_constraint con
                     -- Source table (table that has the FK)
                     JOIN pg_catalog.pg_class src_class 
                     ON con.conrelid = src_class.oid
                     JOIN pg_catalog.pg_namespace src_ns 
                     ON src_class.relnamespace = src_ns.oid
                     -- Target table (table being referenced)
                     JOIN pg_catalog.pg_class tgt_class 
                     ON con.confrelid = tgt_class.oid
                     JOIN pg_catalog.pg_namespace tgt_ns 
                     ON tgt_class.relnamespace = tgt_ns.oid
                     -- Source columns (unnest the conkey array to get each column)
                     JOIN pg_catalog.pg_attribute src_attr
                         ON src_attr.attrelid = con.conrelid
                         AND src_attr.attnum = ANY(con.conkey)
                     -- Target columns (unnest the confkey array to get each referenced column)
                     JOIN pg_catalog.pg_attribute tgt_attr
                         ON tgt_attr.attrelid = con.confrelid
                         AND tgt_attr.attnum = con.confkey[array_position(con.conkey, src_attr.attnum)]
                     WHERE con.contype = 'f'
                         AND src_ns.nspname NOT IN ('pg_catalog', 'information_schema')
                     ORDER BY src_ns.nspname, src_class.relname, array_position(con.conkey, src_attr.attnum)
                     """)
        fk_info = curr.fetchall()


        for each in fk_info:
            from_schema, from_table, from_column, to_schema, to_table, to_column = each
            fks.append({
                "from_table": (from_schema, from_table),
                "from_column": from_column,
                "to_table": (to_schema, to_table),
                "to_column": to_column
            })

        return fks

    except Exception as e:
        raise Exception(f"Error introspecting foreign keys: {str(e)}") from e

    finally:
        try:
            curr.close()
        except Exception:
            pass
