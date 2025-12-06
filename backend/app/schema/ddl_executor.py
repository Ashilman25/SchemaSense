from typing import List, Tuple, Optional, Dict, Any
import logging
from psycopg2.extensions import connection as PgConnection
from app.models.schema_model import CanonicalSchemaModel

logger = logging.getLogger(__name__)

class DDLExecutionError(Exception):
    pass



def generate_ddl_from_action(action_type: str, params: Dict[str, Any], schema_model: CanonicalSchemaModel) -> str:
    if action_type == "add_table":
        return _generate_create_table(params)

    elif action_type == "rename_table":
        return _generate_rename_table(params)

    elif action_type == "drop_table":
        return _generate_drop_table(params)

    elif action_type == "add_column":
        return _generate_add_column(params)

    elif action_type == "rename_column":
        return _generate_rename_column(params)

    elif action_type == "drop_column":
        return _generate_drop_column(params)

    elif action_type == "add_relationship":
        return _generate_add_foreign_key(params)

    elif action_type == "remove_relationship":
        return _generate_drop_foreign_key(params)

    else:
        raise ValueError(f"Unknown action type: {action_type}")