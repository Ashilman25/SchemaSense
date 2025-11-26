# define the data classes or Pydantic models with fields 
# but no logic; add stub methods (from_introspection, to_dict_for_api, apply_change) 
# that just raise NotImplementedError/pass.


from typing import Dict, List
from pydantic import BaseModel, Field


class Column(BaseModel):
    name: str
    type: str
    is_pk: bool = False
    is_fk: bool = False
    nullable: bool = True


class Table(BaseModel):
    name: str
    schema: str = "public"
    columns: List[Column] = Field(default_factory=list)


class Relationship(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class CanonicalSchemaModel(BaseModel):
    tables: Dict[str, Table] = Field(default_factory=dict)
    relationships: List[Relationship] = Field(default_factory=list)

    @classmethod
    def from_introspection(cls, *_args, **_kwargs) -> "CanonicalSchemaModel":
        #build model from query results
        raise NotImplementedError("Schema introspection not implemented yet.")

    #turn model -> json dict or other for api
    def to_dict_for_api(self) -> dict:
        raise NotImplementedError("Schema serialization not implemented yet.")

    #change the model according to schema edits
    def apply_change(self, *_args, **_kwargs) -> None:
        raise NotImplementedError("Schema mutation not implemented yet.")
