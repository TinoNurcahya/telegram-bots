import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from src.config import settings
from src.repositories.video_repo import VideoRepository
from src.bot.keyboards.inline import get_main_menu_keyboard
from src.bot.keyboards.reply import get_main_reply_keyboard

router = Router()
repo = VideoRepository()

@router.message(CommandStart())
@router.message(F.text.in_({"🏠 Menu Utama", "Menu Utama", "Menu"}))
async def cmd_start(message: Message):
    text = (
        f"🎬 **Selamat Datang di AI Shorts Studio!** ⚡\n\n"
        f"Studio produksi video vertikal 9:16 otomatis dengan narasi **Female English Natural** profesional (khas channel dokumenter & misteri modern).\n\n"
        f"🎙️ **Suara Neural**: Natural English Female (*{settings.VOICE_NAME}*) dengan intonasi memikat & jernih.\n"
        f"🔤 **Subtitel**: English kinetic subtitles dinamis tersinkronisasi presisi per kata.\n"
        f"🎲 **1-Click Instant Random**: Sekali klik langsung memproduksi video kasus misteri, sains, atau paradoks secara acak dari 15+ kategori lengkap!\n\n"
        f"📅 **Otomasi Harian (5x/Hari)**: Terjadwal pukul `{', '.join(settings.daily_schedule_times)}` ({settings.SCHEDULER_TIMEZONE}) & otomatis upload ke YouTube.\n"
        f"🎯 **Format Video**: Vertikal 9:16 (1080x1920) optimal untuk YouTube Shorts, Reels, & TikTok.\n\n"
        f"👇 *Pilih menu cepat di bawah atau klik tombol inline:* "
    )
    # Set persistent bottom reply keyboard first
    await message.answer(
        "⚡ **Menu Cepat Aktif** — Tap tombol di bawah tanpa perlu mengetik `/`:",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="Markdown"
    )
    # Then display interactive inline menu
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@router.message(Command("help"))
@router.message(F.text.in_({"📖 Panduan", "Panduan", "Help"}))
async def cmd_help(message: Message):
    text = (
        "📖 **Panduan Penggunaan AI Shorts Studio**\n\n"
        "🔹 `/generate [topik opsional]` — Langsung membuat video topik acak (atau topik tertentu jika kamu tentukan).\n"
        "🔹 `/topics` — Menampilkan daftar 15+ kategori investigasi, sains, dan misteri yang tersedia.\n"
        "🔹 `/stats` — Menampilkan total video yang telah digenerate dan statistik upload.\n"
        "🔹 `/status` — Memeriksa koneksi sistem, latency ping, dan konfigurasi narator suara.\n"
        "🔹 `/help` — Menampilkan panduan ini.\n\n"
        "💡 *Tips:* Kamu bisa langsung tap tombol **🎬 Generate Video (1-Click)** di keyboard bawah tanpa mengetik apa pun!"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@router.message(Command("status"))
@router.message(F.text.in_({"⚙️ Status Sistem", "Status Sistem", "Status"}))
async def cmd_status(message: Message):
    start_t = time.perf_counter()
    msg = await message.answer("📡 Menghitung latency sistem...")
    latency = (time.perf_counter() - start_t) * 1000

    stats = await repo.get_stats()
    scheduler_status = "🟢 Aktif" if settings.ENABLE_DAILY_SCHEDULER else "🔴 Nonaktif"

    schedule_display = ", ".join(settings.daily_schedule_times)
    text = (
        f"⚙️ **Status Sistem AI Shorts Studio**\n\n"
        f"📶 **Latency Ping**: `{latency:.1f} ms`\n"
        f"⏰ **Scheduler (5x/Hari)**: `{scheduler_status}` (`{schedule_display}` {settings.SCHEDULER_TIMEZONE})\n"
        f"🎙️ **Voice Neural**: `{settings.VOICE_NAME}`\n"
        f"📐 **Resolusi Video**: `{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT}` (9:16 @ {settings.FPS}fps)\n"
        f"👥 **Total Pengguna Terdaftar**: `{stats['total_users']}`\n"
        f"🎬 **Total Video Terbuat**: `{stats['total_videos']}`\n"
        f"🆔 **Chat ID Anda**: `{message.chat.id}`"
    )
    await msg.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@router.message(Command("stats"))
@router.message(F.text.in_({"📊 Statistik", "Statistik", "Stats"}))
async def cmd_stats(message: Message):
    stats = await repo.get_stats()
    recent = await repo.get_recent_videos(limit=5)

    recent_text = ""
    if recent:
        recent_text = "\n\n🎞️ **5 Video Terakhir:**\n"
        for v in recent:
            yt_badge = f" [YouTube](https://youtube.com/shorts/{v['youtube_id']})" if v.get('youtube_id') else ""
            recent_text += f"• **{v['title']}** ({v['duration']:.0f}s){yt_badge}\n"

    text = (
        f"📊 **Statistik AI Shorts Studio**\n\n"
        f"🎬 Total Video Digenerate: **{stats['total_videos']}**\n"
        f"🚀 Total Terupload ke YouTube: **{stats['total_uploaded']}**\n"
        f"👤 Total Pengguna: **{stats['total_users']}**"
        f"{recent_text}"
    )
    await message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@router.callback_query(F.data == "btn:main_menu")
async def cb_main_menu(call: CallbackQuery):
    menu_text = "🎬 **AI Shorts Studio — Menu Utama**\n\nPilih aksi yang ingin kamu lakukan:"
    try:
        await call.message.edit_text(
            menu_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    except Exception:
        await call.message.answer(
            menu_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    await call.answer()

@router.callback_query(F.data == "btn:system_info")
async def cb_system_info(call: CallbackQuery):
    scheduler_status = "🟢 Aktif" if settings.ENABLE_DAILY_SCHEDULER else "🔴 Nonaktif"
    schedule_display = ", ".join(settings.daily_schedule_times)
    text = (
        f"⚙️ **Informasi Sistem & Konfigurasi**\n\n"
        f"🤖 **Model AI**: `{settings.GEMINI_MODEL}`\n"
        f"🎙️ **Voice**: `{settings.VOICE_NAME}`\n"
        f"📐 **Format Video**: `{settings.VIDEO_WIDTH}x{settings.VIDEO_HEIGHT}` (9:16 Vertical)\n"
        f"⏰ **Jadwal (5x/Hari)**: `{scheduler_status}` (`{schedule_display}`)\n"
        f"💾 **Storage Database**: `{settings.DATABASE_PATH}`\n"
        f"🆔 **Chat ID Anda**: `{call.message.chat.id}`"
    )
    try:
        await call.message.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception:
        await call.message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    await call.answer()

@router.callback_query(F.data == "btn:stats")
async def cb_stats(call: CallbackQuery):
    stats = await repo.get_stats()
    text = (
        f"📊 **Statistik Produksi Video**\n\n"
        f"🎬 Total Video: **{stats['total_videos']}**\n"
        f"🚀 Terupload ke YouTube: **{stats['total_uploaded']}**\n"
        f"👥 Pengguna: **{stats['total_users']}**"
    )
    try:
        await call.message.edit_text(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    except Exception:
        await call.message.answer(text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")
    await call.answer()

