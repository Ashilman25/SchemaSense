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


_active_config: Optional[DatabaseConfig] = None


#save current request db config for later
def set_database_config(config: DatabaseConfig) -> None:
    global _active_config
    _active_config = config


#get db config
def get_database_config() -> Optional[DatabaseConfig]:
    return _active_config


#build postgres dsn
def build_dsn(config: DatabaseConfig) -> str:
    encoded_user = quote_plus(config.user)
    encoded_password = quote_plus(config.password)
    return f"postgresql://{encoded_user}:{encoded_password}@{config.host}:{config.port}/{config.dbname}"


#open and return a real db connection
def get_connection():
    config = get_database_config()
    if config is None:
        raise RuntimeError("db config not set")

    dsn = build_dsn(config)
    
    try:
        conn = psycopg2.connect(dsn)
        return conn
    
    except psycopg2.OperationalError as e:
        raise RuntimeError(f"Failed to connect to database: {config.host}:{config.port}/{config.dbname}") from e
    
    except Exception as e:
        raise RuntimeError(f"Unexpected error connecting to database") from e
