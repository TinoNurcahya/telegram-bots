import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import settings
from src.repositories.database import init_db
from src.services.video_orchestrator import VideoOrchestrator, FullVideoResult
from src.bot.keyboards.inline import get_video_actions_keyboard

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("production_pipeline")

async def run_pipeline(
    topic: str = None,
    trigger_type: str = "scheduled",
    auto_upload_youtube: bool = True,
    send_telegram: bool = True
):
    logger.info("=" * 60)
    logger.info(f"🚀 Starting AI Shorts Studio Production Pipeline")
    logger.info(f"📌 Trigger: {trigger_type} | Topic: {topic or 'Random Category'}")
    logger.info("=" * 60)

    # 1. Initialize SQLite Database
    await init_db()

    # 2. Initialize Video Orchestrator
    orchestrator = VideoOrchestrator()

    # 3. Create Video End-to-End
    logger.info("🎬 Rendering video with MoviePy + Edge-TTS + Pollinations/Pexels...")
    result: FullVideoResult = await orchestrator.create_short_video(
        topic=topic,
        user_id=settings.TARGET_CHAT_ID if settings.TARGET_CHAT_ID else None,
        trigger_type=trigger_type,
        auto_upload_youtube=auto_upload_youtube
    )

    logger.info(f"✅ Video rendered successfully: {result.video_path}")
    logger.info(f"⏱️ Duration: {result.duration:.1f}s | Title: {result.title}")
    if result.youtube_id:
        logger.info(f"▶️ YouTube Shorts URL: https://youtube.com/shorts/{result.youtube_id}")

    # 4. Broadcast to Telegram if configured
    if send_telegram and settings.BOT_TOKEN and settings.TARGET_CHAT_ID:
        from aiogram import Bot
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.types import FSInputFile

        session = AiohttpSession(timeout=300.0)
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
            session=session
        )
        try:
            logger.info(f"📡 Delivering video to Telegram Chat ID: {settings.TARGET_CHAT_ID}...")
            clean_yt_id = result.youtube_id.replace("_", "\\_") if result.youtube_id else None
            yt_line = f"\n\n▶️ **YouTube Shorts**: https://youtube.com/shorts/{clean_yt_id}" if clean_yt_id else ""
            caption = (
                f"🎬 **AI Shorts Studio — Production Release**\n\n"
                f"📌 **{result.title}**\n\n"
                f"📝 {result.description}\n\n"
                f"🏷️ {' '.join(result.tags)}\n\n"
                f"⏱️ Durasi: `{result.duration:.1f} detik` | 📐 Format: `{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT}`"
                f"{yt_line}"
            )

            video_file = FSInputFile(result.video_path)
            thumb_input = FSInputFile(result.thumbnail_path) if result.thumbnail_path and os.path.exists(result.thumbnail_path) else None

            await bot.send_video(
                chat_id=settings.TARGET_CHAT_ID,
                video=video_file,
                caption=caption,
                parse_mode="Markdown",
                thumbnail=thumb_input,
                reply_markup=get_video_actions_keyboard(result.video_id, youtube_id=result.youtube_id)
            )
            logger.info("✅ Video successfully delivered to Telegram!")
        except Exception as te:
            logger.error(f"Failed to deliver video to Telegram: {te}", exc_info=True)
        finally:
            await bot.session.close()

    logger.info("=" * 60)
    logger.info("🎉 Production Pipeline Execution Finished Successfully!")
    logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="AI Shorts Studio Production Pipeline Runner")
    parser.add_argument("--topic", type=str, default=None, help="Custom topic for the video (optional)")
    parser.add_argument("--trigger", type=str, default="scheduled", help="Trigger type (scheduled, manual, github_action)")
    parser.add_argument("--no-youtube", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram delivery")

    args = parser.parse_args()

    clean_topic = args.topic.strip() if args.topic and args.topic.strip() else None

    asyncio.run(
        run_pipeline(
            topic=clean_topic,
            trigger_type=args.trigger,
            auto_upload_youtube=not args.no_youtube,
            send_telegram=not args.no_telegram
        )
    )

if __name__ == "__main__":
    main()
