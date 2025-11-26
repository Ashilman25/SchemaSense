# define a settings class (pydantic BaseSettings), 
# placeholder fields for DB URL, OpenAI key, environment flags, 
# and a singleton helper like get_settings() that just returns default 
# values for now.

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_url: str = "postgresql://user:password@localhost:5432/schemasense"
    openai_api_key: str | None = None
    environment: str = "development"
    allowed_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SCHEMASENSE_",
        case_sensitive=False,
    )


#load settings from env or default
@lru_cache
def get_settings() -> Settings:
    return Settings()
