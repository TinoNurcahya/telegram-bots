import os
import sys
import json
import shutil
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
from src.services.youtube_service import YouTubeService
from src.bot.keyboards.inline import get_video_actions_keyboard

PENDING_DIR = BASE_DIR / "storage" / "pending_uploads"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("production_pipeline")

async def flush_pending_uploads(yt_service: YouTubeService, clean_bot_token: str) -> int:
    """
    Uploads any previously generated videos that were queued in storage/pending_uploads
    due to daily YouTube API quota limits, so no rendered video is ever wasted.
    """
    if not PENDING_DIR.exists() or not yt_service.is_configured():
        return 0

    meta_files = sorted(PENDING_DIR.glob("*.json"))
    if not meta_files:
        return 0

    uploaded_count = 0
    for meta_path in meta_files:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            video_file = PENDING_DIR / meta["video_filename"]
            thumb_file = (PENDING_DIR / meta["thumb_filename"]) if meta.get("thumb_filename") else None
            if not video_file.exists():
                meta_path.unlink(missing_ok=True)
                continue

            is_longform = meta.get("video_format") == "longform"
            logger.info(f"🔄 Attempting deferred YouTube upload for queued video: {meta.get('title')}")
            yt_id = await yt_service.upload_video(
                video_path=video_file,
                title=meta["title"],
                description=meta["description"],
                tags=meta.get("tags", ["#shorts", "#mystery"]),
                thumbnail_path=thumb_file if (thumb_file and thumb_file.exists()) else None,
                privacy_status=settings.YOUTUBE_PRIVACY_STATUS,
                is_short=not is_longform
            )
            if yt_id:
                uploaded_count += 1
                yt_url = f"https://youtube.com/watch?v={yt_id}" if is_longform else f"https://youtube.com/shorts/{yt_id}"
                logger.info(f"✅ Queued video successfully uploaded to YouTube: {yt_url}")

                # Notify user on Telegram
                if clean_bot_token and settings.TARGET_CHAT_ID:
                    from aiogram import Bot
                    bot = Bot(token=clean_bot_token)
                    try:
                        await bot.send_message(
                            chat_id=settings.TARGET_CHAT_ID,
                            text=(
                                f"✅ <b>Video Antrean Berhasil Diupload ke YouTube!</b>\n\n"
                                f"📌 <b>{meta['title']}</b>\n"
                                f"▶️ <a href=\"{yt_url}\">{yt_url}</a>"
                            ),
                            parse_mode="HTML"
                        )
                    except Exception as te:
                        logger.warning(f"Failed to send deferred upload notice to Telegram: {te}")
                    finally:
                        await bot.session.close()

                # Remove from pending queue
                video_file.unlink(missing_ok=True)
                if thumb_file and thumb_file.exists():
                    thumb_file.unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
            else:
                logger.warning(f"Deferred upload still blocked ({yt_service.last_error}). Keeping in queue for next window.")
                break
        except Exception as e:
            logger.warning(f"Error processing pending upload {meta_path}: {e}")

    return uploaded_count


def save_to_pending_queue(result: FullVideoResult) -> None:
    """Saves a rendered video and its metadata to storage/pending_uploads when YouTube quota is full."""
    try:
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        src_video = Path(result.video_path)
        if not src_video.exists():
            return

        dest_video = PENDING_DIR / src_video.name
        if src_video.resolve() != dest_video.resolve():
            shutil.copy2(src_video, dest_video)

        thumb_name = None
        if result.thumbnail_path and os.path.exists(result.thumbnail_path):
            src_thumb = Path(result.thumbnail_path)
            dest_thumb = PENDING_DIR / src_thumb.name
            if src_thumb.resolve() != dest_thumb.resolve():
                shutil.copy2(src_thumb, dest_thumb)
            thumb_name = dest_thumb.name

        meta = {
            "title": result.title,
            "description": result.description,
            "tags": result.tags,
            "video_format": getattr(result, "video_format", "shorts"),
            "video_filename": dest_video.name,
            "thumb_filename": thumb_name,
        }
        meta_path = PENDING_DIR / f"{src_video.stem}.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"📥 Video saved to pending YouTube upload queue: {meta_path}")
    except Exception as e:
        logger.warning(f"Could not save video to pending queue: {e}")


async def retry_upload_from_telegram(file_id: str, caption: str = "", reply_msg_id: int = None) -> None:
    """
    Downloads an already-rendered video directly from Telegram by file_id and uploads it to YouTube
    without wasting time or quota re-generating the video.
    """
    clean_bot_token = (settings.BOT_TOKEN or "").strip().strip("'\"").replace(" ", "").replace("\r", "").replace("\n", "")
    if not clean_bot_token or not settings.TARGET_CHAT_ID:
        logger.error("BOT_TOKEN or TARGET_CHAT_ID missing for Telegram file_id retry.")
        return

    from aiogram import Bot
    from aiogram.client.session.aiohttp import AiohttpSession

    session = AiohttpSession(timeout=300.0)
    bot = Bot(token=clean_bot_token, session=session)
    yt_service = YouTubeService()

    try:
        temp_dir = settings.abs_temp_dir / "tg_retry"
        temp_dir.mkdir(parents=True, exist_ok=True)
        local_mp4 = temp_dir / "retry_video.mp4"

        logger.info(f"📥 Downloading existing video from Telegram (file_id={file_id[:20]}...)...")
        tg_file = await bot.get_file(file_id)
        await bot.download_file(tg_file.file_path, destination=local_mp4)

        lines = [ln.strip() for ln in (caption or "").splitlines() if ln.strip()]
        title = "Mystery & Science Documentary #Shorts"
        for ln in lines:
            if not ln.startswith(("🎬", "🎥", "⏱️", "🎙️", "⚠️", "🏷️")):
                title = ln.lstrip("📌* ").strip()
                break
            elif ln.startswith("📌"):
                title = ln.lstrip("📌* ").strip()
                break

        is_longform = "1280x720" in (caption or "") or "16:9" in (caption or "")
        description = caption or title
        tags = ["#documentary", "#mystery", "#science"] if is_longform else ["#shorts", "#mystery", "#documentary", "#science"]

        yt_id = await yt_service.upload_video(
            video_path=local_mp4,
            title=title[:100],
            description=description,
            tags=tags,
            privacy_status=settings.YOUTUBE_PRIVACY_STATUS,
            is_short=not is_longform
        )

        if yt_id:
            yt_url = f"https://youtube.com/watch?v={yt_id}" if is_longform else f"https://youtube.com/shorts/{yt_id}"
            await bot.send_message(
                chat_id=settings.TARGET_CHAT_ID,
                text=(
                    f"✅ <b>Berhasil Diupload ke YouTube!</b>\n\n"
                    f"📌 <b>{title}</b>\n"
                    f"▶️ Tonton sekarang:\n<a href=\"{yt_url}\">{yt_url}</a>"
                ),
                parse_mode="HTML",
                reply_to_message_id=reply_msg_id if reply_msg_id else None
            )
        else:
            err = yt_service.last_error or "Gagal mengunggah ke YouTube."
            await bot.send_message(
                chat_id=settings.TARGET_CHAT_ID,
                text=f"⚠️ <b>Upload YouTube Tertunda:</b>\n<i>{err}</i>\n\nSilakan klik tombol upload lagi setelah kuota harian YouTube reset (pukul 15:00 WIB).",
                parse_mode="HTML",
                reply_to_message_id=reply_msg_id if reply_msg_id else None
            )
    finally:
        await bot.session.close()


async def run_pipeline(
    topic: str = None,
    trigger_type: str = "scheduled",
    auto_upload_youtube: bool = True,
    send_telegram: bool = True,
    video_format: str = "shorts"
):
    is_longform = (video_format or "shorts").lower() == "longform"
    clean_bot_token = (settings.BOT_TOKEN or "").strip().strip("'\"").replace(" ", "").replace("\r", "").replace("\n", "")

    logger.info("=" * 60)
    logger.info(f"🚀 Starting AI Shorts Studio Production Pipeline ({video_format.upper()})")
    logger.info(f"📌 Trigger: {trigger_type} | Format: {video_format} | Topic: {topic or 'Rotated Category'}")
    logger.info("=" * 60)

    # 1. Initialize SQLite Database & Flush any Pending YouTube Uploads from earlier runs
    await init_db()
    orchestrator = VideoOrchestrator()
    if auto_upload_youtube:
        await flush_pending_uploads(orchestrator.youtube_service, clean_bot_token)

    # 2. Create Video End-to-End
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
        if auto_upload_youtube:
            save_to_pending_queue(result)
            result.youtube_error = (
                f"{result.youtube_error} (Video sudah disimpan di antrean & akan otomatis diupload pada jadwal berikutnya / klik tombol di bawah)"
            )

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
    parser.add_argument("--retry-file-id", type=str, default=None, help="Telegram file_id to upload directly to YouTube without re-rendering")
    parser.add_argument("--retry-caption", type=str, default=None, help="Original Telegram caption for retry upload")
    parser.add_argument("--retry-msg-id", type=int, default=None, help="Original Telegram message_id to reply to")
    parser.add_argument("--no-youtube", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--no-telegram", action="store_true", help="Skip Telegram delivery")

    args = parser.parse_args()

    if args.retry_file_id and args.retry_file_id.strip():
        asyncio.run(
            retry_upload_from_telegram(
                file_id=args.retry_file_id.strip(),
                caption=args.retry_caption or "",
                reply_msg_id=args.retry_msg_id
            )
        )
        return

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
