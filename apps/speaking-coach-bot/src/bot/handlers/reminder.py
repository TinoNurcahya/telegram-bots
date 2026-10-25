import re
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from src.services.user_service import UserService
from src.services.reminder_service import get_random_reminder_message
from src.bot.keyboards.menu import (
    get_reminder_menu_keyboard,
    get_reminder_action_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="reminder_router")

TIME_REGEX = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def build_reminder_status_text(reminder_time: str, is_enabled: bool) -> str:
    status_str = "🟢 Aktif" if is_enabled else "🔴 Nonaktif"
    return (
        "⏰ *Pengaturan Pengingat Harian (Streak Protector)*\n\n"
        "Pertahankan kebiasaan latihan dan api streak harianmu (`🔥`) agar tidak hangus "
        "dengan notifikasi cerdas bergaya kepribadian unik Duolingo!\n\n"
        f"🕒 *Jam Notifikasi:* `{reminder_time} WIB`\n"
        f"🔔 *Status:* {status_str}\n"
        f"🎭 *Variasi Pesan:* Berganti acak (Judes, Ngga Peduli, Perhatian, Mohon-mohon)\n\n"
        "Pilih salah satu jam preset di bawah, atau uji langsung notifikasinya:"
    )


@router.message(Command("remind"))
async def cmd_remind(message: Message, user_service: UserService) -> None:
    """Open interactive reminder configuration menu."""
    user = message.from_user
    user_id = user.id if user else 0
    profile = await user_service.get_user_profile(user_id)

    r_time = profile.get("reminder_time") or "20:00"
    r_enabled = bool(profile.get("reminder_enabled", 1))

    text = build_reminder_status_text(reminder_time=r_time, is_enabled=r_enabled)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_reminder_menu_keyboard(current_time=r_time, is_enabled=r_enabled),
    )


@router.callback_query(F.data == "remind_settings")
async def cb_remind_settings(callback: CallbackQuery, user_service: UserService) -> None:
    """Open reminder settings from button menu."""
    await callback.answer()
    profile = await user_service.get_user_profile(callback.from_user.id)
    r_time = profile.get("reminder_time") or "20:00"
    r_enabled = bool(profile.get("reminder_enabled", 1))

    text = build_reminder_status_text(reminder_time=r_time, is_enabled=r_enabled)
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_reminder_menu_keyboard(current_time=r_time, is_enabled=r_enabled),
    )


@router.callback_query(F.data.startswith("remind_set:"))
async def cb_remind_set_preset(callback: CallbackQuery, user_service: UserService) -> None:
    """Set preset reminder time (e.g. 08:00, 13:00, 20:00)."""
    new_time = callback.data.split(":")[1] + ":" + callback.data.split(":")[2]
    await user_service.update_reminder_preferences(
        telegram_id=callback.from_user.id,
        reminder_time=new_time,
        enabled=True,
    )
    await callback.answer(f"Jam pengingat disetel ke {new_time} WIB!")

    text = build_reminder_status_text(reminder_time=new_time, is_enabled=True)
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_reminder_menu_keyboard(current_time=new_time, is_enabled=True),
    )


@router.callback_query(F.data == "remind_toggle")
async def cb_remind_toggle(callback: CallbackQuery, user_service: UserService) -> None:
    """Toggle reminder between enabled and disabled."""
    profile = await user_service.get_user_profile(callback.from_user.id)
    r_time = profile.get("reminder_time") or "20:00"
    current_enabled = bool(profile.get("reminder_enabled", 1))
    new_state = not current_enabled

    await user_service.update_reminder_preferences(
        telegram_id=callback.from_user.id,
        reminder_time=r_time,
        enabled=new_state,
    )

    feedback_msg = "Pengingat diaktifkan! 🔔" if new_state else "Pengingat dimatikan! 🔕"
    await callback.answer(feedback_msg)

    text = build_reminder_status_text(reminder_time=r_time, is_enabled=new_state)
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_reminder_menu_keyboard(current_time=r_time, is_enabled=new_state),
    )


@router.callback_query(F.data == "remind_test_now")
async def cb_remind_test_now(callback: CallbackQuery, user_service: UserService) -> None:
    """Trigger an instant simulation of a random Duolingo-style reminder persona."""
    await callback.answer("Mengirim sampel notifikasi acak...")
    profile = await user_service.get_user_profile(callback.from_user.id)
    first_name = profile.get("first_name") or callback.from_user.first_name or "Learner"
    streak = profile.get("current_streak") or 0

    persona, text_body = get_random_reminder_message(name=first_name, current_streak=streak)

    msg = (
        f"🧪 *[Uji Coba Notifikasi]*\n"
        f"⏰ *Speaking Check-in!* ({persona})\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{text_body}\n\n"
        f"🔥 *Current Streak:* `{streak} Hari`\n"
        f"_(Kirim 1 voice note sekarang untuk mengamankan streak hari ini!)_"
    )
    await callback.message.answer(
        msg,
        parse_mode="Markdown",
        reply_markup=get_reminder_action_keyboard(),
    )


@router.callback_query(F.data == "remind_custom_prompt")
async def cb_remind_custom_prompt(callback: CallbackQuery) -> None:
    """Guide user on how to set a custom reminder time."""
    await callback.answer()
    await callback.message.answer(
        "⚙️ *Cara Menyetel Jam Kustom:*\n\n"
        "Cukup ketik jam yang Anda inginkan langsung di chat dalam format `HH:MM` (24 jam).\n"
        "Contoh format jam:\n"
        "⏰ `07:30` (Setengah delapan pagi)\n"
        "⏰ `16:45` (Jam 5 kurang seperempat sore)\n"
        "⏰ `21:15` (Jam sembilan malam lewat seperempat)",
        parse_mode="Markdown",
    )


@router.message(F.text.regexp(r"^(?:[01]\d|2[0-3]):[0-5]\d$"))
async def msg_custom_time_received(message: Message, user_service: UserService) -> None:
    """Handle custom HH:MM time string sent by learner."""
    custom_time = message.text.strip()
    await user_service.update_reminder_preferences(
        telegram_id=message.from_user.id,
        reminder_time=custom_time,
        enabled=True,
    )

    text = (
        f"✅ *Jam Pengingat Berhasil Diatur!*\n\n"
        f"Notifikasi harian akan dikirimkan setiap pukul *{custom_time} WIB* jika Anda belum latihan pada hari tersebut."
    )
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_reminder_menu_keyboard(current_time=custom_time, is_enabled=True),
    )
