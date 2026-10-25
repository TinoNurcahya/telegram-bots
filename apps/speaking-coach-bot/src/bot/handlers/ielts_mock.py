import io
import logging
from typing import Dict, Any

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from src.services.user_service import UserService
from src.services.ai_coach_service import AICoachService
from src.services.tts_service import TTSService
from src.bot.keyboards.menu import (
    get_ielts_exam_type_keyboard,
    get_ielts_question_keyboard,
    get_ielts_cue_card_keyboard,
    get_main_menu_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="ielts_mock")


async def send_ielts_step(
    target_msg: Message,
    user_service: UserService,
    tts_service: TTSService,
    session: Dict[str, Any],
    step_index: int,
) -> None:
    """Send the IELTS exam question for the current step (Audio for Part 1/3, Card for Part 2)."""
    questions = session.get("questions", [])
    if step_index >= len(questions):
        return

    q = questions[step_index]
    part = q.get("part", 1)
    q_type = q.get("type", "interview")
    total_q = len(questions)

    if q_type == "cue_card":
        cue = q.get("cue_card", {})
        bullets = "\n".join([f"📌 {bp}" for bp in cue.get("bullet_points", [])])
        card_text = (
            f"📋 *IELTS Part 2: The Long Turn (Task Card)*\n"
            f"Pertanyaan {step_index + 1} dari {total_q}\n\n"
            f"*Topic:* {cue.get('prompt', q.get('text'))}\n\n"
            f"*You should say:*\n{bullets}\n\n"
            f"⏱️ *Persiapan hingga 60 detik:*\n"
            f"Pikirkan poin-poin yang ingin Anda sampaikan. Begitu siap, tekan tombol di bawah dan rekam suara Anda (1–2 menit)!"
        )
        await target_msg.answer(
            card_text,
            reply_markup=get_ielts_cue_card_keyboard(),
        )
    else:
        # Part 1 or Part 3: Deliver via blind-listening native British examiner audio
        q_text = q.get("text", "")
        part_title = q.get("part_title", f"Part {part}")

        telegram_id = session.get("telegram_id") or target_msg.chat.id
        profile = await user_service.get_user_profile(telegram_id)
        speed = profile.get("tts_speed") or "+0%"
        voice = profile.get("tts_voice") or "en-US-JennyNeural"

        audio_bytes = await tts_service.synthesize_speech(
            text=q_text,
            voice=voice,
            rate=speed,
        )
        if audio_bytes:
            audio_file = BufferedInputFile(audio_bytes, filename=f"ielts_q_{step_index}.mp3")
            caption = (
                f"🎙️ *IELTS Speaking Test - {part_title}*\n"
                f"Pertanyaan {step_index + 1} dari {total_q}\n\n"
                f"🎧 *Dengarkan audio penguji di atas* (Blind Listening).\n"
                f"Tekan & tahan tombol mikrofon untuk merekam jawaban Anda!"
            )
            await target_msg.answer_voice(
                voice=audio_file,
                caption=caption,
                reply_markup=get_ielts_question_keyboard(step_index=step_index),
            )
        else:
            text_prompt = (
                f"🎙️ *IELTS Speaking Test - {part_title}*\n"
                f"Pertanyaan {step_index + 1} dari {total_q}\n\n"
                f"❓ *Pertanyaan Penguji:*\n"
                f"> *\"{q_text}\"*\n\n"
                f"Tekan & tahan tombol mikrofon untuk merekam jawaban Anda!"
            )
            await target_msg.answer(
                text=text_prompt,
                parse_mode="Markdown",
                reply_markup=get_ielts_question_keyboard(step_index=step_index),
            )


@router.message(Command("mock_ielts"))
async def cmd_mock_ielts(message: Message, user_service: UserService) -> None:
    """Initiate official 3-part IELTS Speaking Mock Exam flow."""
    active_session = await user_service.get_active_ielts_session(message.from_user.id)
    if active_session:
        step = active_session.get("current_step", 0)
        total = len(active_session.get("questions", []))
        await message.answer(
            f"⚠️ *Anda memiliki ujian IELTS yang sedang berjalan!* (Pertanyaan {step + 1}/{total})\n\n"
            f"Kirim voice note untuk melanjutkan, atau pilih batalkan untuk mengulang.",
            reply_markup=get_ielts_question_keyboard(step_index=step),
        )
        return

    text = (
        "🎓 *Official 3-Part IELTS Speaking Mock Exam Simulator*\n\n"
        "Simulasi ujian resmi IELTS Speaking standar Cambridge & British Council:\n"
        "🎙️ *Part 1 (Introduction)*: Wawancara seputar topik akrab via *Blind Listening* audio penguji.\n"
        "📋 *Part 2 (The Long Turn)*: Task Card (Cue Card) dengan persiapan 60 detik + 1-2 menit monolog.\n"
        "💬 *Part 3 (Two-way Discussion)*: Pertanyaan analitis dan abstrak.\n\n"
        "📈 *Scorecard Resmi*: Evaluasi 4 kriteria (FC, LR, GRA, PR) + Overall Band (skala 0.0–9.0) + reward *+100 XP*!\n\n"
        "Pilih format durasi yang Anda inginkan:"
    )
    await message.answer(text, reply_markup=get_ielts_exam_type_keyboard())


@router.callback_query(F.data == "btn_start_mock_ielts")
async def cb_start_mock_ielts(
    callback: CallbackQuery, user_service: UserService
) -> None:
    """Handle mock IELTS button click from main menu."""
    await callback.answer()
    active_session = await user_service.get_active_ielts_session(callback.from_user.id)
    if active_session:
        step = active_session.get("current_step", 0)
        total = len(active_session.get("questions", []))
        await callback.message.answer(
            f"⚠️ *Anda memiliki ujian IELTS yang sedang berjalan!* (Pertanyaan {step + 1}/{total})",
            reply_markup=get_ielts_question_keyboard(step_index=step),
        )
        return

    text = (
        "🎓 *Official 3-Part IELTS Speaking Mock Exam Simulator*\n\n"
        "Pilih format durasi yang ingin Anda ikuti:"
    )
    await callback.message.answer(text, reply_markup=get_ielts_exam_type_keyboard())


@router.callback_query(F.data.startswith("ielts_start:"))
async def cb_ielts_start_exam(
    callback: CallbackQuery,
    user_service: UserService,
    ai_coach_service: AICoachService,
    tts_service: TTSService,
) -> None:
    """Start an IELTS exam with selected duration (express or full)."""
    exam_type = callback.data.split(":")[1]  # 'express' or 'full'
    await callback.answer("Menyiapkan lembar soal IELTS...")

    await user_service.reset_all_active_drills(callback.from_user.id)
    questions = ai_coach_service.build_ielts_questions(exam_type=exam_type)
    session_id = await user_service.start_ielts_exam(
        telegram_id=callback.from_user.id,
        exam_type=exam_type,
        questions=questions,
    )

    session = await user_service.get_active_ielts_session(callback.from_user.id)
    if not session:
        await callback.message.answer("❌ Gagal memulai sesi ujian. Coba lagi.")
        return

    type_label = "Express (3 Soal)" if exam_type == "express" else "Full Simulation (6 Soal)"
    await callback.message.answer(
        f"🎯 *Ujian IELTS Dimulai!* Format: *{type_label}*\n"
        f"Penguji IELTS (British Native) akan mengajukan pertanyaan pertama..."
    )

    await send_ielts_step(
        target_msg=callback.message,
        user_service=user_service,
        tts_service=tts_service,
        session=session,
        step_index=0,
    )


@router.callback_query(F.data.startswith("ielts_reveal:"))
async def cb_ielts_reveal_text(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Reveal the question text if user struggled with blind listening."""
    step_str = callback.data.split(":")[1]
    step_idx = int(step_str)

    session = await user_service.get_active_ielts_session(callback.from_user.id)
    if not session or step_idx >= len(session.get("questions", [])):
        await callback.answer("Sesi tidak aktif atau pertanyaan telah lewat.", show_alert=True)
        return

    q = session["questions"][step_idx]
    q_text = q.get("text", "")

    await callback.answer(f"Pertanyaan:\n{q_text}", show_alert=True)


@router.callback_query(F.data == "ielts_ready_cue")
async def cb_ielts_ready_cue(callback: CallbackQuery) -> None:
    """Acknowledge candidate readiness for Part 2 monologue."""
    await callback.answer("Waktu bicara dimulai!")
    await callback.message.answer(
        "🎙️ *Waktu Monolog Anda Dimulai!*\n\n"
        "Tekan dan tahan tombol mikrofon Telegram sekarang, lalu sampaikan monolog Anda (1 hingga 2 menit) "
        "mencakup poin-poin yang diminta pada Cue Card di atas."
    )


@router.callback_query(F.data == "ielts_cancel")
async def cb_ielts_cancel(
    callback: CallbackQuery,
    user_service: UserService,
) -> None:
    """Cancel in-progress IELTS Mock Exam."""
    await user_service.cancel_ielts_exam(callback.from_user.id)
    await callback.answer("Ujian IELTS dibatalkan.")
    await callback.message.answer(
        "❌ *Ujian IELTS Speaking telah dibatalkan.*\n"
        "Anda dapat mengulang kembali kapan saja dengan mengetik `/mock_ielts`.",
    )
