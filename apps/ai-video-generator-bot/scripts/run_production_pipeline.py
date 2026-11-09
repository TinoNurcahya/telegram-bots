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

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
    send_telegram: bool = True,
    video_format: str = "shorts"
):
    is_longform = (video_format or "shorts").lower() == "longform"
    logger.info("=" * 60)
    logger.info(f"🚀 Starting AI Shorts Studio Production Pipeline ({video_format.upper()})")
    logger.info(f"📌 Trigger: {trigger_type} | Format: {video_format} | Topic: {topic or 'Rotated Category'}")
    logger.info("=" * 60)

    # 1. Initialize SQLite Database
    await init_db()

    # 2. Initialize Video Orchestrator
    orchestrator = VideoOrchestrator()

    # 3. Create Video End-to-End
    logger.info(f"🎬 Rendering {video_format} video with MoviePy + Google AI Studio TTS...")
    result: FullVideoResult = await orchestrator.create_short_video(
        topic=topic,
        user_id=settings.TARGET_CHAT_ID if settings.TARGET_CHAT_ID else None,
        trigger_type=trigger_type,
        auto_upload_youtube=auto_upload_youtube,
        video_format=video_format
    )

    logger.info(f"✅ Video rendered successfully: {result.video_path}")
    logger.info(f"⏱️ Duration: {result.duration:.1f}s | Title: {result.title}")
    if result.youtube_id:
        yt_url = f"https://youtube.com/watch?v={result.youtube_id}" if is_longform else f"https://youtube.com/shorts/{result.youtube_id}"
        logger.info(f"▶️ YouTube URL: {yt_url}")
    elif getattr(result, "youtube_error", None):
        logger.warning(f"⚠️ YouTube Upload Skipped/Failed: {result.youtube_error}")

    # 4. Broadcast to Telegram if configured
    clean_bot_token = (settings.BOT_TOKEN or "").strip().strip("'\"").replace(" ", "").replace("\r", "").replace("\n", "")
    if send_telegram and clean_bot_token and settings.TARGET_CHAT_ID:
        from aiogram import Bot
        from aiogram.client.session.aiohttp import AiohttpSession
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        from aiogram.types import FSInputFile

        session = AiohttpSession(timeout=300.0)
        bot = Bot(
            token=clean_bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
            session=session
        )
        try:
            logger.info(f"📡 Delivering {video_format} video to Telegram Chat ID: {settings.TARGET_CHAT_ID}...")
            clean_yt_id = result.youtube_id.replace("_", "\\_") if result.youtube_id else None
            if clean_yt_id:
                if is_longform:
                    yt_line = f"\n\n▶️ **YouTube Documentary (16:9)**: https://youtube.com/watch?v={clean_yt_id}"
                else:
                    yt_line = f"\n\n▶️ **YouTube Shorts**: https://youtube.com/shorts/{clean_yt_id}"
            elif getattr(result, "youtube_error", None):
                yt_line = f"\n\n⚠️ **Status Upload YouTube**: _{result.youtube_error}_"
            else:
                yt_line = ""
            voice_line = ""
            if getattr(result, "voice_persona", None) and getattr(result, "voice_name", None):
                voice_line = f"\n🎙️ **Persona**: `{result.voice_persona}` | **Voice**: `{result.voice_name}`"

            res_str = f"{settings.LONGFORM_WIDTH}x{settings.LONGFORM_HEIGHT} (16:9)" if is_longform else f"{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT} (9:16)"
            header_label = "🎥 **AI Studio — Full Documentary (16:9)**" if is_longform else "🎬 **AI Shorts Studio — Production Release**"
            short_desc = result.description[:450] + "..." if len(result.description) > 450 else result.description
            caption = (
                f"{header_label}\n\n"
                f"📌 **{result.title}**\n\n"
                f"📝 {short_desc}\n\n"
                f"🏷️ {' '.join(result.tags)}\n\n"
                f"⏱️ Durasi: `{result.duration:.1f} detik` | 📐 Format: `{res_str}`"
                f"{voice_line}"
                f"{yt_line}"
            )

            file_size_mb = os.path.getsize(result.video_path) / (1024 * 1024) if os.path.exists(result.video_path) else 0
            thumb_input = FSInputFile(result.thumbnail_path) if result.thumbnail_path and os.path.exists(result.thumbnail_path) else None

            if file_size_mb <= 49.0:
                video_file = FSInputFile(result.video_path)
                await bot.send_video(
                    chat_id=settings.TARGET_CHAT_ID,
                    video=video_file,
                    caption=caption,
                    parse_mode="Markdown",
                    thumbnail=thumb_input,
                    reply_markup=get_video_actions_keyboard(result.video_id, youtube_id=result.youtube_id)
                )
            elif thumb_input:
                await bot.send_photo(
                    chat_id=settings.TARGET_CHAT_ID,
                    photo=thumb_input,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=get_video_actions_keyboard(result.video_id, youtube_id=result.youtube_id)
                )
            else:
                await bot.send_message(
                    chat_id=settings.TARGET_CHAT_ID,
                    text=caption,
                    parse_mode="Markdown",
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
    parser.add_argument("--format", type=str, default="shorts", choices=["shorts", "longform"], help="Video format: shorts (9:16) or longform (16:9)")
    parser.add_argument("--no-youtube", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram delivery")

    args = parser.parse_args()

    clean_topic = args.topic.strip() if args.topic and args.topic.strip() else None

    asyncio.run(
        run_pipeline(
            topic=clean_topic,
            trigger_type=args.trigger,
            auto_upload_youtube=not args.no_youtube,
            send_telegram=not args.no_telegram,
            video_format=args.format
        )
    )

if __name__ == "__main__":
    main()
