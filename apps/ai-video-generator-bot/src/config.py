import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Credentials
    BOT_TOKEN: str = Field(default="", description="Telegram Bot Token from @BotFather")
    TARGET_CHAT_ID: int = Field(default=0, description="Telegram User or Channel ID for daily automated drops")

    # AI & Scripting (Gemini)
    GEMINI_API_KEY: str = Field(default="", description="Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-3.1-flash-lite", description="Gemini Model Identifier")

    # Automation Scheduler
    ENABLE_DAILY_SCHEDULER: bool = Field(default=True, description="Enable APScheduler for daily Shorts generation")
    DAILY_SCHEDULE_TIME: str = Field(default="08:00", description="HH:MM in 24h format")
    SCHEDULER_TIMEZONE: str = Field(default="Asia/Jakarta", description="Timezone string")

    # Audio & Voiceover (Edge-TTS)
    VOICE_NAME: str = Field(default="en-US-JennyNeural", description="Voice ID from Edge-TTS")
    VOICE_RATE: str = Field(default="+0%", description="Speaking speed rate")
    VOICE_PITCH: str = Field(default="+0Hz", description="Voice pitch tuning")

    # Video Specifications (Vertical 9:16 Shorts)
    VIDEO_WIDTH: int = Field(default=720)
    VIDEO_HEIGHT: int = Field(default=1280)
    FPS: int = Field(default=24)
    MAX_SCENE_COUNT: int = Field(default=6)
    MIN_SCENE_DURATION: float = Field(default=5.0)

    # External APIs
    PEXELS_API_KEY: str = Field(default="", description="Optional Pexels API Key for HD stock video clips")

    # YouTube Data API v3
    AUTO_UPLOAD_YOUTUBE: bool = Field(default=True, description="Automatically upload generated videos to YouTube Shorts")
    YOUTUBE_CLIENT_SECRETS_FILE: str = Field(default="client_secrets.json")
    YOUTUBE_CREDENTIALS_STORAGE: str = Field(default="youtube_token.json")

    # Storage Paths
    DATABASE_PATH: str = Field(default="storage/ai_shorts.db")
    TEMP_DIR: str = Field(default="storage/temp")
    OUTPUT_DIR: str = Field(default="storage/output")
    ASSETS_DIR: str = Field(default="assets")

    @property
    def abs_temp_dir(self) -> Path:
        path = BASE_DIR / self.TEMP_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def abs_output_dir(self) -> Path:
        path = BASE_DIR / self.OUTPUT_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def abs_assets_dir(self) -> Path:
        path = BASE_DIR / self.ASSETS_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def abs_db_path(self) -> Path:
        db_file = BASE_DIR / self.DATABASE_PATH
        db_file.parent.mkdir(parents=True, exist_ok=True)
        return db_file

settings = Settings()
