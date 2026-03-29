from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Example: postgresql+psycopg2://user:pass@localhost:5432/db
    DATABASE_URL: str = "postgresql+psycopg2://ai_lms:ai_lms_password@localhost:5432/ai_lms_db"

    JWT_SECRET: str = "dev_only_secret_change_me"
    JWT_ALGORITHM: str = "HS256"
    JWT_TTL_SECONDS: int = 3600

    # Frontend dev server origin(s)
    CORS_ORIGINS: str = "*"

    # Phase 3 AI provider settings
    AI_PROVIDER: str = "groq"
    AI_MODEL: str = "llama-3.1-8b-instant"
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.groq.com/openai/v1"

    # Phase 2 async processing
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    JOB_POLL_INTERVAL_MS: int = 2000


settings = Settings()

