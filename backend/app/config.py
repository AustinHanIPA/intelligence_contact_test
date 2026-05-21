"""
应用配置
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/intelligent_contact"
    DATABASE_URL_SYNC: str = "postgresql://postgres:password@localhost:5432/intelligent_contact"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4"

    # Embedding
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384

    # JWT
    SECRET_KEY: str = "your-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # App
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Tool call timeout
    TOOL_CALL_TIMEOUT: int = 8

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
