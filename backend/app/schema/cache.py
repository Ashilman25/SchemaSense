from typing import Optional
from app.models.schema_model import CanonicalSchemaModel
from app.schema.introspect import introspect_tables_and_columns, introspect_primary_keys, introspect_foreign_keys


_schema_cache: Optional[CanonicalSchemaModel] = None


def get_cached_schema() -> Optional[CanonicalSchemaModel]:
    return _schema_cache


def set_cached_schema(schema: CanonicalSchemaModel) -> None:
    global _schema_cache
    _schema_cache = schema


def clear_schema_cache() -> None:
    global _schema_cache
    _schema_cache = None


def refresh_schema(conn) -> CanonicalSchemaModel:
    clear_schema_cache()

    tables_raw = introspect_tables_and_columns(conn)
    pks_raw = introspect_primary_keys(conn)
    fks_raw = introspect_foreign_keys(conn)

    schema_model = CanonicalSchemaModel.from_introspection(tables_raw, pks_raw, fks_raw)

    set_cached_schema(schema_model)
    return schema_model


def get_or_refresh_schema(conn) -> CanonicalSchemaModel:
    cached = get_cached_schema()
    if cached is not None:
        return cached

    return refresh_schema(conn)
