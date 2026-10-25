import logging
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from src.services.user_service import UserService
from src.services.tts_service import TTSService
from src.services.ai_coach_service import get_tenses_catalog, get_tense_detail
from src.bot.keyboards.menu import (
    get_tenses_selection_keyboard,
    get_tense_card_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="tenses_router")


def build_tenses_intro_text() -> str:
    return (
        "⏳ **Klinik Latihan English Tenses (Speaking Gym)**\n\n"
        "Kuasai tenses bahasa Inggris bukan hanya dengan menghafal rumus, melainkan dengan **mempraktikkannya secara aktif lewat rekaman suara**!\n\n"
        "🌟 **Cara Berlatih:**\n"
        "1️⃣ Pilih salah satu kategori tenses di bawah.\n"
        "2️⃣ Pelajari rumus ringkas dan dengarkan contoh pengucapan audio native.\n"
        "3️⃣ Tahan tombol mikrofon (🎙️) dan jawab skenario speaking yang diberikan.\n"
        "4️⃣ AI Coach akan mengevaluasi ketepatan penggunaan tenses Anda dan membalas dengan audio interaktif!\n\n"
        "Silakan pilih tenses yang ingin Anda latih hari ini:"
    )


def build_tense_card_text(item: dict) -> str:
    return (
        f"⏳ **Klinik Tenses: {item['icon']} {item['title']}**\n\n"
        f"💡 **Konsep & Fungsi:**\n"
        f"{item['concept']}\n\n"
        f"📐 **Rumus / Formula Grammar:**\n"
        f"`{item['formula']}`\n\n"
        f"📝 **Contoh Kalimat Native:**\n"
        f"> *\"{item['example_sentence']}\"*\n\n"
        f"🗣️ **Tugas Berbicara (Speaking Scenario):**\n"
        f"> *\"{item['speaking_scenario']}\"*\n\n"
        f"🎙️ **Instruksi:**\n"
        f"Tekan dan tahan tombol mikrofon (🎙️) di Telegram, lalu jawab skenario di atas dengan menerapkan struktur **{item['title']}** (bicara 15–45 detik)!"
    )


@router.message(Command("tenses"))
async def cmd_tenses(message: Message) -> None:
    """Open the Tenses Speaking Gym catalog menu."""
    text = build_tenses_intro_text()
    await message.answer(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_tenses_selection_keyboard(),
    )


@router.callback_query(F.data == "btn_open_tenses")
async def cb_open_tenses(callback: CallbackQuery) -> None:
    """Handle open tenses catalog from menu buttons."""
    await callback.answer()
    text = build_tenses_intro_text()
    if callback.message:
        await callback.message.edit_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=get_tenses_selection_keyboard(),
        )


@router.callback_query(F.data.startswith("tense_drill:"))
async def cb_tense_drill_select(
    callback: CallbackQuery, user_service: UserService
) -> None:
    """User selected a specific tense to drill."""
    tense_id = callback.data.split(":")[1]
    item = get_tense_detail(tense_id)
    if not item:
        await callback.answer("Kategori tenses tidak ditemukan.", show_alert=True)
        return

    user_id = callback.from_user.id
    # Reset any previous active mode (IELTS, Shadowing, Phonemes) to prevent routing conflicts
    await user_service.reset_all_active_drills(user_id)
    # Set this tense as the active target drill for the user's upcoming voice note
    await user_service.set_active_tense_drill(user_id, item)
    await callback.answer(f"Mode aktif: {item['title']}")

    card_text = build_tense_card_text(item)
    if callback.message:
        await callback.message.edit_text(
            text=card_text,
            parse_mode="Markdown",
            reply_markup=get_tense_card_keyboard(tense_id),
        )


@router.callback_query(F.data.startswith("tense_audio:"))
async def cb_tense_audio(
    callback: CallbackQuery,
    user_service: UserService,
    tts_service: TTSService,
) -> None:
    """Generate and deliver sample native audio for the selected tense."""
    tense_id = callback.data.split(":")[1]
    item = get_tense_detail(tense_id)
    if not item:
        await callback.answer("Data tenses tidak ditemukan.", show_alert=True)
        return

    await callback.answer("Membuat audio contoh native...")
    user_id = callback.from_user.id
    profile = await user_service.get_user_profile(user_id)
    tts_voice = profile.get("tts_voice", "en-US-JennyNeural")
    tts_speed = profile.get("tts_speed", "+0%")

    sample_sentence = item["example_sentence"]
    try:
        audio_stream = await tts_service.synthesize_speech_stream(
            text=sample_sentence,
            voice=tts_voice,
            rate=tts_speed,
        )
        audio_bytes = audio_stream.getvalue()
        voice_file = BufferedInputFile(
            file=audio_bytes,
            filename=f"tense_{tense_id}.ogg",
        )
        if callback.message:
            await callback.message.reply_voice(
                voice=voice_file,
                caption=f"🔊 *Contoh Pengucapan ({item['title']}):*\n\"{sample_sentence}\"",
                parse_mode="Markdown",
            )
    except Exception as err:
        logger.error("Failed to synthesize tense audio example: %s", err)
        if callback.message:
            await callback.message.answer(
                "⚠️ Gagal membuat audio percontohan saat ini. Silakan coba kembali."
            )


@router.callback_query(F.data == "tense_cancel")
async def cb_tense_cancel(
    callback: CallbackQuery, user_service: UserService
) -> None:
    """Cancel active tense drill and return to selection catalog."""
    user_id = callback.from_user.id
    await user_service.clear_active_tense_drill(user_id)
    await callback.answer("Latihan tenses dinonaktifkan.")
    text = build_tenses_intro_text()
    if callback.message:
        await callback.message.edit_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=get_tenses_selection_keyboard(),
        )
