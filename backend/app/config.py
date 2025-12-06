from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import sys


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


    ttl_cleanup_days: int = 7  # Delete databases inactive for more than this many days
    admin_api_key: str = "dev-admin-key-change-in-production"
    enable_sample_data: bool = True  

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_prefix = "SCHEMASENSE_",
        case_sensitive = False,
    )

    @field_validator("managed_pg_admin_dsn")
    @classmethod
    def validate_admin_dsn_in_production(cls, v: str, info) -> str:
        environment = info.data.get("environment", "development")

        # In production or demo, require a non-default DSN
        if environment in ("production", "prod", "demo"):
            default_dsns = [
                "postgresql://schemasense:schemasense_dev@localhost:5432/postgres",
                "postgresql://schemasense:schemasense_dev@postgres:5432/postgres",
            ]

            if v in default_dsns:
                print(
                    f"\n{'='*80}\n"
                    f"FATAL ERROR: MANAGED_PG_ADMIN_DSN must be configured for {environment} environment.\n"
                    f"The default development DSN is not allowed in production.\n"
                    f"Please set SCHEMASENSE_MANAGED_PG_ADMIN_DSN environment variable.\n"
                    f"{'='*80}\n",
                    file=sys.stderr
                )
                sys.exit(1)

        # validate DSN format
        if not v.startswith("postgresql://"):
            print(
                f"\n{'='*80}\n"
                f"FATAL ERROR: MANAGED_PG_ADMIN_DSN must be a valid PostgreSQL connection string.\n"
                f"Expected format: postgresql://user:password@host:port/database\n"
                f"{'='*80}\n",
                file=sys.stderr
            )
            sys.exit(1)

        return v

    @field_validator("session_secret_key")
    @classmethod
    def validate_session_secret_in_production(cls, v: str, info) -> str:
        environment = info.data.get("environment", "development")

        if environment in ("production", "prod", "demo"):
            if v == "dev-secret-key-change-in-production":
                print(
                    f"\n{'='*80}\n"
                    f"FATAL ERROR: SESSION_SECRET_KEY must be changed for {environment} environment.\n"
                    f"Please set SCHEMASENSE_SESSION_SECRET_KEY to a strong random value.\n"
                    f"{'='*80}\n",
                    file=sys.stderr
                )
                sys.exit(1)

        return v

    @field_validator("admin_api_key")
    @classmethod
    def validate_admin_api_key_in_production(cls, v: str, info) -> str:
        environment = info.data.get("environment", "development")

        if environment in ("production", "prod", "demo"):
            if v == "dev-admin-key-change-in-production":
                print(
                    f"\n{'='*80}\n"
                    f"FATAL ERROR: ADMIN_API_KEY must be changed for {environment} environment.\n"
                    f"Please set SCHEMASENSE_ADMIN_API_KEY to a strong random value.\n"
                    f"Generate one with: openssl rand -hex 32\n"
                    f"{'='*80}\n",
                    file=sys.stderr
                )
                sys.exit(1)

        return v


#load settings from env or default
@lru_cache
def get_settings() -> Settings:
    return Settings()
