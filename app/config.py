from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: Optional[str] = None
    database_url_direct: Optional[str] = None
    pi_cmd_path: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
