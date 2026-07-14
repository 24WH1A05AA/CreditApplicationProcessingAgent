import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "CreditApplicationProcessingAgent"
    ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security
    SECRET_KEY: str = "dev_secret_key_change_in_production_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///./credit_processing.db"

    # OpenAI & LLM (Defaulting to OpenRouter Free Models)
    OPENAI_API_KEY: str = "mock-key-for-development"
    OPENAI_MODEL: str = "meta-llama/llama-3-8b-instruct:free"
    OPENAI_API_BASE: str = "https://openrouter.ai/api/v1"

    # RAG
    CHROMA_DB_PATH: str = "./data/chromadb"
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Config source
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate settings
settings = Settings()
