from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgrespassword@localhost:5432/notification_db"
    )
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0")

    ENVIRONMENT: str = Field(default="dev")
    LOG_LEVEL: str = Field(default="INFO")

    PROVIDER_MIN_LATENCY_MS: int = Field(default=200)
    PROVIDER_MAX_LATENCY_MS: int = Field(default=500)

    EMAIL_FAILURE_RATE: float = Field(default=0.1)
    SMS_FAILURE_RATE: float = Field(default=0.1)
    PUSH_FAILURE_RATE: float = Field(default=0.1)

    RATE_LIMIT_MAX_REQUESTS: int = Field(default=100)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=3600)

    IDEMPOTENCY_TTL_SECONDS: int = Field(default=86400)

settings = Settings()
