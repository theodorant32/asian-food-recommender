"""Application configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Asian Food Intelligence Explorer"
    debug: bool = False
    version: str = "0.1.0"
    host: str = "0.0.0.0"
    port: int = 8000
    data_dir: str = "./data"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_results: int = 50
    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
