import io
import logging
from typing import Optional, Any
from aiogram import Router, F, Bot
from aiogram.types import Message

from src.services.user_service import UserService
from src.services.ai_coach_service import AICoachService
from src.services.tts_service import TTSService
from src.worker.dispatcher import VoiceJobDispatcher
from src.worker.arq_worker import execute_voice_job

logger = logging.getLogger(__name__)
router = Router(name="coach_voice_router")


@router.message(F.voice | F.audio)
async def handle_voice_message(
    message: Message,
    bot: Bot,
    user_service: UserService,
    ai_coach_service: AICoachService,
    tts_service: TTSService,
    voice_dispatcher: Optional[VoiceJobDispatcher] = None,
    dialogue_service: Optional[Any] = None,
) -> None:
    """Handle incoming voice note, routing through VoiceJobDispatcher (Arq Queue or In-Process fallback)."""
    user = message.from_user
    user_id = user.id if user else 0

    profile = await user_service.get_user_profile(user_id)
    scenario = profile.get("active_scenario", "Free Conversation")
    active_shadow_target = profile.get("active_shadow_target") or ""
    active_ielts_session = await user_service.get_active_ielts_session(user_id)
    active_phoneme_drill = await user_service.get_active_phoneme_drill(user_id)
    active_tense_drill = await user_service.get_active_tense_drill(user_id)

    dialogue_history = []
    if dialogue_service:
        try:
            dialogue_history = await dialogue_service.get_history(user_id, scenario=scenario, max_turns=10)
        except Exception as e:
            logger.warning("Could not pre-fetch dialogue history: %s", e)

    voice = message.voice or message.audio
    if not voice:
        await message.reply("⚠️ Format audio tidak dikenali. Silakan kirim Voice Note Telegram.")
        return

    duration = getattr(voice, "duration", 0) or 0
    file_size = getattr(voice, "file_size", 0) or 0

    if duration < 1:
        await message.reply(
            "⚠️ **Rekaman Terlalu Singkat:**\n"
            "Audio di bawah 1 detik tidak dapat dianalisis. Tahan tombol mikrofon (🎙️) dan berbicaralah minimal 2–3 kata!",
            parse_mode="Markdown",
        )
        return

    if duration > 90:
        await message.reply(
            "⚠️ **Durasi Terlalu Panjang:**\n"
            f"Durasi rekaman Anda adalah {duration} detik. Mohon batasi durasi suara maksimal 90 detik (1.5 menit) per latihan agar evaluasi AI tetap fokus dan akurat.",
            parse_mode="Markdown",
        )
        return

    if file_size > 10 * 1024 * 1024:
        await message.reply(
            "⚠️ **Ukuran File Melebihi Batas:**\n"
            "Batas maksimal file audio adalah 10 MB. Mohon kirim voice note langsung dari aplikasi Telegram.",
            parse_mode="Markdown",
        )
        return

    status_msg = await message.reply("🎧 *Analyzing your speech with Gemini AI...*", parse_mode="Markdown")

    try:
        file_id = voice.file_id

        # Download voice file directly into in-memory buffer
        audio_buffer = io.BytesIO()
        await bot.download(file_id, destination=audio_buffer)
        audio_bytes = audio_buffer.getvalue()
        mime_type = voice.mime_type or "audio/ogg"

        job_data = {
            "chat_id": message.chat.id,
            "user_id": user_id,
            "status_message_id": status_msg.message_id,
            "audio_bytes": audio_bytes,
            "mime_type": mime_type,
            "duration": duration,
            "target_level": profile.get("target_level", "Intermediate"),
            "scenario": scenario,
            "tts_voice": profile.get("tts_voice", "en-US-JennyNeural"),
            "tts_speed": profile.get("tts_speed", "+0%"),
            "active_shadow_target": active_shadow_target,
            "active_ielts_session": active_ielts_session,
            "active_phoneme_drill": active_phoneme_drill,
            "active_tense_drill": active_tense_drill,
            "dialogue_history": dialogue_history,
        }

        if voice_dispatcher:
            await voice_dispatcher.dispatch(
                job_data=job_data,
                bot=bot,
                user_service=user_service,
                ai_coach_service=ai_coach_service,
                tts_service=tts_service,
                dialogue_service=dialogue_service,
            )
        else:
            await execute_voice_job(
                job_data=job_data,
                bot=bot,
                user_service=user_service,
                ai_coach_service=ai_coach_service,
                tts_service=tts_service,
                dialogue_service=dialogue_service,
            )

    except Exception as err:
        logger.error("Failed to process voice note: %s", err, exc_info=True)
        await status_msg.edit_text(
            "⚠️ **Evaluation Error:**\n\n"
            "Could not complete audio analysis. Please verify your `GEMINI_API_KEY` in `.env` "
            "or check if your voice note was too quiet/short. Try sending another voice note!",
            parse_mode="Markdown",
        )
