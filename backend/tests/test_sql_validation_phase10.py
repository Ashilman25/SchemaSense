import pytest

from app.nl_to_sql.validator import validate_and_normalize_sql, SQLValidationError
from app.models.schema_model import CanonicalSchemaModel, Column


def _sample_schema():
    model = CanonicalSchemaModel()
    model.add_table(
        "users",
        schema="public",
        columns=[
            Column(name="id", type="integer", is_pk=True, nullable=False),
            Column(name="email", type="text", nullable=False),
        ],
    )
    return model


def test_select_is_allowed_and_validated():
    model = _sample_schema()
    normalized, warnings = validate_and_normalize_sql("select email from public.users", model)
    assert "SELECT" in normalized.upper()
    assert warnings == []


def test_insert_is_allowed_and_validated():
    model = _sample_schema()
    normalized, warnings = validate_and_normalize_sql(
        "INSERT INTO public.users (id, email) VALUES (1, 'a@b.com')",
        model,
    )
    assert normalized.upper().startswith("INSERT")
    assert warnings == []


def test_create_table_is_allowed():
    model = _sample_schema()
    normalized, warnings = validate_and_normalize_sql(
        "CREATE TABLE public.new_table (id serial PRIMARY KEY)",
        model,
    )
    assert normalized.upper().startswith("CREATE TABLE")
    assert warnings == []


def test_create_schema_is_allowed():
    model = _sample_schema()
    normalized, warnings = validate_and_normalize_sql(
        "CREATE SCHEMA analytics",
        model,
    )
    assert normalized.upper().startswith("CREATE SCHEMA")
    assert warnings == []


def test_alter_table_add_column_is_allowed():
    model = _sample_schema()
    normalized, warnings = validate_and_normalize_sql(
        "ALTER TABLE public.users ADD COLUMN age integer",
        model,
    )
    assert "ADD COLUMN" in normalized.upper()
    assert warnings == []


def test_alter_table_rename_is_allowed():
    model = _sample_schema()
    normalized, warnings = validate_and_normalize_sql(
        "ALTER TABLE public.users RENAME TO public.users_new",
        model,
    )
    assert "RENAME" in normalized.upper()
    assert warnings == []


def test_drop_table_is_blocked():
    model = _sample_schema()
    with pytest.raises(SQLValidationError):
        validate_and_normalize_sql("DROP TABLE public.users", model)


def test_truncate_is_blocked():
    model = _sample_schema()
    with pytest.raises(SQLValidationError):
        validate_and_normalize_sql("TRUNCATE public.users", model)


def test_update_is_blocked():
    model = _sample_schema()
    with pytest.raises(SQLValidationError):
        validate_and_normalize_sql("UPDATE public.users SET email = 'x'", model)


def test_alter_table_drop_column_is_blocked():
    model = _sample_schema()
    with pytest.raises(SQLValidationError):
        validate_and_normalize_sql("ALTER TABLE public.users DROP COLUMN email", model)


def test_multiple_statements_are_blocked():
    model = _sample_schema()
    with pytest.raises(SQLValidationError):
        validate_and_normalize_sql(
            "INSERT INTO public.users (id, email) VALUES (1, 'a'); INSERT INTO public.users (id, email) VALUES (2, 'b')",
            model,
        )
