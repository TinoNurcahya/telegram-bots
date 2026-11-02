import os
import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command

from src.config import settings
from src.services.video_orchestrator import VideoOrchestrator, FullVideoResult
from src.services.voice_service import GoogleTTSQuotaExhaustedError
from src.services.script_gen import SIESTA_CATEGORIES
from src.services.youtube_service import YouTubeService
from src.repositories.video_repo import VideoRepository
from src.bot.keyboards.inline import (
    get_topic_selection_keyboard,
    get_video_actions_keyboard,
    get_main_menu_keyboard,
    get_tts_retry_keyboard
)

logger = logging.getLogger(__name__)

router = Router()
orchestrator = VideoOrchestrator()
youtube_service = YouTubeService()
repo = VideoRepository()

# Global Concurrency Lock to prevent CPU/RAM exhaustion from overlapping renders
_generation_lock = asyncio.Lock()

async def process_video_generation(
    chat_id: int,
    status_msg: Message,
    topic: str = None,
    user_id: int = None
):
    """Executes the pipeline with concurrency protection and progressive status updates."""
    if _generation_lock.locked():
        await status_msg.edit_text(
            "⚠️ **Studio Sedang Memproses Video**\n\n"
            "Saat ini sistem sedang aktif merender video lain. Untuk menjaga stabilitas server dan mencegah crash, "
            "harap tunggu hingga proses sebelumnya selesai (sekitar 1–2 menit).",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    async with _generation_lock:
        try:
            await status_msg.edit_text("🧠 [1/4] Merancang naskah investigasi & fakta menarik via Gemini AI...")

            async def update_progress(msg_text: str):
                try:
                    await status_msg.edit_text(msg_text, parse_mode="Markdown")
                except Exception:
                    pass

            # Video creation pipeline
            result: FullVideoResult = await orchestrator.create_short_video(
                topic=topic,
                user_id=user_id,
                trigger_type="manual",
                auto_upload_youtube=settings.AUTO_UPLOAD_YOUTUBE,
                progress_callback=update_progress
            )

            # Validate file existence and size (< 50MB limit for Telegram Bot API)
            file_size_bytes = os.path.getsize(result.video_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            if file_size_mb > 49.5:
                await status_msg.edit_text(
                    f"⚠️ Ukuran file video ({file_size_mb:.1f} MB) melebihi batas 50MB Telegram Bot API.\n"
                    f"File tersimpan lokal di: `{result.video_path}`"
                )
                return

            format_str = f"{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT} (9:16)"
            voice_line = ""
            if getattr(result, "voice_persona", None) and getattr(result, "voice_name", None):
                voice_line = f"\n🎙️ **Persona**: `{result.voice_persona}` | **Voice**: `{result.voice_name}`"

            caption = (
                f"🎬 **{result.title}**\n\n"
                f"📝 {result.description}\n\n"
                f"🏷️ {' '.join(result.tags)}\n\n"
                f"⏱️ **Durasi**: `{result.duration:.1f} detik` | 📐 **Format**: `{format_str}`{voice_line}"
            )
            if result.youtube_id:
                clean_yt_id = result.youtube_id.replace("_", "\\_")
                caption += f"\n\n▶️ **YouTube Shorts**:\nhttps://youtube.com/shorts/{clean_yt_id}"

            video_file = FSInputFile(result.video_path)
            thumb_input = FSInputFile(result.thumbnail_path) if result.thumbnail_path and os.path.exists(result.thumbnail_path) else None
            await status_msg.answer_video(
                video=video_file,
                caption=caption,
                parse_mode="Markdown",
                thumbnail=thumb_input,
                reply_markup=get_video_actions_keyboard(result.video_id, youtube_id=result.youtube_id)
            )

            # Delete the progress message
            try:
                await status_msg.delete()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error in video generation: {e}", exc_info=True)
            err_msg = str(e)
            is_quota_error = (
                isinstance(e, GoogleTTSQuotaExhaustedError)
                or "GoogleTTSQuotaExhaustedError" in type(e).__name__
                or "429" in err_msg
                or "RESOURCE_EXHAUSTED" in err_msg
                or "quota" in err_msg.lower()
            )
            if is_quota_error:
                await status_msg.edit_text(
                    "⚠️ **Kuota Voice TTS Mencapai Batas**\n\n"
                    "Model suara Google AI Studio sedang mencapai batas kuota (Rate Limit/Harian).\n"
                    "Silakan tunggu sekitar 1 menit lalu coba lagi.",
                    reply_markup=get_tts_retry_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                await status_msg.edit_text(
                    f"❌ **Gagal Membuat Video**\n\n"
                    f"Terjadi kesalahan saat memproses video:\n`{str(e)}`\n\n"
                    f"Silakan coba lagi atau gunakan tombol generate di bawah.",
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="Markdown"
                )

@router.message(Command("generate"))
@router.message(F.text.in_({"🎬 Generate Video (1-Click)", "Generate Video", "🎬 Generate"}))
async def cmd_generate(message: Message):
    # Enforce admin restriction if TARGET_CHAT_ID is configured
    if settings.TARGET_CHAT_ID and settings.TARGET_CHAT_ID != 0:
        if message.from_user.id != settings.TARGET_CHAT_ID and message.chat.id != settings.TARGET_CHAT_ID:
            await message.answer(
                "⛔ **Akses Khusus Pemilik Studio**\n\n"
                "Bot ini dikonfigurasi sebagai Studio Produksi Pribadi. "
                "Perintah pembuatan video hanya diizinkan untuk Admin Studio terdaftar.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )
            return

    # Extract topic if explicitly provided by user, otherwise None for 100% random case
    topic = None
    if message.text and message.text.startswith("/generate"):
        parts = message.text.split(maxsplit=1)
        topic = parts[1].strip() if len(parts) > 1 else None

    status_text = (
        f"⏳ **Sedang menganalisis topik: \"{topic}\"...**"
        if topic
        else "⏳ **Membuka investigasi misteri baru...**\n🎲 Kategori dipilih secara acak..."
    )
    status_msg = await message.answer(status_text, parse_mode="Markdown")
    await process_video_generation(
        chat_id=message.chat.id,
        status_msg=status_msg,
        topic=topic,
        user_id=message.from_user.id
    )

@router.message(Command("topics"))
@router.message(F.text.in_({"🔍 Kategori Kasus", "Kategori Kasus", "Topics"}))
async def cmd_topics(message: Message):
    cats_preview = list(SIESTA_CATEGORIES.items())[:8]
    categories_list = "\n".join([f"• **{name}**: {data['description']}" for name, data in cats_preview])
    text = (
        "🔍 **Kategori Analisis & Dokumenter (100% Acak Saat Digenerate):**\n\n"
        f"{categories_list}\n"
        "• *...dan masih banyak lagi (Total 15+ Kategori Komprehensif)*\n\n"
        "💡 *Klik tombol di bawah untuk langsung mengenerate video kasus acak:* "
    )
    await message.answer(
        text,
        reply_markup=get_topic_selection_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(
    F.data.in_({"btn:generate_instant", "btn:generate_prompt", "btn:trending_topics"}) | F.data.startswith("gen_topic:")
)
async def cb_generate_instant(call: CallbackQuery):
    if settings.TARGET_CHAT_ID and settings.TARGET_CHAT_ID != 0:
        if call.from_user.id != settings.TARGET_CHAT_ID and call.message.chat.id != settings.TARGET_CHAT_ID:
            await call.answer("⛔ Akses Khusus: Hanya Admin Studio yang dapat memicu pembuatan video.", show_alert=True)
            return

    status_text = (
        "⏳ **Membuka investigasi misteri baru...**\n"
        "🎲 Memilih kategori & sudut analisis secara acak..."
    )
    try:
        status_msg = await call.message.edit_text(status_text, parse_mode="Markdown")
    except Exception:
        status_msg = await call.message.answer(status_text, parse_mode="Markdown")
    await call.answer()

    await process_video_generation(
        chat_id=call.message.chat.id,
        status_msg=status_msg,
        topic=None,
        user_id=call.from_user.id
    )

@router.callback_query(F.data.startswith("yt_upload:"))
async def cb_yt_upload(call: CallbackQuery):
    video_id = int(call.data.split(":")[1])
    video_record = await repo.get_video_by_id(video_id)

    if not video_record:
        await call.answer("Video tidak ditemukan.", show_alert=True)
        return

    if not youtube_service.is_configured():
        await call.answer(
            "⚠️ Kredensial YouTube belum dikonfigurasi di server.\n"
            "Simpan file 'client_secrets.json' untuk mengaktifkan upload otomatis.",
            show_alert=True
        )
        return

    await call.answer("🚀 Memulai upload ke YouTube...", show_alert=False)
    progress_msg = await call.message.reply("📡 Mengupload video ke YouTube Shorts...")

    try:
        from pathlib import Path
        import html
        yt_id = await youtube_service.upload_video(
            video_path=Path(video_record["video_path"]),
            title=video_record["title"],
            description=video_record["description"] or "",
            tags=(video_record["tags"] or "").split(),
            privacy_status=settings.YOUTUBE_PRIVACY_STATUS
        )
        if yt_id:
            await repo.update_youtube_id(video_id, yt_id)
            yt_url = f"https://youtube.com/shorts/{yt_id}"
            await progress_msg.edit_text(
                f"✅ <b>Berhasil Diupload ke YouTube Shorts!</b>\n\n"
                f"▶️ Tonton sekarang:\n<a href=\"{yt_url}\">{yt_url}</a>",
                parse_mode="HTML"
            )
            # Update the original video action button to direct YouTube link
            try:
                from src.bot.keyboards.inline import get_video_actions_keyboard
                await call.message.edit_reply_markup(
                    reply_markup=get_video_actions_keyboard(video_id, youtube_id=yt_id)
                )
            except Exception:
                pass
        else:
            await progress_msg.edit_text("❌ Gagal mengautentikasi ke YouTube Data API.")
    except Exception as e:
        import html
        logger.error(f"YouTube upload error: {e}")
        await progress_msg.edit_text(f"❌ Error upload: <code>{html.escape(str(e))}</code>", parse_mode="HTML")
