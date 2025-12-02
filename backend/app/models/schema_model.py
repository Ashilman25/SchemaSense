from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


VALID_POSTGRES_TYPES = {
    'smallint', 'integer', 'bigint', 'decimal', 'numeric', 'real', 'double precision',
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
        

    #change the model according to schema edits
    def apply_change(self, *_args, **_kwargs) -> None:
        raise NotImplementedError("Schema mutation not implemented yet.")

