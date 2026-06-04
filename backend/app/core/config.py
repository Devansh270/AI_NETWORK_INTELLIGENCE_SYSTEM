"""
Application configuration loaded from environment variables.

Uses pydantic-settings to read .env files and provide typed access to
all configuration values. This keeps secrets out of code and makes the
app deployable to any environment by just changing the .env file.

Defaults are localhost-friendly so the app works when uvicorn runs
directly on a developer's machine. When FastAPI runs inside Docker,
the .env file overrides the hosts with Docker service names.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All AINIS configuration values, loaded from infra/.env."""

    # ─── PostgreSQL ────────────────────────────────────────────
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # ─── InfluxDB ──────────────────────────────────────────────
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "myorg"
    influxdb_bucket: str = "metrics"

    # ─── Redis ─────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_channel: str = "packets"

    # ─── FastAPI ───────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file="../infra/.env",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Using lru_cache so the .env file is only read once per process —
    subsequent calls return the same object. Cheap and safe to call
    anywhere in the codebase.
    """
    return Settings()
