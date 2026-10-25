import asyncio
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional

try:
    from aiogram import Bot
except ImportError:
    Bot = Any

from src.services.user_service import UserService

logger = logging.getLogger(__name__)

# ==============================================================================
# DUOLINGO-STYLE UNHINGED & VARIED REMINDER MESSAGES
# ==============================================================================

JUDES_MESSAGES = [
    "Streak {streak} hari kamu mau dibuang gitu aja? Ya udah sih terserah, aku cuma robot yang buang-buang waktu nungguin kamu 😒💅",
    "Hai {name}, kayaknya kamu lebih sibuk scroll medsos daripada latihan speaking 2 menit ya. No judgment, cuma fakta aja 💅📱",
    "Oh {name}, jadi bahasa Inggrisnya udah fasih banget ya sampai hari ini gak mau latihan? Streak {streak} hari kamu angus lho 🙄",
    "Streak {streak} harimu lagi sekarat nih. Kalau hilang jangan salahin aku ya, salahin rasa magermu 😤",
]

NGGA_PEDULI_MESSAGES = [
    "Ini pengingat harian kamu. Mau latihan atau ngga, hidupku tetap lanjut. Streak {streak} hari kamu sih yang hangus 🤷‍♂️",
    "Hari ini belum ada voice note dari kamu, {name}. Not that I care, but your streak definitely does 😐",
    "Hanya sekadar memberitahu: hari ini kamu belum latihan. Terserah mau amankan streak {streak} hari atau ngga 🧊",
    "Satu voice note sebelum tengah malam, atau streak {streak} hari kamu jadi abu. Pilihan ada di tanganmu 😶",
]

PERHATIAN_MESSAGES = [
    "Hai {name}! ☀️ Luangkan waktu 2 menit aja buat diri kamu hari ini. Kamu hebat udah bertahan streak {streak} hari! Yuk kirim 1 voice note santai 🔥",
    "Hai {name}, jangan lupa bersyukur dan amankan streak {streak} hari untuk masa depanmu! Aku udah siap mendengarkan suaramu hari ini 🌟🎙️",
    "Progres kecil setiap hari bakal jadi lompatan besar! Streak {streak} hari kamu bukti dedikasi kamu. Semangat latihan hari ini, {name}! 💪",
    "Hai {name}! Luangkan sejenak waktu santai, tarik napas, dan ceritakan harimu dalam bahasa Inggris demi streak {streak} hari kita! ☕✨",
]

MOHON_MOHON_MESSAGES = [
    "PLISSS kirim satu voice note aja hari ini {name}! Aku mohonnn demi api streak {streak} hari kamu jangan sampai padam 😭🙏🔥",
    "Aku sampai sujud mohon-mohon nih {name}... 2 menit aja, tolong jangan tinggalkan aku dan hancurkan streak {streak} hari kita 🥺💔",
    "Bentar doang kok {name}, cuma 30 detik ngomong apa aja! Tolong selamatkan nyawa streak {streak} hari kamu, jangan buat aku menangis 😭",
    "Demi masa depan IELTS dan karir impianmu {name}, aku memohon padamu... buka mic dan bicara satu kalimat aja hari ini! 🥺🙏",
]

PERSONA_COLLECTION = [
    ("😒 Judes", JUDES_MESSAGES),
    ("😐 Ngga Peduli", NGGA_PEDULI_MESSAGES),
    ("☀️ Perhatian", PERHATIAN_MESSAGES),
    ("🥺 Mohon-mohon", MOHON_MOHON_MESSAGES),
]


def get_random_reminder_message(name: str = "Learner", current_streak: int = 0) -> Tuple[str, str]:
    """Select a random Duolingo-style persona message and interpolate user details."""
    safe_streak = max(1, current_streak)
    persona_label, message_list = random.choice(PERSONA_COLLECTION)
    template = random.choice(message_list)
    formatted = template.format(name=name, streak=safe_streak)
    return persona_label, formatted


async def reminder_worker_loop(
    bot: Bot,
    user_service: UserService,
    check_interval_seconds: int = 60,
) -> None:
    """Async background task that periodically checks and dispatches due reminders."""
    from src.bot.keyboards.menu import get_reminder_action_keyboard
    logger.info("Proactive reminder background worker started (Interval: %ss)", check_interval_seconds)

    while True:
        try:
            # WIB (UTC+7) time reference
            now_utc7 = datetime.now(timezone(timedelta(hours=7)))
            current_hh_mm = now_utc7.strftime("%H:%M")
            today_str = now_utc7.date().isoformat()

            # Query due learners who have not practiced today
            due_users = await user_service.get_due_reminders(
                current_hh_mm=current_hh_mm,
                today_str=today_str,
            )

            for u in due_users:
                telegram_id = u["telegram_id"]
                first_name = u.get("first_name") or "Learner"
                streak = u.get("current_streak") or 0

                persona, text_body = get_random_reminder_message(
                    name=first_name,
                    current_streak=streak,
                )

                msg = (
                    f"⏰ *Speaking Check-in!* ({persona})\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{text_body}\n\n"
                    f"🔥 *Current Streak:* `{streak} Hari`\n"
                    f"_(Kirim 1 voice note sekarang untuk mengamankan streak hari ini!)_"
                )

                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=msg,
                        parse_mode="Markdown",
                        reply_markup=get_reminder_action_keyboard(),
                    )
                    await user_service.mark_reminded(telegram_id=telegram_id, today_str=today_str)
                    logger.info("Sent reminder alert to user %s (%s)", telegram_id, persona)
                except Exception as send_err:
                    logger.warning("Failed to send reminder to user %s: %s", telegram_id, send_err)

            await asyncio.sleep(check_interval_seconds)

        except asyncio.CancelledError:
            logger.info("Proactive reminder background worker received stop signal.")
            break
        except Exception as err:
            logger.error("Error in reminder worker loop: %s", err)
            await asyncio.sleep(check_interval_seconds)
