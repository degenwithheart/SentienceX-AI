from pydantic import BaseSettings, Field
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # Model settings
    SENTIMENT_MODEL: Optional[str] = Field(None)
    THREAT_MODEL: Optional[str] = Field(None)
    SARCASM_MODEL: Optional[str] = Field(None)
    RESPONSE_MODEL: Optional[str] = Field(None)
    USE_LOCAL_MODELS: bool = Field(False)
    MODEL_DEVICE: str = Field("cpu")  # cpu, cuda, auto
    MODEL_CACHE_DIR: str = Field("backend/app/saved_model")

    # Infra
    AUTH_TOKEN: Optional[str] = Field(None)
    REDIS_URL: Optional[str] = Field(None)
    RABBITMQ_URL: Optional[str] = Field(None)
    DATABASE_URL: Optional[str] = Field(None)

    # Runtime
    DISABLE_HTTPS_ENFORCEMENT: bool = Field(False)
    RETRAIN_COOLDOWN: int = Field(300)

    # Security / rate limiting
    RATE_LIMIT_REQUESTS: int = Field(60)
    RATE_LIMIT_WINDOW: int = Field(60)
    # Optional namespace for rate limit keys in Redis (helps multi-tenant)
    RATE_LIMIT_NAMESPACE: str = Field("sentiencex")
    # Optional JSON string mapping route prefixes to limit dicts. Example:
    # '{"/retrain": {"requests": 2, "window": 300, "burst": 4}, "/chat": {"requests": 60, "window": 60}}'
    RATE_LIMITS: Optional[str] = Field(None)
    # If True, invalid RATE_LIMITS JSON will cause startup failure
    RATE_LIMITS_STRICT: bool = Field(False)
    # Admin / management
    ADMIN_TOKEN: Optional[str] = Field(None)
    ADMIN_ROLE: Optional[str] = Field(None)

    # Metrics
    ENABLE_METRICS: bool = Field(True)
    # Admin header and IP whitelist
    # Header name the admin token must be provided in (default: X-Admin-Token)
    ADMIN_HEADER_NAME: str = Field("X-Admin-Token")
    # Comma-separated list of IP addresses that are allowed admin access without a token
    ADMIN_IP_WHITELIST: Optional[str] = Field(None)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
