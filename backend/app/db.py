from typing import Optional
from urllib.parse import quote_plus
from pydantic import BaseModel
import psycopg2


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    dbname: str = "schemasense"
    user: str = "schemasense"
    password: str = "schemasense_dev"


_session_configs: dict[str, DatabaseConfig] = {}


#save current request db config for this session
def set_database_config(config: DatabaseConfig, session_id: str) -> None:
    if config is None:
        _session_configs.pop(session_id, None)
    else:
        _session_configs[session_id] = config


#get db config for this session
def get_database_config(session_id: str) -> Optional[DatabaseConfig]:
    return _session_configs.get(session_id)


#build postgres dsn
def build_dsn(config: DatabaseConfig) -> str:
    encoded_user = quote_plus(config.user)
    encoded_password = quote_plus(config.password)
    return f"postgresql://{encoded_user}:{encoded_password}@{config.host}:{config.port}/{config.dbname}"


#open and return a real db connection
def get_connection(session_id: str):
    config = get_database_config(session_id)
    if config is None:
        raise RuntimeError("db config not set for this session")

    dsn = build_dsn(config)

    try:
        conn = psycopg2.connect(dsn)
        return conn

    except psycopg2.OperationalError as e:
        raise RuntimeError(f"Failed to connect to database: {config.host}:{config.port}/{config.dbname}") from e

    except Exception as e:
        raise RuntimeError(f"Unexpected error connecting to database") from e
