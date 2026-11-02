import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from aiogram.types import FSInputFile

from src.config import settings
from src.services.video_orchestrator import VideoOrchestrator, FullVideoResult
from src.bot.keyboards.inline import get_video_actions_keyboard

logger = logging.getLogger(__name__)

class DailyVideoScheduler:
    def __init__(self, bot: Optional[Bot] = None, orchestrator: Optional[VideoOrchestrator] = None):
        self.bot = bot
        self.orchestrator = orchestrator or VideoOrchestrator()
        self.scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)

    def start(self) -> None:
        """Configures and starts the daily cron job."""
        if not settings.ENABLE_DAILY_SCHEDULER:
            logger.info("Daily video scheduler is disabled in configuration.")
            return

        time_parts = settings.DAILY_SCHEDULE_TIME.split(":")
        hour = int(time_parts[0]) if len(time_parts) > 0 else 8
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            timezone=settings.SCHEDULER_TIMEZONE
        )

        self.scheduler.add_job(
            self.execute_daily_run,
            trigger=trigger,
            id="daily_shorts_generator",
            name="Daily AI Shorts Generation",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(
            f"Daily Video Scheduler successfully started: Scheduled at {settings.DAILY_SCHEDULE_TIME} ({settings.SCHEDULER_TIMEZONE})"
        )

    async def execute_daily_run(self) -> None:
        """Executes the automated daily video generation and broadcasts to target chat."""
        logger.info("⏰ Triggering Automated Daily AI Shorts Generation...")

        try:
            # 1. Orchestrate video generation
            result: FullVideoResult = await self.orchestrator.create_short_video(
                topic=None,  # Pick random trending
                user_id=settings.TARGET_CHAT_ID if settings.TARGET_CHAT_ID else None,
                trigger_type="scheduled",
                auto_upload_youtube=settings.AUTO_UPLOAD_YOUTUBE
            )

            # 2. Broadcast video to Telegram Chat / Channel if bot & chat_id are present
            if self.bot and settings.TARGET_CHAT_ID != 0:
                caption = (
                    f"🎬 **Daily Automated AI Shorts**\n\n"
                    f"📌 **{result.title}**\n\n"
                    f"📝 {result.description}\n\n"
                    f"🏷️ {' '.join(result.tags)}\n\n"
                    f"⏱️ Durasi: {result.duration:.1f} detik"
                )
                if result.youtube_id:
                    clean_yt_id = result.youtube_id.replace("_", "\\_")
                    caption += f"\n\n▶️ **YouTube Shorts**: https://youtube.com/shorts/{clean_yt_id}"

                video_file = FSInputFile(result.video_path)
                thumb_input = FSInputFile(result.thumbnail_path) if result.thumbnail_path and os.path.exists(result.thumbnail_path) else None
                await self.bot.send_video(
                    chat_id=settings.TARGET_CHAT_ID,
                    video=video_file,
                    caption=caption,
                    parse_mode="Markdown",
                    thumbnail=thumb_input,
                    reply_markup=get_video_actions_keyboard(result.video_id, youtube_id=result.youtube_id)
                )
                logger.info(f"Daily Shorts delivered to chat ID: {settings.TARGET_CHAT_ID}")

        except Exception as e:
            logger.error(f"Error in daily scheduled video job: {e}", exc_info=True)
            if self.bot and settings.TARGET_CHAT_ID != 0:
                try:
                    await self.bot.send_message(
                        chat_id=settings.TARGET_CHAT_ID,
                        text=f"⚠️ Gagal membuat video harian otomatis:\n`{str(e)}`",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Daily Video Scheduler shut down.")
