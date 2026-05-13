"""Configuration management for Talaash using pydantic-settings."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    TALAASH_DB_PATH: str = Field(default="./talaash_db")
    TALAASH_INDEX_PATH: str = Field(default="./talaash_index")
    TALAASH_MODEL_NAME: str = Field(
        default="paraphrase-multilingual-MiniLM-L12-v2"
    )
    TALAASH_MAX_FILE_SIZE_MB: int = Field(default=100)
    TALAASH_SUPPORTED_EXTENSIONS: list[str] = Field(
        default=[".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg"]
    )
    TALAASH_BATCH_SIZE: int = Field(default=10)
    TALAASH_API_PORT: int = Field(default=8765)
    TALAASH_LOG_LEVEL: str = Field(default="INFO")


settings = Settings()
