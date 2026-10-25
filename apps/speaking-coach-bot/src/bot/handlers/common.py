import logging
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from src.services.user_service import UserService
from src.services.ai_coach_service import AICoachService
from src.services.tts_service import TTSService, SPEED_PRESETS
from src.services.dialogue_service import DialogueService, SCENARIO_OPENINGS
from src.bot.keyboards.menu import (
    get_main_menu_keyboard,
    get_level_selection_keyboard,
    get_scenario_selection_keyboard,
    get_voice_selection_keyboard,
    get_speed_selection_keyboard,
    get_shadowing_control_keyboard,
    get_referral_keyboard,
    get_progress_navigation_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="coach_common_router")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user_service: UserService,
    bot: Bot,
    command: Optional[CommandObject] = None,
) -> None:
    """Send welcome greeting with streak status, processing referral if present."""
    user = message.from_user
    user_id = user.id if user else 0

    referral_banner = ""
    if command and command.args and command.args.startswith("ref_"):
        try:
            inviter_id = int(command.args.replace("ref_", ""))
            ref_result = await user_service.process_referral(inviter_id=inviter_id, invitee_id=user_id)
            if ref_result and ref_result.get("success"):
                referral_banner = (
                    "🎁 **BONUS SAMBUTAN REFERRAL!**\n"
                    "Anda bergabung melalui link undangan teman. Anda mendapatkan:\n"
                    "✨ **+3 Kuota Suara Tambahan** (Total 13 kuota gratis hari ini!)\n"
                    "⚡ **+25 XP Bonus Sambutan**\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
                try:
                    inviter_notify = (
                        "🎉 **Teman Baru Bergabung via Link Referral Anda!**\n\n"
                        f"Kawan Anda **{user.first_name}** baru saja mulai latihan berbicara!\n\n"
                        "🎁 **Hadiah yang Telah Masuk ke Akun Anda:**\n"
                        "✨ +3 Kuota Suara Tambahan Hari Ini\n"
                        "❄️ +1 Tiket Pelindung Streak (Streak Freeze)\n"
                        "⚡ +50 XP Bonus Pengundang\n\n"
                        "Terima kasih telah menyebarkan semangat latihan bahasa Inggris!"
                    )
                    await bot.send_message(chat_id=inviter_id, text=inviter_notify, parse_mode="Markdown")
                except Exception as notify_err:
                    logger.warning("Could not notify inviter %s: %s", inviter_id, notify_err)
        except (ValueError, TypeError):
            pass

    profile = await user_service.get_user_profile(user_id)
    level = profile.get("target_level", "Intermediate")
    scenario = profile.get("active_scenario", "Free Conversation")
    streak = profile.get("current_streak", 0)
    xp = profile.get("total_xp", 0)
    name = user.first_name if user else "Friend"

    streak_badge = f"🔥 `{streak} Days Streak`" if streak > 0 else "🔥 `Start Today's Streak!`"

    text = (
        f"{referral_banner}"
        f"🎙️ **Halo {name}, Selamat datang di AI Speaking Coach!**\n\n"
        "Tingkatkan kelancaran dan rasa percaya diri berbicara bahasa Inggris Anda bersama AI Coach pribadi yang siap mendengarkan 24/7 dan merespons dengan audio suara *native speaker*!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏆 **STATUS BELAJAR ANDA**\n"
        f"🔥 **Streak Harian:** {streak_badge}\n"
        f"⚡ **Experience Points:** `{xp} XP`\n"
        f"🎯 **Target Kemahiran:** `{level}` *(ubah via `/level`)*\n"
        f"🎭 **Skenario Percakapan:** `{scenario}` *(ubah via `/scenario`)*\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎙️ **CARA MULAI LATIHAN LANGSUNG**\n"
        "Anda **tidak perlu mengetik perintah apapun** untuk mulai berbicara!\n"
        "🎙️ Tahan tombol **Voice Note (🎙️)** di Telegram.\n"
        "🗣️ Bicaralah dalam bahasa Inggris selama 15–60 detik.\n"
        "✨ Bot akan langsung menganalisis rekaman Anda:\n"
        "   📝 **Transkrip teks** akurat dari apa yang Anda katakan\n"
        "   📊 **Skor Kelancaran & Estimasi IELTS Band / CEFR**\n"
        "   🛠️ **Koreksi Tata Bahasa (Grammar Slips)** & saran kosakata alami\n"
        "   🔊 **Balasan Suara AI** yang melanjutkan obrolan secara interaktif!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **MODE & FITUR LATIHAN LENGKAP**\n"
        "Ketik tanda **`/`** di kolom pesan atau klik tombol **[ Menu ]** untuk mencoba:\n\n"
        "🎓 `/mock_ielts` — **Simulasi Ujian Resmi IELTS Speaking**\n"
        "  Simulasi 3 bagian (Part 1, Part 2 cue card, Part 3) lengkap dengan examiner scorecard (FC, LR, GRA, PR).\n\n"
        "🎧 `/shadow` — **Latihan Shadowing & Intonasi**\n"
        "  Dengarkan kalimat native speaker, lalu tiru pengucapan dan temponya untuk mengasah aksen alami.\n\n"
        "👄 `/phonemes` — **Klinik Fonetik & Minimal Pairs**\n"
        "  Latihan membedakan pasangan bunyi yang rawan tertukar (seperti `/θ/` vs `/s/`, `/p/` vs `/f/`, `/l/` vs `/r/`) beserta tips posisi lidah & bibir.\n\n"
        "⏳ `/tenses` — **Klinik Latihan Tenses Aktif**\n"
        "  Kuasai tenses (Present Continuous, Past, Future, Conditionals, dll) dengan kartu rumus, audio native, dan evaluasi akurasi AI.\n\n"
        "🎭 `/scenario` — **Simulasi Situasi Nyata (Roleplay)**\n"
        "  Latihan wawancara kerja (*Job Interview*), pesan kopi di cafe, imigrasi bandara, atau *tech standup*.\n\n"
        "📖 `/review` — **Bank Kosakata & Grammar Pribadi**\n"
        "  Arsip otomatis kesalahan grammar dan kosakata baru dari voice note Anda untuk dipelajari ulang.\n\n"
        "💡 `/topic` — **Topik Percakapan Harian**\n"
        "  Dapatkan pertanyaan pemantik yang disesuaikan dengan tingkat kemahiran Anda.\n\n"
        "⏰ `/remind` — **Pengingat Harian & Pelindung Streak**\n"
        "  Atur jadwal pengingat ramah agar api streak 🔥 harian Anda tidak padam.\n\n"
        "📊 `/progress` — **Kartu Statistik & Progres Lengkap**\n"
        "  Lihat grafik level, bar progres XP, status api streak 🔥, rekor IELTS, dan galeri badges prestasi langsung di chat!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👉 **Mulai Sekarang:** Tahan tombol mikrofon (🎙️) di bawah dan sapa AI Coach Anda dalam bahasa Inggris!"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("shadow"))
async def cmd_shadow(
    message: Message,
    bot: Bot,
    user_service: UserService,
    ai_coach_service: AICoachService,
    tts_service: TTSService,
    target_user_id: Optional[int] = None,
) -> None:
    """Initiate a native Shadowing pronunciation challenge."""
    user = message.from_user
    user_id = target_user_id or (user.id if user else 0)
    profile = await user_service.get_user_profile(user_id)
    level = profile.get("target_level", "Intermediate")
    tts_voice = profile.get("tts_voice", "en-US-JennyNeural")
    tts_speed = profile.get("tts_speed", "+0%")

    target_sentence = ai_coach_service.get_shadowing_target(level=level)
    await user_service.reset_all_active_drills(user_id)
    await user_service.set_active_shadow_target(user_id, target_sentence)

    # Generate reference audio
    reference_audio = await tts_service.generate_speech(target_sentence, voice=tts_voice, rate=tts_speed)

    caption = (
        f"🎧 **Shadowing Challenge ({level} Level)**\n\n"
        f"Listen to the reference pronunciation:\n"
        f"> *\"{target_sentence}\"*\n\n"
        "🎙️ **Your turn:** Hold the microphone button and repeat this sentence!\n"
        "Try to match the speaker's tempo, cadence, and pronunciation."
    )

    if reference_audio:
        voice_file = BufferedInputFile(reference_audio, filename="shadow_reference.mp3")
        await message.reply_voice(
            voice=voice_file,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=get_shadowing_control_keyboard(),
        )
    else:
        await message.answer(caption, parse_mode="Markdown", reply_markup=get_shadowing_control_keyboard())


@router.message(Command("scenario"))
async def cmd_scenario(message: Message, user_service: UserService) -> None:
    """Choose a situational roleplay scenario."""
    user = message.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)
    current = profile.get("active_scenario", "Free Conversation")

    text = (
        "🎭 **Choose a Roleplay Scenario**\n\n"
        f"Current Scenario: **{current}**\n\n"
        "Select a simulated situation for your speaking session:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_scenario_selection_keyboard(current))


@router.message(Command("review"))
async def cmd_review(message: Message, user_service: UserService) -> None:
    """Display personal vocabulary and grammar review bank."""
    user = message.from_user
    user_id = user.id if user else 0
    bank = await user_service.get_vocab_review_items(user_id, limit=10)

    if not bank:
        await message.answer(
            "📖 **Bank Kosakata & Review Anda Masih Kosong!**\n\n"
            "Saat Anda merekam dan mengirimkan voice note bahasa Inggris, setiap koreksi tata bahasa (*grammar slips*) dan kosakata yang lebih alami akan otomatis disimpan di sini agar Anda bisa mempelajarinya kembali.",
            parse_mode="Markdown",
        )
        return

    text = "📖 **Bank Kosakata & Koreksi Grammar Anda**\n\n"
    for i, item in enumerate(bank, 1):
        text += (
            f"**{i}. Pengucapan:** `{item['original_phrase']}`\n"
            f"   👉 **Saran Perbaikan:** *{item['correction']}*\n"
        )
        if item.get("explanation"):
            text += f"   💡 *{item['explanation']}*\n"
        text += "\n"

    text += "💡 *Tips: Gunakan frasa-frasa di atas pada latihan voice note berikutnya agar semakin lancar!*"
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("voice"))
async def cmd_voice(message: Message, user_service: UserService) -> None:
    """Choose preferred neural TTS spoken voice."""
    user = message.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)
    current_voice = profile.get("tts_voice", "en-US-JennyNeural")

    text = (
        "🎙️ **AI Spoken Voice Settings**\n\n"
        "Choose which voice the AI coach uses when replying to you with voice notes:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_voice_selection_keyboard(current_voice))


@router.message(Command("topic"))
async def cmd_topic(message: Message, user_service: UserService, ai_coach_service: AICoachService) -> None:
    """Provide a curated speaking prompt suited to learner's level."""
    user = message.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)
    level = profile.get("target_level", "Intermediate")
    topic = ai_coach_service.get_speaking_topic(level=level)

    text = (
        f"💡 **Speaking Practice Topic ({level} Level)**\n\n"
        f"> *\"{topic}\"*\n\n"
        "🎙️ **Your turn:** Hold the microphone button and share your thoughts in English (20–45 seconds)!"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("level"))
async def cmd_level(message: Message, user_service: UserService) -> None:
    """Change target proficiency level."""
    user = message.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)
    level = profile.get("target_level", "Intermediate")

    text = (
        "🎯 **Choose Your Target English Level**\n\n"
        f"Your current target is: **{level}**.\n"
        "Select an option to calibrate the vocabulary and feedback complexity:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_level_selection_keyboard(level))


from src.services.user_service import calculate_user_level, BADGES_CATALOG
import json


def generate_text_progress_bar(percentage: int, total_blocks: int = 10) -> str:
    """Generate a clean visual ASCII progress bar for Telegram messages."""
    filled = max(0, min(total_blocks, round(percentage / 100 * total_blocks)))
    empty = total_blocks - filled
    return "█" * filled + "░" * empty


async def render_native_progress_card(user_id: int, user_service: UserService) -> str:
    """Render comprehensive 100% native Telegram progress and statistics scorecard."""
    profile = await user_service.get_user_profile(user_id)
    history = await user_service.get_practice_history(user_id, limit=5)
    ielts_history = await user_service.get_ielts_history(user_id, limit=3)
    phoneme_stats = await user_service.get_phoneme_stats(user_id)

    name = profile.get("first_name", "Learner")
    current_streak = profile.get("current_streak", 0)
    max_streak = profile.get("max_streak", 0)
    total_xp = profile.get("total_xp", 0)
    streak_freezes = profile.get("streak_freeze_count", 1)
    is_premium = profile.get("is_premium", 0) == 1
    level_info = calculate_user_level(total_xp)
    progress_bar = generate_text_progress_bar(level_info["progress_percent"])

    pro_tag = " ⭐ *(PRO Patron)*" if is_premium else ""

    text = (
        f"📊 **KARTU PROFIL & STATISTIK BELAJAR AI**{pro_tag}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Learner:** {name}\n"
        f"🎯 **Target CEFR:** `{profile.get('target_level', 'Intermediate')}` | 🎭 **Skenario:** `{profile.get('active_scenario', 'Free Conversation')}`\n\n"
        f"⚡ **Level & Pengalaman:**\n"
        f"🎖️ **Rank:** Level `{level_info['level']}` — *{level_info['title']}*\n"
        f"⚡ **XP:** `{total_xp} XP` `[{progress_bar}]` `{level_info['progress_percent']}%`\n"
        f"📈 Butuh `{level_info['xp_needed']} XP` lagi untuk naik ke Level `{level_info['next_level']}`\n\n"
        f"🔥 **Konsistensi Streak:**\n"
        f"🔥 **Daily Streak:** `{current_streak} Hari` (Rekor: `{max_streak}`)\n"
        f"❄️ **Pelindung Streak:** `{streak_freezes} Tiket Freeze Tersedia`\n"
        f"🎙️ **Total Evaluasi:** `{profile.get('total_voice_notes', 0)} Voice Notes`\n\n"
    )

    # Badges display
    raw_badges = profile.get("badges_json") or "[]"
    try:
        user_badges = json.loads(raw_badges)
    except Exception:
        user_badges = []

    if user_badges:
        badge_lines = []
        for b in user_badges:
            b_meta = BADGES_CATALOG.get(b)
            if b_meta:
                badge_lines.append(f"{b_meta['icon']} *{b_meta['title']}*")
        if badge_lines:
            text += "🏆 **Milestone Badges:**\n" + "\n".join(badge_lines) + "\n\n"

    if phoneme_stats.get("total_drills", 0) > 0:
        text += (
            "👄 **Klinik Fonem & Pengucapan:**\n"
            f"🎯 Latihan: `{phoneme_stats['total_drills']}` drill | Rata-rata Akurasi: `{phoneme_stats['avg_accuracy']}%`\n"
            f"👂 Kontras Terdengar Jelas: `{phoneme_stats['clear_distinctions']}` pasang\n\n"
        )

    if ielts_history:
        text += "🎓 **Simulasi Ujian Resmi IELTS Terakhir:**\n"
        for res in ielts_history:
            date_str = res["created_at"][:10]
            etype = res.get("exam_type", "express").upper()
            text += (
                f"🎓 **Band `{res['overall_band']}`** ({etype} — {date_str})\n"
                f"  FC: `{res['fluency_coherence']}` | LR: `{res['lexical_resource']}` | GRA: `{res['grammar_accuracy']}` | PR: `{res['pronunciation']}`\n"
            )
        text += "\n"

    if history:
        text += "📝 **5 Sesi Latihan Terakhir:**\n"
        for i, s in enumerate(history, 1):
            date_str = s["created_at"][:10]
            cefr = s.get("cefr_level", "B1")
            ielts = s.get("ielts_band", 6.0)
            score = s.get("fluency_score", 0)
            text += f"🎙️ **Sesi #{i}** ({date_str}) — Skor: `{score}/100` | `{cefr}` (IELTS ~`{ielts}`)\n"
            if s.get("transcript"):
                snippet = s["transcript"][:55].replace("\n", " ") + "..."
                text += f"  > *\"{snippet}\"*\n"
    else:
        text += "Belum ada rekaman suara. Tahan tombol mikrofon (🎙️) untuk mengirim voice note pertama Anda!"

    return text


@router.message(Command("dashboard"))
@router.message(Command("progress"))
@router.message(Command("stats"))
async def cmd_progress(message: Message, user_service: UserService) -> None:
    """View personal speaking practice metrics, streaks, and history (100% Native Telegram)."""
    user = message.from_user
    user_id = user.id if user else 0
    text = await render_native_progress_card(user_id, user_service)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_progress_navigation_keyboard(),
    )


@router.callback_query(F.data.in_({"btn_my_progress", "btn_open_tma"}))
async def cb_my_progress(query: CallbackQuery, user_service: UserService) -> None:
    """Inline button for native progress card."""
    await query.answer()
    text = await render_native_progress_card(query.from_user.id, user_service)
    if query.message:
        await query.message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_progress_navigation_keyboard(),
        )


@router.callback_query(F.data == "btn_refresh_progress")
async def cb_refresh_progress(query: CallbackQuery, user_service: UserService) -> None:
    """Refresh the native progress card in-place."""
    await query.answer("Data statistik diperbarui! 🔄")
    text = await render_native_progress_card(query.from_user.id, user_service)
    if query.message:
        try:
            await query.message.edit_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=get_progress_navigation_keyboard(),
            )
        except Exception:
            pass


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Display command reference guide in Indonesian."""
    text = (
        "📖 **Panduan Penggunaan Speaking Coach**\n\n"
        "🎙️ **Cara Berlatih Paling Mudah:**\n"
        "Anda tidak wajib mengetik perintah! Cukup tahan tombol **Voice Note (🎙️)** di Telegram dan bicaralah dalam bahasa Inggris. Bot akan otomatis menilai kelancaran, mengoreksi grammar, dan membalas dengan suara native.\n\n"
        "✨ **Daftar Perintah Lengkap:**\n"
        "🚀 `/start` — Sambutan awal & status profil belajar Anda\n"
        "🎓 `/mock_ielts` — Simulasi resmi 3-Part IELTS Speaking Exam\n"
        "🎧 `/shadow` — Latihan peniruan tempo & intonasi native (Shadowing)\n"
        "👄 `/phonemes` — Klinik fonetik membedakan pasangan bunyi rawan tertukar\n"
        "⏳ `/tenses` — Klinik latihan tenses aktif dengan kartu rumus & skenario bicara\n"
        "🎭 `/scenario` — Ganti situasi percakapan (Interview, Cafe, Airport, Standup)\n"
        "💡 `/topic` — Dapatkan topik berbicara harian sesuai level\n"
        "🎯 `/level` — Ubah target kemahiran (Beginner / Intermediate / Advanced)\n"
        "📖 `/review` — Buka bank catatan koreksi grammar & kosakata pribadi\n"
        "📊 `/progress` — Kartu profil & statistik lengkap (Level XP, Streak, Badges, IELTS)\n"
        "🎙️ `/voice` — Ganti aksen suara balasan audio AI (Jenny / Guy / Sonia / Ryan)\n"
        "⚡ `/speed` — Atur kecepatan berbicara suara audio AI\n"
        "⏰ `/remind` — Pasang pengingat harian agar streak tidak padam\n"
        "🎁 `/invite` — Ajak teman belajar & dapatkan bonus kuota suara\n"
        "⭐ `/upgrade` — Buka akses Premium tanpa batas harian\n"
        "ℹ️ `/about` — Informasi bot & kontak bantuan\n\n"
        "💡 *Tips: Tekan tombol **[ Menu ]** di samping kolom ketikan untuk memilih perintah secara cepat.*"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    """Display information about Speaking Coach bot purpose, features, and official support."""
    text = (
        "🤖 **Tentang AI Speaking Coach**\n\n"
        "AI Speaking Coach adalah partner latihan berbicara bahasa Inggris interaktif Anda di Telegram yang siap menemani latihan kapan saja 24/7.\n\n"
        "🌟 **Fitur Utama Bot:**\n"
        "🎙️ **Latihan Percakapan Alami** dengan balasan audio suara native speaker\n"
        "🎓 **Simulasi Ujian Resmi IELTS** lengkap dengan examiner scorecard band 0.0–9.0\n"
        "🎧 **Shadowing & Intonasi** untuk melatih tempo dan ritme berbicara\n"
        "👄 **Klinik Fonem & Minimal Pairs** untuk membedakan pasangan bunyi rawan tertukar\n"
        "⏳ **Klinik Tenses Aktif** dengan kartu rumus, audio native, dan evaluasi akurasi AI\n"
        "🔥 **Sistem Streak & XP Harian** untuk menjaga konsistensi belajar Anda\n\n"
        "📬 **Kontak & Dukungan:**\n"
        "✉️ Email: `tinonurcahya.ti@gmail.com`\n\n"
        "💡 *Ketik `/help` untuk panduan penggunaan atau tahan mikrofon 🎙️ untuk mulai latihan!*"
    )
    await message.answer(text, parse_mode="Markdown")


# Callback query handlers
@router.callback_query(F.data == "btn_start_shadow")
async def cb_start_shadow(
    query: CallbackQuery,
    bot: Bot,
    user_service: UserService,
    ai_coach_service: AICoachService,
    tts_service: TTSService,
) -> None:
    """Start shadowing from inline button."""
    await query.answer()
    if query.message:
        await cmd_shadow(
            message=query.message,
            bot=bot,
            user_service=user_service,
            ai_coach_service=ai_coach_service,
            tts_service=tts_service,
            target_user_id=query.from_user.id,
        )


@router.callback_query(F.data == "btn_cancel_shadow")
async def cb_cancel_shadow(query: CallbackQuery, user_service: UserService) -> None:
    """Cancel active shadowing target."""
    await user_service.clear_active_shadow_target(query.from_user.id)
    await query.answer("Shadowing mode exited.")
    if query.message:
        await query.message.answer(
            "✅ **Shadowing Challenge Closed.**\n\nYou can now send normal voice notes for free conversation or roleplay!",
            parse_mode="Markdown",
        )


@router.callback_query(F.data == "btn_open_scenarios")
async def cb_open_scenarios(query: CallbackQuery, user_service: UserService) -> None:
    """Open scenario picker."""
    profile = await user_service.get_user_profile(query.from_user.id)
    current = profile.get("active_scenario", "Free Conversation")
    await query.answer()
    if query.message:
        await query.message.edit_text(
            f"🎭 **Select a Roleplay Scenario**\n\nCurrent: **{current}**",
            parse_mode="Markdown",
            reply_markup=get_scenario_selection_keyboard(current),
        )


@router.callback_query(F.data.startswith("scen_"))
async def cb_set_scenario(
    query: CallbackQuery,
    user_service: UserService,
    dialogue_service: Optional[DialogueService] = None,
) -> None:
    """Set active scenario and reset conversation memory with icebreaker."""
    new_scenario = query.data.replace("scen_", "")
    await user_service.update_active_scenario(query.from_user.id, new_scenario)

    if dialogue_service:
        await dialogue_service.clear_history(query.from_user.id)
        opening = dialogue_service.get_scenario_opening(new_scenario)
    else:
        opening = SCENARIO_OPENINGS.get(new_scenario, "Hi there! What's on your mind today?")

    await query.answer(f"Scenario updated: {new_scenario}")
    if query.message:
        await query.message.edit_text(
            f"🎭 **Scenario Activated:** `{new_scenario}`\n"
            "🔄 *Memori percakapan lama di-reset ke awal.*\n\n"
            f"🗣️ **Pembuka dari AI Partner:**\n"
            f"> *\"{opening}\"*\n\n"
            "🎙️ Tahan tombol Voice Note (🎙️) dan jawab langsung untuk memulai!",
            parse_mode="Markdown",
        )


@router.message(Command("reset"))
async def cmd_reset(
    message: Message,
    user_service: UserService,
    dialogue_service: Optional[DialogueService] = None,
) -> None:
    """Reset dialogue memory for the current scenario and start fresh."""
    user = message.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)
    scenario = profile.get("active_scenario", "Free Conversation")

    if dialogue_service:
        await dialogue_service.clear_history(user_id)
        opening = dialogue_service.get_scenario_opening(scenario)
    else:
        opening = SCENARIO_OPENINGS.get(scenario, "Hi there! What's on your mind today?")

    text = (
        "🔄 **Percakapan Berhasil Di-reset!**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Memori percakapan pada skenario **{scenario}** telah dikosongkan. AI Coach siap memulai obrolan baru!\n\n"
        f"🗣️ **Pertanyaan Pembuka:**\n"
        f"> *\"{opening}\"*\n\n"
        "🎙️ **Giliran Anda:** Tahan tombol mikrofon (🎙️) untuk menjawab dan melanjutkan percakapan!"
    )
    await message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data == "btn_vocab_review")
async def cb_vocab_review(query: CallbackQuery, user_service: UserService) -> None:
    """Open vocab review via inline button."""
    await query.answer()
    bank = await user_service.get_vocab_review_items(query.from_user.id, limit=8)
    if not bank:
        msg = (
            "📖 **Vocab Review Bank is Empty!**\n\n"
            "Any grammar or vocabulary slips from your voice notes will appear here automatically."
        )
    else:
        msg = "📖 **Recent Vocabulary & Grammar Corrections:**\n\n"
        for i, item in enumerate(bank, 1):
            msg += f"✏️ **{item['original_phrase']}** ➔ `{item['correction']}`\n"
    if query.message:
        await query.message.answer(msg, parse_mode="Markdown")


@router.callback_query(F.data == "btn_voice_settings")
async def cb_voice_settings(query: CallbackQuery, user_service: UserService) -> None:
    """Open voice settings."""
    profile = await user_service.get_user_profile(query.from_user.id)
    current_voice = profile.get("tts_voice", "en-US-JennyNeural")
    await query.answer()
    if query.message:
        await query.message.edit_text(
            "🎙️ **Select AI Spoken Reply Voice**",
            parse_mode="Markdown",
            reply_markup=get_voice_selection_keyboard(current_voice),
        )


@router.callback_query(F.data.startswith("voice_"))
async def cb_set_voice(query: CallbackQuery, user_service: UserService) -> None:
    """Set TTS voice."""
    new_voice = query.data.replace("voice_", "")
    await user_service.update_tts_voice(query.from_user.id, new_voice)
    await query.answer("Suara berhasil diperbarui!")
    if query.message:
        await query.message.edit_text(
            f"🎙️ **AI Voice Set to:** `{new_voice}`\n\nThe AI coach will reply with this voice note tone.",
            parse_mode="Markdown",
            reply_markup=get_voice_selection_keyboard(new_voice),
        )


@router.message(Command("speed"))
async def cmd_speed(message: Message, user_service: UserService) -> None:
    """Choose preferred neural TTS speaking speed."""
    user = message.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)
    current_speed = profile.get("tts_speed", "+0%")

    text = (
        "⚡ **AI Spoken Speed Settings (Kecepatan Suara)**\n\n"
        "Atur kecepatan berbicara AI coach sesuai kenyamanan latihan Anda:\n"
        "🐢 **0.75x** — Sangat lambat (pemula yang butuh kejelasan)\n"
        "🎧 **0.85x** — Santai & artikulasi jelas\n"
        "⚡ **1.0x** — Kecepatan normal standar native speaker\n"
        "🚀 **1.15x** — Percakapan natural agak cepat\n"
        "🏎️ **1.25x** — Cepat untuk tantangan listening\n\n"
        "Pilih tingkat kecepatan di bawah:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=get_speed_selection_keyboard(current_speed))


@router.callback_query(F.data == "open_speed_settings")
async def cb_open_speed_settings(query: CallbackQuery, user_service: UserService) -> None:
    """Open speed settings from voice menu."""
    await query.answer()
    profile = await user_service.get_user_profile(query.from_user.id)
    current_speed = profile.get("tts_speed", "+0%")
    text = (
        "⚡ **AI Spoken Speed Settings (Kecepatan Suara)**\n\n"
        "Pilih kecepatan bicara AI coach saat membalas rekaman Anda:"
    )
    if query.message:
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=get_speed_selection_keyboard(current_speed))


@router.callback_query(F.data.startswith("speed_"))
async def cb_set_speed(query: CallbackQuery, user_service: UserService) -> None:
    """Update user's speech rate setting."""
    new_speed = query.data.replace("speed_", "")
    await user_service.update_tts_speed(query.from_user.id, new_speed)
    await query.answer("Kecepatan suara berhasil diperbarui!")

    label = "1.0x (Normal Standar)"
    for item in SPEED_PRESETS.values():
        if item["rate"] == new_speed:
            label = item["label"]
            break

    text = (
        f"⚡ **Kecepatan Suara Disetel ke:** `{label}`\n\n"
        "AI Coach akan berbicara dengan kecepatan ini pada semua balasan audio dan latihan."
    )
    if query.message:
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_speed_selection_keyboard(new_speed),
        )


@router.callback_query(F.data == "btn_get_topic")
async def cb_get_topic(query: CallbackQuery, user_service: UserService, ai_coach_service: AICoachService) -> None:
    """Inline button handler for getting topic."""
    profile = await user_service.get_user_profile(query.from_user.id)
    level = profile.get("target_level", "Intermediate")
    topic = ai_coach_service.get_speaking_topic(level=level)

    await query.answer()
    text = (
        f"💡 **Speaking Practice Topic ({level} Level)**\n\n"
        f"> *\"{topic}\"*\n\n"
        "🎙️ **Your turn:** Hold the microphone button and share your thoughts in English (20–45 seconds)!"
    )
    if query.message:
        await query.message.answer(text, parse_mode="Markdown")


@router.callback_query(F.data == "btn_select_level")
async def cb_select_level(query: CallbackQuery, user_service: UserService) -> None:
    """Inline button handler to open level selector."""
    profile = await user_service.get_user_profile(query.from_user.id)
    level = profile.get("target_level", "Intermediate")
    await query.answer()
    if query.message:
        await query.message.edit_text(
            f"🎯 **Select Your Proficiency Level**\n\nCurrent: **{level}**",
            parse_mode="Markdown",
            reply_markup=get_level_selection_keyboard(level),
        )


@router.callback_query(F.data.startswith("lvl_"))
async def cb_set_level(query: CallbackQuery, user_service: UserService) -> None:
    """Handle level update."""
    new_level = query.data.replace("lvl_", "")
    await user_service.update_target_level(query.from_user.id, new_level)
    await query.answer(f"Target level updated to {new_level}!")
    if query.message:
        await query.message.edit_text(
            f"✅ **Level Updated!**\n\nYour target proficiency is now set to **{new_level}**.",
            parse_mode="Markdown",
        )





@router.callback_query(F.data == "btn_back_main")
async def cb_back_main(query: CallbackQuery) -> None:
    """Close/delete the inline selector message."""
    await query.answer()
    if query.message:
        try:
            await query.message.delete()
        except Exception:
            pass


@router.message(Command("invite"))
@router.message(Command("referral"))
async def cmd_invite(message: Message, user_service: UserService, bot: Bot) -> None:
    """Show user's referral link, stats, and 1-click share button."""
    user = message.from_user
    user_id = user.id if user else 0
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "MyEnglishCoach2000_bot"

    ref_info = await user_service.get_referral_info(user_id, bot_username=bot_username)
    link = ref_info["referral_link"]
    share_text = ref_info["share_text"]
    total_referred = ref_info["total_referred"]
    bonus_quota = ref_info["bonus_quota"]
    freezes = ref_info["streak_freezes_earned"]

    text = (
        "🎁 **Program Ajak Teman & Dapatkan Hadiah (Referral)**\n\n"
        "Ajak teman atau rekan kerja Anda untuk latihan speaking bahasa Inggris bersama AI!\n\n"
        "👥 **Hadiah Untuk Anda (Pengundang):**\n"
        "✨ **+3 Kuota Suara Tambahan** per teman yang bergabung\n"
        "❄️ **+1 Tiket Pelindung Streak (Streak Freeze)**\n"
        "⚡ **+50 XP** untuk menaikkan level ranking profil Anda\n\n"
        "🎉 **Hadiah Untuk Teman Baru Anda:**\n"
        "✨ **+3 Kuota Suara Sambutan** (Total 13 kuota suara di hari pertama) & +25 XP!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 **Statistik Referral Anda:**\n"
        f"👥 Teman Berhasil Diajak: `{total_referred} orang`\n"
        f"🎙️ Bonus Kuota Aktif: `+{bonus_quota} Voice Notes`\n"
        f"❄️ Tiket Streak Freeze Didapat: `+{freezes} Freeze`\n\n"
        f"🔗 **Link Referral Anda:**\n`{link}`\n\n"
        "Tekan tombol di bawah untuk langsung membagikannya ke chat atau grup Telegram:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_referral_keyboard(referral_link=link, share_text=share_text),
    )


@router.callback_query(F.data == "open_referral_menu")
async def cb_open_referral_menu(query: CallbackQuery, user_service: UserService, bot: Bot) -> None:
    """Callback triggered from Main Menu referral button."""
    await query.answer()
    user_id = query.from_user.id
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "MyEnglishCoach2000_bot"

    ref_info = await user_service.get_referral_info(user_id, bot_username=bot_username)
    link = ref_info["referral_link"]
    share_text = ref_info["share_text"]
    total_referred = ref_info["total_referred"]
    bonus_quota = ref_info["bonus_quota"]
    freezes = ref_info["streak_freezes_earned"]

    text = (
        "🎁 **Program Ajak Teman & Dapatkan Hadiah (Referral)**\n\n"
        "Ajak teman atau rekan kerja Anda untuk latihan speaking bahasa Inggris bersama AI!\n\n"
        "👥 **Hadiah Untuk Anda (Pengundang):**\n"
        "✨ **+3 Kuota Suara Tambahan** per teman yang bergabung\n"
        "❄️ **+1 Tiket Pelindung Streak (Streak Freeze)**\n"
        "⚡ **+50 XP** untuk menaikkan level ranking profil Anda\n\n"
        "🎉 **Hadiah Untuk Teman Baru Anda:**\n"
        "✨ **+3 Kuota Suara Sambutan** (Total 13 kuota suara di hari pertama) & +25 XP!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 **Statistik Referral Anda:**\n"
        f"👥 Teman Berhasil Diajak: `{total_referred} orang`\n"
        f"🎙️ Bonus Kuota Aktif: `+{bonus_quota} Voice Notes`\n"
        f"❄️ Tiket Streak Freeze Didapat: `+{freezes} Freeze`\n\n"
        f"🔗 **Link Referral Anda:**\n`{link}`\n\n"
        "Tekan tombol di bawah untuk langsung membagikannya ke chat atau grup Telegram:"
    )

    if query.message:
        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_referral_keyboard(referral_link=link, share_text=share_text),
        )

