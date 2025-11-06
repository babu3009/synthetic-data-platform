import secrets
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Synthetic Data Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    
    # CORS settings
    # Use plain strings here to avoid AnyHttpUrl validation errors for dev loopback origins.
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "synthetic_data_platform"
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[PostgresDsn] = None
    # Database schema (and optional testing schema)
    DB_SCHEMA: str = "synthetic_data"
    TESTING_DB_SCHEMA: Optional[str] = None

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return str(self.DATABASE_URL)
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=int(self.POSTGRES_PORT),
            path=self.POSTGRES_DB,
        ))

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # MinIO settings
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "synthetic-data"

    # JWT settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Data generation settings
    MAX_ROWS_PER_GENERATION: int = 1_000_000
    DEFAULT_ROWS_PER_GENERATION: int = 1000

    # Inference & rate limiting
    INFER_RATE_LIMIT_PER_MINUTE: int = 60
    MAX_INFER_COLUMNS: int = 500
    DEFAULT_INFER_TEMPERATURE: float = 0.2

    # LLM provider configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = None
    LMSTUDIO_BASE_URL: Optional[str] = None
    DEFAULT_LLM_PROVIDER: Optional[str] = None
    DEFAULT_LLM_MODEL: Optional[str] = None

    # Observability
    LOG_LEVEL: str = "info"
    ENABLE_METRICS: bool = True
    ENABLE_TRACING: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    OTEL_EXPORTER_OTLP_PROTOCOL: str = "http"
    OTEL_SERVICE_NAME: str = "synthetic-data-backend"
    SENTRY_DSN: Optional[str] = None

    # Audit / retention
    AUDIT_RETENTION_DAYS: int = 30

    # Security toggles
    AUTH_DISABLED: bool = False
    API_KEY_HASH_ALGO: str = "sha256"

    # Redis unified URL
    REDIS_URL: Optional[str] = None

    # MinIO extras
    MINIO_SECURE: bool = False
    MINIO_REGION: Optional[str] = None

    # DB pool tuning
    DB_POOL_SIZE: int = 5
    DB_POOL_MAX_OVERFLOW: int = 10
    DB_CONN_TIMEOUT: int = 10

    # Feature flags
    FF_ENABLE_DISCOVERY_CACHE: bool = True
    FF_ENABLE_PROBE_AUDIT: bool = True
    FF_ENABLE_RATE_LIMIT_AUDIT: bool = True

    # Encryption (future expansion)
    ENCRYPTION_KEK: Optional[str] = None

    # App identity
    APP_ENV: str = "local"
    APP_INSTANCE_ID: str = "dev-1"

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Allow extra env vars like OIDC_* without raising
    )


settings = Settings()