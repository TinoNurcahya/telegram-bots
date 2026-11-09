import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonCommands

from src.config import settings
from src.repositories.database import init_db
from src.repositories.video_repo import VideoRepository
from src.bot.middleware.user_tracker import UserTrackingMiddleware
from src.bot.handlers import base, generator
from src.services.scheduler import DailyVideoScheduler

# Setup UTF-8 encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ai_shorts_studio")

async def setup_bot_commands(bot: Bot):
    """
    Registers native Telegram bot commands and configures the native [ ≡ Menu ] button
    in the chat bar so users can quickly pick actions without typing '/'.
    """
    commands = [
        BotCommand(command="generate", description="🎬 Generate Video Shorts (9:16)"),
        BotCommand(command="longform", description="🎥 Generate Dokumenter Panjang (16:9)"),
        BotCommand(command="topics", description="🔍 15+ Kategori Misteri & Sains"),
        BotCommand(command="stats", description="📊 Riwayat & Statistik Video"),
        BotCommand(command="status", description="⚙️ Status Sistem & Otomasi"),
        BotCommand(command="help", description="📖 Panduan Penggunaan"),
        BotCommand(command="start", description="🏠 Menu Utama Bot"),
    ]
    try:
        await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("✅ Telegram [ ≡ Menu ] button and commands registered successfully.")
    except Exception as e:
        logger.warning(f"Could not register Telegram bot commands: {e}")

async def main():
    logger.info("Initializing AI Shorts Studio Bot...")

    # 1. Initialize embedded SQLite persistence
    await init_db()
    logger.info("SQLite Database initialized.")

    # 2. Check Bot Token
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "your_telegram_bot_token_here":
        logger.warning(
            "⚠️ BOT_TOKEN is not set or using placeholder! "
            "Please configure your BOT_TOKEN in apps/ai-video-generator-bot/.env"
        )

    # 3. Initialize Bot & Dispatcher with generous 300s timeout for video uploads
    from aiogram.client.session.aiohttp import AiohttpSession
    session = AiohttpSession(timeout=300.0)
    bot = Bot(
        token=settings.BOT_TOKEN if settings.BOT_TOKEN else "123456:PLACEHOLDER",
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        session=session
    )
    dp = Dispatcher()

    # 4. Attach Middlewares
    repo = VideoRepository()
    dp.update.outer_middleware(UserTrackingMiddleware(repo))

    # 5. Register Handlers
    dp.include_router(base.router)
    dp.include_router(generator.router)

    # 6. Initialize & Start Daily Automation Scheduler
    scheduler = DailyVideoScheduler(bot=bot)
    scheduler.start()

    # 7. Setup Native Telegram Commands & Menu Button
    if settings.BOT_TOKEN and settings.BOT_TOKEN != "your_telegram_bot_token_here":
        await setup_bot_commands(bot)

    logger.info("🤖 AI Shorts Studio Bot is ready and listening (Polling Mode)...")

    try:
        if settings.BOT_TOKEN and settings.BOT_TOKEN != "your_telegram_bot_token_here":
            # Clear any previously registered webhook so polling can receive updates
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Cleared previous webhook (drop_pending_updates=True).")
            await dp.start_polling(bot)
        else:
            logger.info("Running in offline demonstration mode. Press Ctrl+C to stop.")
            while True:
                await asyncio.sleep(3600)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("AI Shorts Studio Bot shut down cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process terminated by user.")
