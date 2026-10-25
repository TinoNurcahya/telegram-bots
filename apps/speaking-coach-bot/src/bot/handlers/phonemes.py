import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from src.services.user_service import UserService
from src.services.tts_service import TTSService
from src.services.ai_coach_service import (
    get_phoneme_categories,
    get_phoneme_pairs_by_category,
    get_phoneme_pair,
    get_random_phoneme_pair,
    MINIMAL_PAIRS_CATALOG,
)
from src.bot.keyboards.menu import (
    get_phoneme_categories_keyboard,
    get_phoneme_pairs_keyboard,
    get_phoneme_drill_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="phonemes_router")


def build_phoneme_intro_text() -> str:
    return (
        "👄 *Phonetics Clinic & Minimal Pairs Lab*\n\n"
        "Latih artikulasi bunyi bahasa Inggris yang sering membingungkan atau salah diucapkan oleh penutur Indonesia!\n\n"
        "Setiap drill menyajikan sepasang kata kontras (*minimal pair*), panduan fonetik International Phonetic Alphabet (IPA), "
        "petunjuk fisik penempatan lidah/bibir, serta kalimat latihan kontekstual.\n\n"
        "Pilih salah satu kategori fokus fonem di bawah, atau coba pasangan acak:"
    )


def build_drill_card_text(drill: dict) -> str:
    return (
        f"🎯 *Minimal Pair Drill:* **{drill['word_a']}** vs **{drill['word_b']}**\n"
        f"📂 *Kategori:* {drill.get('category_title', '')}\n\n"
        f"🔤 *Panduan Fonetik (IPA):*\n"
        f"🔊 **{drill['word_a']}** ➔ `{drill['ipa_a']}`\n"
        f"🔊 **{drill['word_b']}** ➔ `{drill['ipa_b']}`\n\n"
        f"👄 *Petunjuk Posisi Anatomi Mulut:*\n"
        f"{drill['mouth_tip']}\n\n"
        f"📝 *Kalimat Latihan Kontras:*\n"
        f"> *\"{drill['sentence']}\"*\n\n"
        f"🎙️ *Instruksi Rekaman Voice Note:*\n"
        f"🎧 *(Opsional)* Tekan tombol di bawah untuk mendengarkan audio percontohan.\n"
        f"🎙️ Tahan tombol mikrofon Telegram, lalu ucapkan:\n"
        f"   👉 **\"{drill['word_a']} ... {drill['word_b']}\"** lalu baca kalimat:\n"
        f"   👉 **\"{drill['sentence']}\"**"
    )


@router.message(Command("phonemes"))
async def cmd_phonemes(message: Message) -> None:
    """Open the Phonetics Clinic & Minimal Pairs menu."""
    categories = get_phoneme_categories()
    text = build_phoneme_intro_text()
    await message.reply(
        text=text,
        parse_mode="Markdown",
        reply_markup=get_phoneme_categories_keyboard(categories),
    )


@router.callback_query(F.data == "btn_open_phonemes")
async def cb_open_phonemes(query: CallbackQuery, user_service: UserService) -> None:
    """Callback to display the phoneme category selector."""
    user = query.from_user
    if user:
        await user_service.clear_active_phoneme_drill(user.id)

    categories = get_phoneme_categories()
    text = build_phoneme_intro_text()

    if query.message:
        try:
            await query.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_categories_keyboard(categories),
            )
        except Exception:
            await query.message.answer(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_categories_keyboard(categories),
            )
    await query.answer()


@router.callback_query(F.data.startswith("phoneme_cat:"))
async def cb_phoneme_category(query: CallbackQuery, user_service: UserService) -> None:
    """Display minimal pairs within a selected phoneme category."""
    user = query.from_user
    if user:
        await user_service.clear_active_phoneme_drill(user.id)

    cat_id = query.data.split(":")[1]
    cat_data = MINIMAL_PAIRS_CATALOG.get(cat_id)
    if not cat_data:
        await query.answer("Kategori tidak ditemukan.", show_alert=True)
        return

    pairs = get_phoneme_pairs_by_category(cat_id)
    text = (
        f"{cat_data['title']}\n\n"
        f"ℹ️ {cat_data['description']}\n\n"
        "Pilih salah satu pasangan kata di bawah untuk memulai drill:"
    )

    if query.message:
        try:
            await query.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_pairs_keyboard(cat_id, pairs),
            )
        except Exception:
            await query.message.answer(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_pairs_keyboard(cat_id, pairs),
            )
    await query.answer()


@router.callback_query(F.data.startswith("phoneme_drill:"))
async def cb_phoneme_drill(query: CallbackQuery, user_service: UserService) -> None:
    """Activate a specific phoneme drill and present instructions."""
    user = query.from_user
    user_id = user.id if user else 0

    pair_id = query.data.split(":")[1]
    drill = get_phoneme_pair(pair_id)
    if not drill:
        await query.answer("Pasangan fonem tidak ditemukan.", show_alert=True)
        return

    # Store active phoneme challenge in user session
    await user_service.reset_all_active_drills(user_id)
    await user_service.set_active_phoneme_drill(user_id, drill)

    text = build_drill_card_text(drill)
    if query.message:
        try:
            await query.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_drill_keyboard(pair_id),
            )
        except Exception:
            await query.message.answer(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_drill_keyboard(pair_id),
            )
    await query.answer("Latihan fonem aktif! Rekam suaramu.")


@router.callback_query(F.data == "phoneme_random")
async def cb_phoneme_random(query: CallbackQuery, user_service: UserService) -> None:
    """Activate a random minimal pair challenge."""
    user = query.from_user
    user_id = user.id if user else 0

    drill = get_random_phoneme_pair()
    await user_service.reset_all_active_drills(user_id)
    await user_service.set_active_phoneme_drill(user_id, drill)

    text = build_drill_card_text(drill)
    if query.message:
        try:
            await query.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_drill_keyboard(drill["id"]),
            )
        except Exception:
            await query.message.answer(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_drill_keyboard(drill["id"]),
            )
    await query.answer("Pasangan acak dipilih! Rekam suaramu.")


@router.callback_query(F.data.startswith("phoneme_audio:"))
async def cb_phoneme_audio(
    query: CallbackQuery,
    user_service: UserService,
    tts_service: TTSService,
) -> None:
    """Synthesize and send listening demonstration audio on demand."""
    pair_id = query.data.split(":")[1]
    drill = get_phoneme_pair(pair_id)
    if not drill:
        await query.answer("Data fonem tidak ditemukan.", show_alert=True)
        return

    user = query.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)
    voice = profile.get("tts_voice") or "en-US-JennyNeural"
    speed = profile.get("tts_speed") or "+0%"

    await query.answer("Synthesizing audio demonstration...")

    audio_bytes = await tts_service.synthesize_phoneme_contrast_audio(
        word_a=drill["word_a"],
        word_b=drill["word_b"],
        sentence=drill["sentence"],
        voice=voice,
        rate=speed,
    )

    if audio_bytes and query.message:
        voice_file = BufferedInputFile(
            file=audio_bytes,
            filename=f"phoneme_{pair_id}.mp3",
        )
        caption = (
            f"🎧 *Audio Contoh Pengucapan:* **{drill['word_a']}** (`{drill['ipa_a']}`) vs "
            f"**{drill['word_b']}** (`{drill['ipa_b']}`)\n\n"
            f"Dengarkan kontrasnya, lalu rekam suaramu menirukannya!"
        )
        await query.message.answer_voice(
            voice=voice_file,
            caption=caption,
            parse_mode="Markdown",
        )
    elif query.message:
        await query.message.answer(
            "⚠️ Audio contoh percontohan sedang tidak tersedia. "
            "Anda dapat langsung membaca panduan IPA & posisi mulut di atas lalu rekam suara Anda!",
            parse_mode="Markdown",
        )


@router.callback_query(F.data == "phoneme_cancel")
async def cb_phoneme_cancel(query: CallbackQuery, user_service: UserService) -> None:
    """Cancel active phoneme challenge and return to phoneme category menu."""
    user = query.from_user
    if user:
        await user_service.clear_active_phoneme_drill(user.id)

    categories = get_phoneme_categories()
    text = (
        "❌ *Latihan fonem dibatalkan.*\n\n"
        + build_phoneme_intro_text()
    )

    if query.message:
        try:
            await query.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_categories_keyboard(categories),
            )
        except Exception:
            await query.message.answer(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_phoneme_categories_keyboard(categories),
            )
    await query.answer("Latihan dibatalkan.")
