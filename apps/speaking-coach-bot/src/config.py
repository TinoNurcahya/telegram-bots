import os
from typing import Literal

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    class BaseSettings:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def Field(default=None, default_factory=None, description=""):  # type: ignore
        return default

    SettingsConfigDict = dict  # type: ignore


class Settings(BaseSettings):
    """Configuration loaded from environment variables and .env file."""

    bot_token: str = Field(default="mock_token", description="Telegram Bot API Token from @BotFather")
    gemini_api_key: str = Field(default="mock_key", description="Google Gemini API Key from Google AI Studio")
    gemini_model: str = Field(default="gemini-3.1-flash-lite", description="Gemini multimodal model")

    bot_mode: Literal["polling", "webhook"] = Field(
        default="polling", description="Execution mode: 'polling' or 'webhook'"
    )
    database_path: str = Field(
        default="speaking_coach.db", description="Path to SQLite database file"
    )
    database_url: str = Field(
        default="",
        description="Optional PostgreSQL URL (e.g. postgresql://user:pass@host:5432/dbname). If empty, SQLite is used.",
    )
    redis_url: str = Field(
        default="",
        description="Optional Redis URL for Arq queue worker (e.g. redis://localhost:6379/0). If empty, fallback to in-process.",
    )

    # Webhook settings
    webhook_url: str = Field(
        default="https://localhost/webhook",
        description="Public HTTPS URL for Telegram webhook",
    )
    webhook_path: str = Field(
        default="/webhook", description="Endpoint for incoming webhooks"
    )
    webhook_secret: str = Field(
        default="", description="Optional secret token for verifying webhooks"
    )
    webapp_host: str = Field(
        default="0.0.0.0", description="Host address for webhook server"
    )
    webapp_port: int = Field(
        default=int(os.getenv("PORT") or os.getenv("WEBAPP_PORT") or 8000),
        description="Port for webhook server / cloud health check",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_settings() -> Settings:
    """Instantiate and validate application settings."""
    try:
        return Settings()
    except Exception:
        return Settings(
            bot_token=os.getenv("BOT_TOKEN", "mock_token"),
            gemini_api_key=os.getenv("GEMINI_API_KEY", "mock_key"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite"),
            bot_mode=os.getenv("BOT_MODE", "polling"),
            database_path=os.getenv("DATABASE_PATH", "speaking_coach.db"),
            database_url=os.getenv("DATABASE_URL", ""),
            redis_url=os.getenv("REDIS_URL", ""),
            webhook_url=os.getenv("WEBHOOK_URL", "https://localhost/webhook"),
            webhook_path=os.getenv("WEBHOOK_PATH", "/webhook"),
            webhook_secret=os.getenv("WEBHOOK_SECRET", ""),
            webapp_host=os.getenv("WEBAPP_HOST", "0.0.0.0"),
            webapp_port=int(os.getenv("PORT") or os.getenv("WEBAPP_PORT") or "8000"),
        )
