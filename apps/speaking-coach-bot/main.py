import asyncio
import logging
import sys
from typing import Optional, Any
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, MenuButtonCommands
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from src.config import load_settings
from src.repositories import create_coach_repository
from src.services.user_service import UserService
from src.services.ai_coach_service import AICoachService
from src.services.tts_service import TTSService
from src.services.dialogue_service import DialogueService
from src.worker.dispatcher import VoiceJobDispatcher
from src.bot.middlewares.user_tracker import UserTrackerMiddleware
from src.bot.handlers import register_handlers
from src.services.reminder_service import reminder_worker_loop

try:
    from arq.connections import RedisSettings, create_pool
except ImportError:
    RedisSettings = None
    create_pool = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("speaking_coach_bot")


async def setup_bot_commands(bot: Bot) -> None:
    """Register menu commands with Telegram API."""
    commands = [
        BotCommand(command="start", description="Mulai bot & profil"),
        BotCommand(command="mock_ielts", description="Simulasi IELTS Speaking"),
        BotCommand(command="shadow", description="Latihan intonasi nada"),
        BotCommand(command="phonemes", description="Klinik pengucapan bunyi"),
        BotCommand(command="tenses", description="Klinik latihan tenses aktif"),
        BotCommand(command="scenario", description="Ganti situasi percakapan"),
        BotCommand(command="reset", description="Mulai percakapan dari awal"),
        BotCommand(command="topic", description="Topik latihan bicara"),
        BotCommand(command="level", description="Ganti tingkat kemahiran"),
        BotCommand(command="review", description="Catatan kosakata & grammar"),
        BotCommand(command="progress", description="Kartu statistik, XP & streak"),
        BotCommand(command="voice", description="Ganti suara AI"),
        BotCommand(command="speed", description="Atur kecepatan suara AI"),
        BotCommand(command="remind", description="Atur pengingat harian"),
        BotCommand(command="invite", description="Ajak teman & bonus kuota"),
        BotCommand(command="upgrade", description="Buka fitur Premium"),
        BotCommand(command="help", description="Panduan penggunaan"),
        BotCommand(command="about", description="Info bot"),
    ]
    await bot.set_my_commands(commands)
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception as e:
        logger.warning("Could not set chat menu button: %s", e)
    logger.info("Speaking Coach bot menu commands & Menu button synchronized")


async def init_redis_pool(redis_url: str) -> Optional[Any]:
    """Attempt to initialize Arq Redis connection pool."""
    if not redis_url or not create_pool or not RedisSettings:
        logger.info("Redis URL not provided or arq not installed. Running in In-Process worker mode.")
        return None
    try:
        settings = RedisSettings.from_dsn(redis_url)
        pool = await create_pool(settings)
        logger.info("Connected to Redis Arq queue pool at %s", redis_url)
        return pool
    except Exception as e:
        logger.warning("Could not connect to Redis (%s). Falling back to In-Process worker mode.", e)
        return None


async def on_startup(bot: Bot, settings, db_conn) -> None:
    """Startup lifecycle hook."""
    logger.info("Initializing Speaking Coach (Mode: %s)...", settings.bot_mode)
    await db_conn.init_schema()
    await setup_bot_commands(bot)

    if settings.bot_mode == "webhook":
        target = f"{settings.webhook_url.rstrip('/')}{settings.webhook_path}"
        logger.info("Setting webhook to: %s", target)
        await bot.set_webhook(
            url=target,
            secret_token=settings.webhook_secret or None,
            drop_pending_updates=True,
        )


async def on_shutdown(bot: Bot, settings, arq_pool: Optional[Any] = None, repo: Optional[Any] = None) -> None:
    """Shutdown lifecycle hook."""
    logger.info("Shutting down Speaking Coach bot...")
    if arq_pool:
        try:
            await arq_pool.close()
        except Exception:
            pass
    if repo and hasattr(repo, "close"):
        try:
            await repo.close()
        except Exception:
            pass
    if settings.bot_mode == "webhook":
        await bot.delete_webhook()
    await bot.session.close()


def run_webhook(
    bot: Bot,
    dp: Dispatcher,
    settings,
    db_conn,
    user_service: UserService,
    ai_coach_service: AICoachService,
    tts_service: TTSService,
    dialogue_service: DialogueService,
    repo: Any,
) -> None:
    """Run bot in Webhook mode via aiohttp."""
    app = web.Application()

    dp["user_service"] = user_service
    dp["ai_coach_service"] = ai_coach_service
    dp["tts_service"] = tts_service
    dp["dialogue_service"] = dialogue_service

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret or None,
    )
    webhook_handler.register(app, path=settings.webhook_path)

    async def _health_handler(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "SpeakingCoachBot", "mode": "webhook"})

    app.router.add_get("/", _health_handler)
    app.router.add_get("/health", _health_handler)

    setup_application(app, dp, bot=bot)

    async def _on_startup_app(_):
        arq_pool = await init_redis_pool(settings.redis_url)
        dp["arq_pool"] = arq_pool
        dp["voice_dispatcher"] = VoiceJobDispatcher(arq_pool=arq_pool)

        await on_startup(bot, settings, db_conn)
        dp["reminder_task"] = asyncio.create_task(
            reminder_worker_loop(bot=bot, user_service=user_service)
        )

    async def _on_shutdown_app(_):
        reminder_task = dp.get("reminder_task")
        if reminder_task and not reminder_task.done():
            reminder_task.cancel()
            try:
                await reminder_task
            except asyncio.CancelledError:
                pass
        await on_shutdown(bot, settings, arq_pool=dp.get("arq_pool"), repo=repo)

    app.on_startup.append(_on_startup_app)
    app.on_shutdown.append(_on_shutdown_app)

    logger.info(
        "Webhook listening at http://%s:%s%s",
        settings.webapp_host,
        settings.webapp_port,
        settings.webhook_path,
    )
    web.run_app(app, host=settings.webapp_host, port=settings.webapp_port)


async def run_polling(
    bot: Bot,
    dp: Dispatcher,
    settings,
    db_conn,
    user_service: UserService,
    ai_coach_service: AICoachService,
    tts_service: TTSService,
    dialogue_service: DialogueService,
    repo: Any,
) -> None:
    """Run bot in Long Polling mode with embedded HTTP health check server."""
    dp["user_service"] = user_service
    dp["ai_coach_service"] = ai_coach_service
    dp["tts_service"] = tts_service
    dp["dialogue_service"] = dialogue_service

    await on_startup(bot, settings, db_conn)

    arq_pool = await init_redis_pool(settings.redis_url)
    dp["arq_pool"] = arq_pool
    dp["voice_dispatcher"] = VoiceJobDispatcher(arq_pool=arq_pool)

    reminder_task = asyncio.create_task(
        reminder_worker_loop(bot=bot, user_service=user_service)
    )
    dp["reminder_task"] = reminder_task

    # Background health check server for Koyeb / Render / Fly.io Free Web Services
    health_app = web.Application()
    async def _health_handler(_: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "service": "SpeakingCoachBot", "mode": "polling"})

    health_app.router.add_get("/", _health_handler)
    health_app.router.add_get("/health", _health_handler)
    health_runner = web.AppRunner(health_app)
    await health_runner.setup()
    health_site = web.TCPSite(health_runner, settings.webapp_host, settings.webapp_port)
    try:
        await health_site.start()
        logger.info("Health check server listening at http://%s:%s/health", settings.webapp_host, settings.webapp_port)
    except Exception as e:
        logger.warning("Could not start background health check server: %s", e)

    try:
        logger.info("Long polling started. Send a voice note in Telegram to practice! (100% Native Telegram)")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        try:
            await health_runner.cleanup()
        except Exception:
            pass
        if reminder_task and not reminder_task.done():
            reminder_task.cancel()
            try:
                await reminder_task
            except asyncio.CancelledError:
                pass
        await on_shutdown(bot, settings, arq_pool=arq_pool, repo=repo)


def main() -> None:
    """Bootstrap speaking coach bot with Clean Architecture."""
    settings = load_settings()

    # 1. Data Access Layer (Dual SQLite / PostgreSQL via factory)
    repo, db_conn = create_coach_repository(
        database_url=settings.database_url,
        database_path=settings.database_path,
    )

    # 2. Domain Service Layer
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

    # 3. Presentation / Transport Layer
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()

    # Middlewares
    dp.update.middleware(UserTrackerMiddleware(user_service=user_service))

    # Handlers
    register_handlers(dp)

    # 4. Mode Selection
    if settings.bot_mode == "webhook":
        run_webhook(bot, dp, settings, db_conn, user_service, ai_coach_service, tts_service, dialogue_service, repo)
    else:
        asyncio.run(run_polling(bot, dp, settings, db_conn, user_service, ai_coach_service, tts_service, dialogue_service, repo))


if __name__ == "__main__":
    main()
