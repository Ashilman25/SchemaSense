from typing import Optional
from urllib.parse import quote_plus
from pydantic import BaseModel
from app.cache.redis_client import get_redis_client
from app.config import get_settings
import psycopg2


class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    dbname: str = "schemasense"
    user: str = "schemasense"
    password: str = "schemasense_dev"

redis_client = get_redis_client()
settings = get_settings()
_session_configs: dict[str, DatabaseConfig] = {}

REDIS_KEY_PREFIX = "schemasense:session"


#save current request db config for this session
def set_database_config(config: DatabaseConfig, session_id: str) -> None:
    key = f"{REDIS_KEY_PREFIX}:{session_id}:db_config"
    ttl = settings.session_max_age_days * 86400

    if config is None:
        result = redis_client.delete_key(key)
        if result["status"] == 0 or not settings.redis_enabled:
            _session_configs.pop(session_id, None)

    else:
        result = redis_client.set_response(key, config.model_dump(), ttl_seconds=ttl)
        if result["status"] == 0 or not settings.redis_enabled:
            _session_configs[session_id] = config


#get db config for this session
def get_database_config(session_id: str) -> Optional[DatabaseConfig]:
    key = f"{REDIS_KEY_PREFIX}:{session_id}:db_config"
    result = redis_client.get_response(key)

    if result["status"] == 1:
        return DatabaseConfig(**result["data"])

    if not settings.redis_enabled:
        return _session_configs.get(session_id)

    return None


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
