import logging
from typing import Dict, Any
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice

from src.services.user_service import UserService
from src.bot.keyboards.menu import get_upgrade_keyboard

logger = logging.getLogger(__name__)
router = Router(name="monetization_router")

PLANS: Dict[str, Dict[str, Any]] = {
    "1m": {
        "title": "Speaking Coach 1 Bulan (30 Hari)",
        "description": "Akses Premium 1 Bulan: Evaluasi voice note tanpa batas, IELTS Mock Exam, +3 Freeze Pass, +250 XP.",
        "stars": 40,
        "payload": "plan_1m",
    },
    "3m": {
        "title": "Speaking Coach 3 Bulan (90 Hari)",
        "description": "Akses Premium 3 Bulan Hemat: Evaluasi voice note tanpa batas, IELTS Mock Exam, +3 Freeze Pass, +250 XP.",
        "stars": 95,
        "payload": "plan_3m",
    },
    "lifetime": {
        "title": "Speaking Coach Seumur Hidup",
        "description": "Akses Premium Permanen: Evaluasi voice note tanpa batas, IELTS Mock Exam, +3 Freeze Pass, +250 XP & Badge.",
        "stars": 150,
        "payload": "plan_lifetime",
    },
}


PAYLOAD_TO_PLAN: Dict[str, Dict[str, Any]] = {
    p["payload"]: p for p in PLANS.values()
}
PAYLOAD_TO_PLAN["payload_speaking_coach_premium"] = PLANS["lifetime"]


def build_upgrade_pitch_text(profile: Dict[str, Any]) -> str:
    is_premium = profile.get("is_premium", 0) == 1
    freezes = profile.get("streak_freeze_count", 1)
    tier = profile.get("premium_tier") or ""
    days_left = profile.get("days_left", 0)
    is_lifetime = profile.get("is_lifetime", False) or tier == "lifetime"
    has_used_trial = profile.get("has_used_trial", 0) == 1

    if is_premium:
        if is_lifetime:
            return (
                "⭐ **Status Akun: Premium Member (Seumur Hidup)**\n\n"
                "Terima kasih atas dukungan penuh Anda! Anda menikmati seluruh fasilitas eksklusif selamanya:\n"
                "✨ Evaluasi voice note tanpa batas kuota harian\n"
                "🏛️ Akses ujian IELTS Mock Exam lengkap (Part 1, 2, & 3)\n"
                f"❄️ Sisa Tiket Pelindung Streak: `{freezes} Freeze Pass`\n"
                "🎖️ Badge Koleksi: *Star Patron* ⭐"
            )

        tier_display = "Free Trial 7 Hari" if tier == "trial_7d" else tier
        return (
            f"⭐ **Status Akun: Premium Member ({tier_display})**\n"
            f"⏳ **Sisa Masa Aktif:** `{days_left} hari lagi`\n\n"
            "Fasilitas eksklusif Anda saat ini:\n"
            "✨ Evaluasi voice note tanpa batas kuota harian\n"
            "🏛️ Akses ujian IELTS Mock Exam lengkap (Part 1, 2, & 3)\n"
            f"❄️ Sisa Tiket Pelindung Streak: `{freezes} Freeze Pass`\n\n"
            "💡 *Ingin memperpanjang masa aktif atau upgrade ke Seumur Hidup? Pilih paket di bawah:*"
        )

    trial_bullet = "🎁 **Trial 7 Hari:** `GRATIS` *(1x klaim, coba semua fitur premium!)*\n" if not has_used_trial else ""

    return (
        "⭐ **Speaking Coach Premium Pass (Telegram Stars)**\n\n"
        "Tingkatkan kemampuan berbicara bahasa Inggris Anda tanpa batasan kuota harian!\n\n"
        "📋 **Pilihan Paket Belajar Berdasarkan Durasi:**\n"
        f"{trial_bullet}"
        "🌟 **1 Bulan (30 Hari):** `40 Stars` *(Mulai latihan konsisten)*\n"
        "🚀 **3 Bulan (90 Hari):** `95 Stars` *(Hemat 20% dibanding bulanan)*\n"
        "👑 **Seumur Hidup (Lifetime):** `150 Stars` *(Sekali bayar akses selamanya)*\n\n"
        "✨ **Keuntungan Seluruh Member Premium:**\n"
        "🎙️ **Unlimited Voice Evaluations**: Bebas latihan sepuasnya setiap hari.\n"
        "🏛️ **Official 3-Part IELTS Simulator**: Akses ujian lengkap tanpa limit.\n"
        "❄️ **+3 Streak Freeze Passes**: Tiket pelindung streak latihan Anda.\n"
        "⚡ **+250 XP Bonus & Star Patron Badge**: Tingkatkan tier ranking profil Anda.\n\n"
        "Pilih tombol di bawah untuk mengaktifkan paket pilihan Anda:"
    )


@router.message(Command("upgrade"))
async def cmd_upgrade(message: Message, user_service: UserService) -> None:
    """Send premium upgrade pitch and duration options."""
    profile = await user_service.get_user_profile(message.from_user.id)
    is_premium = profile.get("is_premium", 0) == 1
    is_lifetime = profile.get("is_lifetime", False) or profile.get("premium_tier") == "lifetime"
    has_used_trial = profile.get("has_used_trial", 0) == 1

    text = build_upgrade_pitch_text(profile)
    if is_premium and is_lifetime:
        await message.answer(text, parse_mode="Markdown")
    else:
        keyboard = get_upgrade_keyboard(
            has_used_trial=has_used_trial,
            is_active_subscriber=is_premium and not is_lifetime,
        )
        await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data == "buy_premium")
async def cb_buy_premium(query: CallbackQuery, user_service: UserService) -> None:
    """Callback triggered from menu or freemium quota limit."""
    await query.answer()
    profile = await user_service.get_user_profile(query.from_user.id)
    is_premium = profile.get("is_premium", 0) == 1
    is_lifetime = profile.get("is_lifetime", False) or profile.get("premium_tier") == "lifetime"
    has_used_trial = profile.get("has_used_trial", 0) == 1

    text = build_upgrade_pitch_text(profile)
    if is_premium and is_lifetime:
        await query.message.edit_text(text, parse_mode="Markdown")
    else:
        keyboard = get_upgrade_keyboard(
            has_used_trial=has_used_trial,
            is_active_subscriber=is_premium and not is_lifetime,
        )
        await query.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)


@router.callback_query(F.data == "claim_trial_7d")
async def cb_claim_trial(query: CallbackQuery, user_service: UserService) -> None:
    """One-click activation for 7-day free trial."""
    await query.answer()
    res = await user_service.claim_free_trial(query.from_user.id)
    if res.get("success"):
        raw_expiry = res.get("expires_at", "")
        expires_date_str = raw_expiry[:10] if raw_expiry else "7 hari ke depan"
        celebration = (
            "🎉 **TRIAL GRATIS 7 HARI BERHASIL DIAKTIFKAN!** 🎁\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Selamat! Akun Anda aktif sebagai **Premium Member** hingga `{expires_date_str}`.\n\n"
            "✨ **Fasilitas yang Langsung Aktif:**\n"
            "🎙️ Evaluasi voice note tanpa batas kuota harian\n"
            "🏛️ Akses penuh ujian resmi IELTS Mock Exam (`/mock_ielts`)\n\n"
            "Ayo tahan tombol Voice Note (🎙️) sekarang dan rasakan serunya latihan tanpa batas!"
        )
        await query.message.edit_text(celebration, parse_mode="Markdown")
    else:
        err_msg = res.get("message", "Gagal mengklaim Free Trial.")
        await query.message.answer(f"⚠️ {err_msg}", parse_mode="Markdown")


@router.callback_query(F.data.startswith("pay_stars_"))
async def cb_pay_stars(query: CallbackQuery, bot: Bot) -> None:
    """Send official Telegram Stars invoice for the selected package."""
    await query.answer()
    plan_key = query.data.replace("pay_stars_", "")

    if plan_key == "150":
        plan_key = "lifetime"

    plan = PLANS.get(plan_key, PLANS["lifetime"])
    prices = [LabeledPrice(label=plan["title"], amount=plan["stars"])]

    try:
        await bot.send_invoice(
            chat_id=query.from_user.id,
            title=plan["title"],
            description=plan["description"],
            payload=plan["payload"],
            currency="XTR",  # Telegram Stars native currency
            prices=prices,
        )
    except Exception as e:
        logger.error("Failed to send Stars invoice for %s: %s", plan_key, e)
        await query.message.answer(
            "⚠️ Maaf, pembayaran via Telegram Stars memerlukan setup Bot Payments di BotFather, "
            "atau Anda dapat mencoba kembali dalam beberapa saat.",
            parse_mode="Markdown",
        )


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    """Validate payment before charging user's Telegram Stars against tampering."""
    currency = pre_checkout_query.currency
    payload = pre_checkout_query.invoice_payload or ""
    total_amount = pre_checkout_query.total_amount

    # 1. Currency validation: Telegram Stars is exclusively XTR
    if currency != "XTR":
        logger.warning("Rejected pre-checkout: invalid currency %s (expected XTR)", currency)
        await pre_checkout_query.answer(
            ok=False,
            error_message="Mata uang transaksi tidak valid. Hanya Telegram Stars (XTR) yang didukung.",
        )
        return

    # 2. Payload validation: Must be known plan payload
    plan = PAYLOAD_TO_PLAN.get(payload)
    if not plan:
        logger.warning("Rejected pre-checkout: unknown invoice payload '%s'", payload)
        await pre_checkout_query.answer(
            ok=False,
            error_message="Paket langganan tidak valid atau telah kedaluwarsa.",
        )
        return

    # 3. Amount validation: Price in Stars must match exactly
    expected_stars = plan["stars"]
    if total_amount != expected_stars:
        logger.warning(
            "Rejected pre-checkout: amount mismatch for %s (got %s Stars, expected %s Stars)",
            payload, total_amount, expected_stars,
        )
        await pre_checkout_query.answer(
            ok=False,
            error_message=f"Jumlah Telegram Stars tidak cocok (diharapkan {expected_stars} Stars).",
        )
        return

    # All checks passed
    logger.info(
        "Approved pre-checkout for user %s: payload=%s, amount=%s Stars",
        pre_checkout_query.from_user.id, payload, total_amount,
    )
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, user_service: UserService) -> None:
    """Fulfill order upon verified successful Stars payment."""
    payment = message.successful_payment
    user_id = message.from_user.id
    payload = payment.invoice_payload or ""
    total_amount = payment.total_amount
    currency = payment.currency

    # Re-verify payment parameters before fulfillment
    plan = PAYLOAD_TO_PLAN.get(payload)
    if not plan or currency != "XTR" or total_amount != plan["stars"]:
        logger.error(
            "Suspicious successful payment received from user %s: payload=%s, currency=%s, amount=%s",
            user_id, payload, currency, total_amount,
        )
        await message.answer(
            "⚠️ Pembayaran Anda tercatat, tetapi rincian transaksi tidak cocok dengan sistem kami. "
            "Silakan hubungi admin untuk bantuan.",
            parse_mode="Markdown",
        )
        return

    logger.info("Fulfilling verified payment from user %s for plan %s (%s Stars)", user_id, payload, total_amount)

    # Grant duration subscription
    result = await user_service.grant_subscription(user_id, plan_type=payload)
    tier_name = result.get("tier", "Premium")
    is_lifetime = result.get("is_lifetime", False)
    expires_at = result.get("expires_at", "")[:10] if not is_lifetime else "Selamanya (Seumur Hidup)"

    celebration = (
        "🎉 **PEMBAYARAN TELEGRAM STARS BERHASIL!** ⭐\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"Selamat! Akun Anda kini berstatus **Speaking Coach {tier_name}**.\n"
        f"⏳ **Masa Aktif:** `{expires_at}`\n\n"
        "🎁 **Keuntungan yang Langsung Aktif:**\n"
        "🎙️ Evaluasi voice note tanpa batas kuota harian\n"
        "🏛️ Akses penuh ujian resmi IELTS Mock Exam\n"
        "❄️ +3 Tiket Pelindung Streak (Streak Freeze)\n"
        "⚡ +250 XP bonus telah ditambahkan ke profil Anda\n"
        "🎖️ Badge *Star Patron* ⭐ resmi terbuka!\n\n"
        "Ayo rekam suara Anda sekarang dan lanjutkan latihan berbicara!"
    )

    await message.answer(celebration, parse_mode="Markdown")
