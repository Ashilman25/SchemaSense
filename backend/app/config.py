from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_url: str = "postgresql://user:password@localhost:5432/schemasense"
    openai_api_key: str | None = None
    environment: str = "development"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    provision_mode_default: str = "managed"

    # Admin cluster DSN for provisioning (CREATE DATABASE, CREATE ROLE)
    # Must connect to admin/superuser account with permission to create databases and roles
    # Dev (backend on host): postgresql://schemasense:schemasense_dev@localhost:5432/postgres
    # Dev (backend in Docker): postgresql://schemasense:schemasense_dev@postgres:5432/postgres
    # Prod: Neon connection string with admin/owner privileges
    # Note: Connect to 'postgres' database (admin DB), not the app database
    managed_pg_admin_dsn: str = "postgresql://schemasense:schemasense_dev@localhost:5432/postgres"

    # Session management
    session_secret_key: str = "dev-secret-key-change-in-production"
    session_cookie_name: str = "schemasense_session"
    session_max_age_days: int = 365


    provision_max_dbs_per_session: int = 3  
    provision_global_max_dbs: int = 100     

    provision_default_statement_timeout_ms: int = 15000  
    provision_connection_limit_per_role: int = 10        
    provision_idle_in_transaction_timeout_ms: int = 30000  

    ephemeral_ttl_minutes: int = 60  #maybe for future

    enable_sample_data: bool = True  # Allow loading sample sales schema

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_prefix = "SCHEMASENSE_",
        case_sensitive = False,
    )


#load settings from env or default
@lru_cache
def get_settings() -> Settings:
    return Settings()
