import logging
import os
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Ensure project root is in sys.path for modular imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import load_settings
from src.repositories import create_coach_repository
from src.services.user_service import UserService
from src.services.ai_coach_service import AICoachService
from src.services.tts_service import TTSService
from src.services.dialogue_service import DialogueService
from src.worker.dispatcher import VoiceJobDispatcher
from src.bot.middlewares.user_tracker import UserTrackerMiddleware
from src.bot.handlers import register_handlers

logger = logging.getLogger("speaking_coach_vercel")

# 1. Load Settings
settings = load_settings()

# In Vercel serverless, if no external DATABASE_URL is set, use /tmp for SQLite writes
database_url = settings.database_url
database_path = settings.database_path
if not database_url and not Path(database_path).is_absolute():
    database_path = str(Path(tempfile.gettempdir()) / "speaking_coach.db")

# 2. Data Access & Domain Services
repo, db_conn = create_coach_repository(
    database_url=database_url,
    database_path=database_path,
)
user_service = UserService(repository=repo)
ai_coach_service = AICoachService(
    api_key=settings.gemini_api_key,
    model_name=settings.gemini_model,
)
tts_service = TTSService()
dialogue_service = DialogueService(
    repository=repo,
    redis_url=settings.redis_url,
)

# 3. Presentation / Aiogram Setup
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
dp = Dispatcher()

# Dependency Injection into Dispatcher context
dp["user_service"] = user_service
dp["ai_coach_service"] = ai_coach_service
dp["tts_service"] = tts_service
dp["dialogue_service"] = dialogue_service
dp["voice_dispatcher"] = VoiceJobDispatcher(arq_pool=None)

# Middlewares & Handlers
dp.update.middleware(UserTrackerMiddleware(user_service=user_service))
register_handlers(dp)

_initialized = False


async def ensure_db_initialized():
    """Lazily initialize database schema on first invocation."""
    global _initialized
    if not _initialized:
        try:
            await db_conn.init_schema()
            _initialized = True
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.error("Failed to initialize database schema: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan hook for warming up dependencies."""
    await ensure_db_initialized()
    yield
    if hasattr(repo, "close"):
        try:
            await repo.close()
        except Exception:
            pass
    await bot.session.close()


# 4. FastAPI Serverless App
app = FastAPI(
    title="Speaking Coach AI - Vercel Serverless Webhook",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> Dict[str, str]:
    """Root info endpoint."""
    return {
        "status": "online",
        "service": "English Speaking Coach AI",
        "runtime": "Vercel Serverless",
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for Vercel and uptime monitoring."""
    return {
        "status": "ok",
        "service": "SpeakingCoachBot",
        "mode": "vercel-serverless",
        "db": "postgresql" if settings.database_url else "sqlite-tmp",
    }


@app.post("/api/index")
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive and dispatch Telegram webhook updates."""
    # Verify secret token if configured
    if settings.webhook_secret:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_header != settings.webhook_secret:
            logger.warning("Rejected webhook: invalid or missing X-Telegram-Bot-Api-Secret-Token")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: invalid secret token",
            )

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    await ensure_db_initialized()

    try:
        update = types.Update(**data)
        await dp.feed_update(bot=bot, update=update)
        return {"ok": True}
    except Exception as e:
        logger.error("Error processing update: %s", e)
        # Always return 200/ok to Telegram to prevent infinite retry loops
        return {"ok": True, "error": str(e)}
