from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
import sqlglot
from sqlglot import exp


VALID_POSTGRES_TYPES = {
    'smallint', 'integer', 'int', 'bigint', 'decimal', 'numeric', 'real', 'double precision',
    'smallserial', 'serial', 'bigserial', 'int2', 'int4', 'int8', 'float4', 'float8',
    'money',
    'character varying', 'varchar', 'character', 'char', 'text',
    'bytea',
    'timestamp', 'timestamp without time zone', 'timestamp with time zone',
    'date', 'time', 'time without time zone', 'time with time zone', 'interval',
    'boolean', 'bool',
    'enum',
    'point', 'line', 'lseg', 'box', 'path', 'polygon', 'circle',
    'cidr', 'inet', 'macaddr', 'macaddr8',
    'bit', 'bit varying',
    'tsvector', 'tsquery',
    'uuid',
    'xml',
    'json', 'jsonb',
    'array',
    'int4range', 'int8range', 'numrange', 'tsrange', 'tstzrange', 'daterange',
    'oid', 'regproc', 'regprocedure', 'regoper', 'regoperator', 'regclass',
    'regtype', 'regrole', 'regnamespace', 'regconfig', 'regdictionary'
}


class SchemaValidationError(Exception):
    pass


class Column(BaseModel):
    name: str
    type: str
    is_pk: bool = False
    is_fk: bool = False
    nullable: bool = True


class Table(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    schema: str = "public"
    columns: List[Column] = Field(default_factory=list)
    row_count: int | None = None 


class Relationship(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class CanonicalSchemaModel(BaseModel):
    tables: Dict[str, Table] = Field(default_factory=dict)
    relationships: List[Relationship] = Field(default_factory=list)

    @classmethod
    def from_introspection(cls, tables_raw: dict, pks_raw: dict, fks_raw: list, row_counts_raw: dict = None) -> "CanonicalSchemaModel":
        tables_dict = {}
        relationships_list = []

        #fk lookup
        fk_columns = set()
        for fk in fks_raw:
            from_schema, from_table = fk["from_table"]
            fk_columns.add((from_schema, from_table, fk["from_column"]))


        for table_key, table_data in tables_raw.items():
            schema_name, table_name = table_key

            pk_columns = set(pks_raw.get(table_key, []))

            columns = []
            for col_data in table_data["columns"]:
                col_name = col_data["name"]

                #check pk or fk
                is_pk = col_name in pk_columns
                is_fk = (schema_name, table_name, col_name) in fk_columns

                #nullable -> bool
                nullable = col_data["nullable"] == "YES"

                columns.append(Column(
                    name = col_name,
                    type = col_data["type"],
                    is_pk = is_pk,
                    is_fk = is_fk,
                    nullable = nullable
                ))

            # Get row count if available
            row_count = None
            if row_counts_raw:
                row_count = row_counts_raw.get(table_key)

            table = Table(name = table_name, schema = schema_name, columns = columns, row_count = row_count)

            fully_qualified_name = f"{schema_name}.{table_name}"
            tables_dict[fully_qualified_name] = table

        #relations
        for fk in fks_raw:
            from_schema, from_table = fk["from_table"]
            to_schema, to_table = fk["to_table"]

            relationships_list.append(Relationship(
                from_table = f"{from_schema}.{from_table}",
                from_column = fk["from_column"],
                to_table = f"{to_schema}.{to_table}",
                to_column = fk["to_column"]
            ))

        return cls(tables = tables_dict, relationships = relationships_list)

    @classmethod
    def from_ddl(cls, ddl_text: str) -> "CanonicalSchemaModel":
        tables_dict = {}
        relationships_list = []

        try:
            statements = sqlglot.parse(ddl_text, read = "postgres")

        except Exception as e:
            raise SchemaValidationError(f"Failed to parse DDL: {str(e)}")

        if not statements:
            return cls(tables={}, relationships=[])

        for statement in statements:
            if isinstance(statement, exp.Create) and statement.kind == "TABLE":
                cls._process_create_table(statement, tables_dict)

        for statement in statements:
            if isinstance(statement, exp.Alter):
                cls._process_alter_table(statement, tables_dict, relationships_list)

        return cls(tables = tables_dict, relationships = relationships_list)

    @classmethod
    def _process_create_table(cls, statement: exp.Create, tables_dict: Dict[str, Table]) -> None:
        table_expr = statement.this

        if isinstance(table_expr, exp.Schema):
            table_name_expr = table_expr.this
        else:
            table_name_expr = table_expr

        # Get table name
        if isinstance(table_name_expr, exp.Table):
            table_name = table_name_expr.name
            schema_name = table_name_expr.db or "public"
            
        else:
            table_name = str(table_name_expr)
            schema_name = "public"

        columns = []
        pk_columns = []


        if isinstance(table_expr, exp.Schema):
            for expr in table_expr.expressions:
                if isinstance(expr, exp.ColumnDef):
                    col_name = expr.this.name
                    col_type = cls._extract_column_type(expr)
                    nullable = cls._extract_nullable(expr)

                    is_pk = cls._is_primary_key_inline(expr)
                    if is_pk:
                        pk_columns.append(col_name)

                    columns.append(Column(
                        name = col_name,
                        type = col_type,
                        is_pk = is_pk,
                        is_fk = False, 
                        nullable = nullable
                    ))

                elif isinstance(expr, exp.PrimaryKey):
                    for col_expr in expr.expressions:
                        col_name = col_expr.name if hasattr(col_expr, 'name') else str(col_expr)
                        pk_columns.append(col_name)

                elif isinstance(expr, exp.Constraint):
                    for constraint_expr in expr.expressions:
                        if isinstance(constraint_expr, exp.PrimaryKey):
                            for col_expr in constraint_expr.expressions:
                                if hasattr(col_expr, 'this'):
                                    col_obj = col_expr.this if isinstance(col_expr.this, exp.Column) else col_expr
                                    
                                    if hasattr(col_obj, 'this') and hasattr(col_obj.this, 'name'):
                                        col_name = col_obj.this.name
                                    else:
                                        col_name = str(col_obj)
                                        
                                elif hasattr(col_expr, 'name'):
                                    col_name = col_expr.name
                                else:
                                    col_name = str(col_expr)
                                    
                                pk_columns.append(col_name)

        for col in columns:
            if col.name in pk_columns:
                col.is_pk = True

        fully_qualified_name = f"{schema_name}.{table_name}"
        table = Table(name = table_name, schema = schema_name, columns = columns, row_count = None)

        tables_dict[fully_qualified_name] = table



    #turn model -> json dict or other for api
    def to_dict_for_api(self) -> dict:
        api_data = {
            "tables" : [
                {
                    "schema" : t.schema,
                    "name" : t.name,
                    "columns" : [c.model_dump() for c in t.columns],
                    "row_count" : t.row_count,
                }
                for t in self.tables.values()
            ],
            "relationships" : [r.model_dump() for r in self.relationships],
        }

        return api_data
    
    
    def to_ddl(self) -> str:
        ddl_statements = []
        
        sorted_tables = sorted(self.tables.items(), key = lambda x: x[0])
        
        for _, table in sorted_tables:
            ddl_statements.append(self._generate_create_table_statement(table))
            
        fk_statements = self._generate_foreign_key_statements()
        if fk_statements:
            ddl_statements.extend(fk_statements)
            
        
        return "\n\n".join(ddl_statements)
    
    
    def _generate_create_table_statement(self, table: Table) -> str:
        lines = []
        
        fully_qualified = f"{table.schema}.{table.name}"
        lines.append(f"CREATE TABLE {fully_qualified} (")
        
        column_lines = []
        pk_columns = []
        
        for col in table.columns:
            col_parts = [f"    {col.name}", col.type]
            
            if not col.nullable:
                col_parts.append("NOT NULL")
                
            column_lines.append(" ".join(col_parts))
            
            if col.is_pk:
                pk_columns.append(col.name)
                
        if pk_columns:
            pk_constraint_name = f"{table.name}_pkey"
            pk_columns_str = ", ".join(pk_columns)
            column_lines.append(f"    CONSTRAINT {pk_constraint_name} PRIMARY KEY ({pk_columns_str})")
            
        lines.append(",\n".join(column_lines))
        lines.append(");")
        return "\n".join(lines)
    
    def _generate_foreign_key_statements(self) -> List[str]:
        fk_statements = []
        relationships_by_table = {}
        
        for rel in self.relationships:
            if rel.from_table not in relationships_by_table:
                relationships_by_table[rel.from_table] = []
                
            relationships_by_table[rel.from_table].append(rel)


        for from_table in sorted(relationships_by_table.keys()):
            for rel in relationships_by_table[from_table]:
                fk_statements.append(self._generate_single_fk_statement(rel))

        return fk_statements
    
    def _generate_single_fk_statement(self, rel: Relationship) -> str:
        from_table_name = rel.from_table.split(".")[-1]
        constraint_name = f"{from_table_name}_{rel.from_column}_fkey"

        statement = (
            f"ALTER TABLE {rel.from_table}\n"
            f"    ADD CONSTRAINT {constraint_name}\n"
            f"    FOREIGN KEY ({rel.from_column})\n"
            f"    REFERENCES {rel.to_table} ({rel.to_column});"
        )

        return statement


    #change the model according to schema edits
    def apply_change(self, *_args, **_kwargs) -> None:
        raise NotImplementedError("Schema mutation not implemented yet.")




    #VALIDATING THE INPUT
    #helper funcs
    
    def _validate_column_type(self, col_type: str) -> None:
        normalized_type = col_type.lower().strip()
        
        #array types like integer[]
        if normalized_type.endswith('[]'):
            base_type = normalized_type[:-2].strip()
            
            if base_type not in VALID_POSTGRES_TYPES:
                raise SchemaValidationError(f"Invalid PostgreSQL type: '{col_type}'. Base type '{base_type}' is not recognized.")
        
            return
        
        #with params like varchar(255)
        if '(' in normalized_type:
            base_type = normalized_type.split('(')[0].strip()
            
            if base_type not in VALID_POSTGRES_TYPES:
                raise SchemaValidationError(f"Invalid PostgreSQL type: '{col_type}'. Base type '{base_type}' is not recognized.")
            
            return
        
        #if type in valid
        if normalized_type not in VALID_POSTGRES_TYPES:
            raise SchemaValidationError(f"Invalid PostgreSQL type: '{col_type}'. Must be a valid PostgreSQL data type.")
        
        
    
    def _get_table_by_name(self, table_name: str, schema_name: str = "public") -> Optional[Table]:
        fully_qualified = f"{schema_name}.{table_name}"
        return self.tables.get(fully_qualified)
    
    def _get_column_by_name(self, table: Table, column_name: str) -> Optional[Column]:
        for col in table.columns:
            if col.name == column_name:
                return col
            
        return None
    
    def _is_column_referenced_by_fk(self, table_name: str, column_name: str) -> List[Relationship]:
        referenced_by = []
        
        for rel in self.relationships:
            if rel.to_table == table_name and rel.to_column == column_name:
                referenced_by.append(rel)
                
        return referenced_by
    
    
    def _get_outgoing_fks(self, table_name: str, column_name: Optional[str] = None) -> List[Relationship]:
        outgoing = []
        
        for rel in self.relationships:
            if rel.from_table == table_name:
                if column_name is None or rel.from_column == column_name:
                    outgoing.append(rel)
                    
        return outgoing
    
    
    
    
    #TABLE MUTATION METHODS
    
    def add_table(self, name: str, schema: str = "public", columns: Optional[List[Column]] = None) -> None:
        fully_qualified_name = f"{schema}.{name}"
        
        #check dupes
        if fully_qualified_name in self.tables:
            raise SchemaValidationError(f"Table '{fully_qualified_name}' already exists in schema '{schema}'.")
        
        if columns:
            for col in columns:
                self._validate_column_type(col.type)
                
        new_table = Table(name = name, schema = schema, columns = columns or [], row_count = None)
        self.tables[fully_qualified_name] = new_table
        
        
        
    def rename_table(self, old_name: str, new_name: str, schema: str = "public") -> None:
        old_fully_qualified = f"{schema}.{old_name}"
        new_fully_qualified = f"{schema}.{new_name}"
        
        if old_fully_qualified not in self.tables:
            raise SchemaValidationError(f"Table '{old_fully_qualified}' does not exist.")
        
        if new_fully_qualified in self.tables:
            raise SchemaValidationError(f"Table '{new_fully_qualified}' already exists. Cannot rename.")
        
        table = self.tables[old_fully_qualified]
        table.name = new_name
        
        self.tables[new_fully_qualified] = table
        del self.tables[old_fully_qualified]
        
        for rel in self.relationships:
            if rel.from_table == old_fully_qualified:
                rel.from_table = new_fully_qualified
                
            if rel.to_table == old_fully_qualified:
                rel.to_table = new_fully_qualified
                
                
                
    def drop_table(self, name: str, schema: str = "public", force: bool = False) -> None:
        fully_qualified_name = f"{schema}.{name}"
        
        if fully_qualified_name not in self.tables:
            raise SchemaValidationError(f"Table '{fully_qualified_name}' does not exist.")        
        
        referenced_by = []
        for rel in self.relationships:
            if rel.to_table == fully_qualified_name:
                referenced_by.append(rel)
                
        if referenced_by and not force:
            fk_details = [f"{r.from_table}.{r.from_column}" for r in referenced_by]
            raise SchemaValidationError(
                f"Cannot drop table '{fully_qualified_name}'. "
                f"It is referenced by foreign keys: {', '.join(fk_details)}. "
                f"Use force=True to drop anyway."
            )
            
        #remove table and all relations
        del self.tables[fully_qualified_name]
        
        self.relationships = [
            rel for rel in self.relationships
            if rel.from_table != fully_qualified_name and rel.to_table != fully_qualified_name
        ]
        
        
        
    
    #COLUMN MUTATIONS
    
    def add_column(self, table_name: str, column: Column, schema: str = "public") -> None:
        fully_qualified_name = f"{schema}.{table_name}"
        
        if fully_qualified_name not in self.tables:
            raise SchemaValidationError(f"Table '{fully_qualified_name}' does not exist.")
        
        table = self.tables[fully_qualified_name]
        
        if self._get_column_by_name(table, column.name):
            raise SchemaValidationError(f"Column '{column.name}' already exists in table '{fully_qualified_name}'.")
        
        self._validate_column_type(column.type)
        table.columns.append(column)
        
        
        
    def rename_column(self, table_name: str, old_col: str, new_col: str, schema: str = "public") -> None:
        fully_qualified_name = f"{schema}.{table_name}"
        
        if fully_qualified_name not in self.tables:
            raise SchemaValidationError(f"Table '{fully_qualified_name}' does not exist.")
        
        table = self.tables[fully_qualified_name]
        
        old_column = self._get_column_by_name(table, old_col)
        if not old_column:
            raise SchemaValidationError(f"Column '{old_col}' does not exist in table '{fully_qualified_name}'.")
        
        if self._get_column_by_name(table, new_col):
            raise SchemaValidationError(f"Column '{new_col}' already exists in table '{fully_qualified_name}'.")
        
        old_column.name = new_col
        
        for rel in self.relationships:
            if rel.from_table == fully_qualified_name and rel.from_column == old_col:
                rel.from_column = new_col
                
            if rel.to_table == fully_qualified_name and rel.to_column == old_col:
                rel.to_column = new_col
                
                
                
    def drop_column(self, table_name: str, column_name: str, schema: str = "public", force: bool = False) -> None:
        fully_qualified_name = f"{schema}.{table_name}"
        
        if fully_qualified_name not in self.tables:
            raise SchemaValidationError(f"Table '{fully_qualified_name}' does not exist.")
        
        table = self.tables[fully_qualified_name]
        
        column = self._get_column_by_name(table, column_name)
        if not column:
            raise SchemaValidationError(f"Column '{column_name}' does not exist in table '{fully_qualified_name}'.")
        
        #check if col referenced by FKs
        referenced_by = self._is_column_referenced_by_fk(fully_qualified_name, column_name)
        if referenced_by and not force:
            fk_details = [f"{r.from_table}.{r.from_column}" for r in referenced_by]
            
            raise SchemaValidationError(
                f"Cannot drop column '{fully_qualified_name}.{column_name}'. "
                f"It is referenced by foreign keys: {', '.join(fk_details)}. "
                f"Use force=True to drop anyway."
            )
    
        #check if col is referencing other FKs
        outgoing_fks = self._get_outgoing_fks(fully_qualified_name, column_name)
        if outgoing_fks and not force:
            fk_details = [f"{r.to_table}.{r.to_column}" for r in outgoing_fks]
            
            raise SchemaValidationError(
                f"Cannot drop column '{fully_qualified_name}.{column_name}'. "
                f"It has foreign key constraints to: {', '.join(fk_details)}. "
                f"Use force=True to drop anyway."
            )
        
        #remove col and relations    
        table.columns = [col for col in table.columns if col.name != column_name]
        
        self.relationships = [
            rel for rel in self.relationships
            if not (
                (rel.from_table == fully_qualified_name and rel.from_column == column_name) or
                (rel.to_table == fully_qualified_name and rel.to_column == column_name)
            )
        ]
        
        
        
        
    #RELATIONSHIP MUTATIONS
    
    def add_relationship(self, from_table: str, from_column: str, to_table: str, to_column: str, from_schema: str = "public", to_schema: str = "public") -> None:
        from_fqn = f"{from_schema}.{from_table}"
        to_fqn = f"{to_schema}.{to_table}"
        
        #check start table exists
        if from_fqn not in self.tables:
            raise SchemaValidationError(f"Source table '{from_fqn}' does not exist.")
        
        #check end tables exist
        if to_fqn not in self.tables:
            raise SchemaValidationError(f"Target table '{to_fqn}' does not exist.")
        
        from_table_obj = self.tables[from_fqn]
        to_table_obj = self.tables[to_fqn]
        
        from_col = self._get_column_by_name(from_table_obj, from_column)
        if not from_col:
            raise SchemaValidationError(f"Source column '{from_column}' does not exist in table '{from_fqn}'.")
        
        to_col = self._get_column_by_name(to_table_obj, to_column)
        if not to_col:
            raise SchemaValidationError(f"Target column '{to_column}' does not exist in table '{to_fqn}'.")
        
        
        if not to_col.is_pk:
            raise SchemaValidationError(
                f"Target column '{to_fqn}.{to_column}' must be a primary key or unique column. "
                f"Foreign keys must reference a PK or unique constraint."
            )
            
        
        for rel in self.relationships:
            if (rel.from_table == from_fqn and rel.from_column == from_column and rel.to_table == to_fqn and rel.to_column == to_column):
                raise SchemaValidationError(f"Relationship from '{from_fqn}.{from_column}' to '{to_fqn}.{to_column}' already exists.")
            
        
        #mark source col as FK and add relationship
        from_col.is_fk = True
        
        new_relationship = Relationship(from_table = from_fqn, from_column = from_column, to_table = to_fqn, to_column = to_column)
        self.relationships.append(new_relationship)
        
        
    def remove_relationship(self, from_table: str, from_column: str, to_table: str, to_column: str, from_schema: str = "public", to_schema: str = "public") -> None:
        from_fqn = f"{from_schema}.{from_table}"
        to_fqn = f"{to_schema}.{to_table}"
        
        
        #find relationship
        relationship_found = False
        for i, rel in enumerate(self.relationships):
            if (rel.from_table == from_fqn and rel.from_column == from_column and rel.to_table == to_fqn and rel.to_column == to_column):
                relationship_found = True
                del self.relationships[i]
                break
            
        if not relationship_found:
            raise SchemaValidationError(f"Relationship from '{from_fqn}.{from_column}' to '{to_fqn}.{to_column}' does not exist.")
        
        
        #check if source col as outgoing FKs, if not unmark from fk
        if from_fqn in self.tables:
            from_table_obj = self.tables[from_fqn]
            from_col = self._get_column_by_name(from_table_obj, from_column)

            if from_col:
                still_fk = False
                
                for rel in self.relationships:
                    if rel.from_table == from_fqn and rel.from_column == from_column:
                        still_fk = True
                        break

                if not still_fk:
                    from_col.is_fk = False
        


    