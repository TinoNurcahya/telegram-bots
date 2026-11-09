import os
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
        """Configures and starts the staggered daily cron jobs (up to MAX_DAILY_AUTO_VIDEOS per day)."""
        if not settings.ENABLE_DAILY_SCHEDULER:
            logger.info("Daily video scheduler is disabled in configuration.")
            return

        schedule_times = settings.daily_schedule_times[: settings.MAX_DAILY_AUTO_VIDEOS]
        for idx, time_str in enumerate(schedule_times, start=1):
            time_parts = time_str.split(":")
            hour = int(time_parts[0]) if len(time_parts) > 0 else 13
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0

            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=settings.SCHEDULER_TIMEZONE
            )

            self.scheduler.add_job(
                self.execute_daily_run,
                trigger=trigger,
                id=f"daily_shorts_slot_{idx}",
                name=f"Daily AI Shorts Slot #{idx} ({time_str})",
                replace_existing=True
            )

        # Also register the daily 16:9 Long-Form Documentary slot (default 20:15 WIB)
        if getattr(settings, "LONGFORM_SCHEDULE_TIME", ""):
            lf_parts = settings.LONGFORM_SCHEDULE_TIME.strip().split(":")
            lf_hour = int(lf_parts[0]) if len(lf_parts) > 0 else 20
            lf_min = int(lf_parts[1]) if len(lf_parts) > 1 else 15
            self.scheduler.add_job(
                self.execute_daily_longform,
                trigger=CronTrigger(hour=lf_hour, minute=lf_min, timezone=settings.SCHEDULER_TIMEZONE),
                id="daily_longform_documentary",
                name=f"Daily 16:9 Long-Form Documentary ({settings.LONGFORM_SCHEDULE_TIME})",
                replace_existing=True
            )

        self.scheduler.start()
        logger.info(
            f"Daily Video Scheduler started: {len(schedule_times)} Shorts slots ({', '.join(schedule_times)}) + "
            f"1 Long-Form slot ({settings.LONGFORM_SCHEDULE_TIME}) [{settings.SCHEDULER_TIMEZONE}]"
        )

    async def execute_daily_longform(self) -> None:
        """Executes the automated daily 16:9 Long-Form Documentary generation."""
        logger.info("🎥 Triggering Automated Daily 16:9 Long-Form Documentary Generation...")
        await self.execute_daily_run(video_format="longform")

    async def execute_daily_run(self, video_format: str = "shorts") -> None:
        """Executes the automated daily video generation and broadcasts to target chat."""
        logger.info(f"⏰ Triggering Automated Daily AI Video Generation ({video_format})...")

        try:
            # 1. Orchestrate video generation
            result: FullVideoResult = await self.orchestrator.create_short_video(
                topic=None,  # Uses deterministic slot rotation + dynamic AI case discovery
                user_id=settings.TARGET_CHAT_ID if settings.TARGET_CHAT_ID else None,
                trigger_type="scheduled",
                auto_upload_youtube=settings.AUTO_UPLOAD_YOUTUBE,
                video_format=video_format
            )

            # 2. Broadcast video to Telegram Chat / Channel if bot & chat_id are present
            if self.bot and settings.TARGET_CHAT_ID != 0:
                voice_line = ""
                if getattr(result, "voice_persona", None) and getattr(result, "voice_name", None):
                    voice_line = f"\n🎙️ **Persona**: `{result.voice_persona}` | **Voice**: `{result.voice_name}`"

                caption = (
                    f"🎬 **Daily Automated AI Shorts**\n\n"
                    f"📌 **{result.title}**\n\n"
                    f"📝 {result.description}\n\n"
                    f"🏷️ {' '.join(result.tags)}\n\n"
                    f"⏱️ Durasi: `{result.duration:.1f} detik`{voice_line}"
                )
                if result.youtube_id:
                    clean_yt_id = result.youtube_id.replace("_", "\\_")
                    caption += f"\n\n▶️ **YouTube Shorts**: https://youtube.com/shorts/{clean_yt_id}"
                elif getattr(result, "youtube_error", None):
                    caption += f"\n\n⚠️ **Status Upload YouTube**: _{result.youtube_error}_"

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
