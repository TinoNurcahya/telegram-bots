import asyncio
import io
import logging
from typing import Dict, Any, Optional

try:
    from arq.connections import RedisSettings, create_pool
except ImportError:
    RedisSettings = None
    create_pool = None

try:
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.types import BufferedInputFile
except ImportError:
    Bot = Any  # type: ignore
    DefaultBotProperties = Any  # type: ignore
    ParseMode = Any  # type: ignore

    class BufferedInputFile:  # type: ignore
        def __init__(self, file: bytes, filename: str = "", **kwargs):
            self.file = file
            self.filename = filename

from src.config import load_settings
from src.repositories import create_coach_repository
from src.services.user_service import UserService
from src.services.ai_coach_service import AICoachService
from src.services.tts_service import TTSService
from src.bot.keyboards.menu import (
    get_shadowing_control_keyboard,
    get_phoneme_result_keyboard,
    get_tense_result_keyboard,
    get_main_menu_keyboard,
    get_ielts_question_keyboard,
)

logger = logging.getLogger("speaking_coach_worker")


async def safe_edit_message_text(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: Optional[Any] = None,
    parse_mode: str = "Markdown",
) -> None:
    """Edit message with fallback to plain text if Markdown entity parsing fails or text is too long."""
    if len(text) > 4000:
        text = text[:3990] + "\n\n... (truncated)"

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
    except Exception as err:
        logger.warning("safe_edit_message_text markdown failed: %s. Falling back to plain text.", err)
        try:
            clean_text = text.replace("*", "").replace("`", "").replace("_", "").replace("~", "")
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=clean_text,
                reply_markup=reply_markup,
            )
        except Exception as retry_err:
            logger.error("safe_edit_message_text fallback failed completely: %s", retry_err)


async def execute_voice_job(
    job_data: Dict[str, Any],
    bot: Bot,
    user_service: UserService,
    ai_coach_service: AICoachService,
    tts_service: TTSService,
    dialogue_service: Optional[Any] = None,
) -> Dict[str, Any]:
    """Core domain logic to process audio evaluation and deliver spoken responses.
    
    Can be invoked by Arq background worker or direct in-process fallback.
    """
    chat_id = job_data["chat_id"]
    user_id = job_data["user_id"]
    status_message_id = job_data["status_message_id"]
    audio_bytes = job_data["audio_bytes"]
    mime_type = job_data.get("mime_type", "audio/ogg")
    duration = job_data.get("duration", 0)

    # Context settings
    active_ielts_session = job_data.get("active_ielts_session")
    active_shadow_target = job_data.get("active_shadow_target") or ""
    active_phoneme_drill = job_data.get("active_phoneme_drill")
    active_tense_drill = job_data.get("active_tense_drill")

    # 0. Freemium Daily Quota Check
    profile = {}
    if hasattr(user_service, "get_user_profile"):
        try:
            res = user_service.get_user_profile(user_id)
            if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
                profile = await res or {}
            elif isinstance(res, dict):
                profile = res
        except Exception as e:
            logger.warning("Could not fetch user profile in worker: %s", e)
    can_eval, used_today, max_limit = await user_service.check_daily_quota(user_id)
    if not can_eval:
        from src.bot.keyboards.menu import get_freemium_limit_keyboard
        has_used_trial = bool(profile.get("has_used_trial", 0))
        limit_text = (
            f"⏳ **Batas Latihan Harian Tercapai ({max_limit}/{max_limit} Voice Notes Gratis)**\n\n"
            f"Anda telah menggunakan {max_limit} evaluasi gratis Anda untuk hari ini!\n"
            "Kuota gratis Anda akan otomatis di-reset besok pukul 07:00 WIB (00:00 UTC).\n\n"
            "🌟 **Upgrade ke Speaking Coach Premium Pass:**\n"
            "✨ Evaluasi voice note & respon suara AI tanpa batas\n"
            "🏛️ Akses penuh ujian resmi IELTS Mock Exam\n"
            "❄️ +3 Tiket Pelindung Streak (Streak Freeze)\n"
            "⚡ +250 Bonus XP dan Badge Eksklusif Star Patron ⭐\n\n"
            "Tingkatkan akun Anda sekarang dengan Telegram Stars (`XTR`) atau klaim Free Trial 7 Hari!"
        )
        await safe_edit_message_text(
            bot=bot,
            chat_id=chat_id,
            message_id=status_message_id,
            text=limit_text,
            parse_mode="Markdown",
            reply_markup=get_freemium_limit_keyboard(has_used_trial=has_used_trial),
        )
        return {"status": "quota_exceeded"}

    # -------------------------------------------------------------
    # Branch 0: Active IELTS Mock Exam Session
    # -------------------------------------------------------------
    if active_ielts_session:
        user_transcript = await ai_coach_service.transcribe_voice_note(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
        )
        await user_service.record_daily_eval(user_id)

        step_idx = active_ielts_session.get("current_step", 0)
        questions = active_ielts_session.get("questions", [])
        responses = active_ielts_session.get("responses", [])
        curr_q = questions[step_idx] if step_idx < len(questions) else {}

        responses.append({
            "step_index": step_idx,
            "part": curr_q.get("part", 1),
            "part_title": curr_q.get("part_title", ""),
            "question_text": curr_q.get("text", ""),
            "transcript": user_transcript,
        })

        next_step = step_idx + 1

        if next_step < len(questions):
            await user_service.record_ielts_answer(
                session_id=active_ielts_session["id"],
                current_step=next_step,
                responses=responses,
            )
            active_ielts_session["current_step"] = next_step
            active_ielts_session["responses"] = responses

            await safe_edit_message_text(
                bot=bot,
                chat_id=chat_id,
                message_id=status_message_id,
                text=(
                    f"✅ *Jawaban Anda tercatat:*\n> \"_{user_transcript}_\"\n\n"
                    f"Penguji IELTS melanjutkan ke pertanyaan berikutnya..."
                ),
                parse_mode="Markdown",
            )
            from src.bot.handlers.ielts_mock import send_ielts_step
            # Create dummy target message object for sending question
            class FakeMsg:
                async def answer(self, text, reply_markup=None):
                    return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="Markdown")
                async def answer_voice(self, voice, caption=None, reply_markup=None):
                    return await bot.send_voice(chat_id=chat_id, voice=voice, caption=caption, reply_markup=reply_markup, parse_mode="Markdown")

            await send_ielts_step(
                target_msg=FakeMsg(),
                user_service=user_service,
                tts_service=tts_service,
                session=active_ielts_session,
                step_index=next_step,
            )
            return {"status": "ielts_step_completed", "step": next_step}
        else:
            await safe_edit_message_text(
                bot=bot,
                chat_id=chat_id,
                message_id=status_message_id,
                text=(
                    "⏳ *Ujian IELTS Selesai!*\n\n"
                    "Official Examiner sedang menganalisis rekaman seluruh sesi dan menghitung 4 kriteria IELTS Scorecard Anda...\n"
                    "_(Mohon tunggu sekitar 5–10 detik)_"
                ),
                parse_mode="Markdown",
            )

            ielts_feedback = await ai_coach_service.evaluate_ielts_mock_exam(
                exam_type=active_ielts_session["exam_type"],
                questions=questions,
                responses=responses,
            )

            streak_res = await user_service.finalize_ielts_exam(
                telegram_id=user_id,
                exam_type=active_ielts_session["exam_type"],
                feedback=ielts_feedback,
            )

            strengths_text = "\n".join([f"💪 {s}" for s in ielts_feedback.strengths]) or "💪 Consistent engagement"
            weaknesses_text = "\n".join([f"🎯 {w}" for w in ielts_feedback.weaknesses]) or "🎯 Minor grammatical hesitations"

            scorecard_msg = (
                f"🎓 *OFFICIAL IELTS SPEAKING SCORECARD* 🏛️\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📋 *Format:* {active_ielts_session['exam_type'].upper()} MOCK EXAM\n\n"
                f"🌟 *OVERALL BAND SCORE:  `{ielts_feedback.overall_band}` / 9.0*\n\n"
                f"📊 *Assessment Criteria Sub-Scores:*\n"
                f"🗣️ *Fluency & Coherence (FC):* `{ielts_feedback.fluency_coherence}`\n"
                f"📚 *Lexical Resource (LR):* `{ielts_feedback.lexical_resource}`\n"
                f"📐 *Grammar Range & Accuracy (GRA):* `{ielts_feedback.grammar_accuracy}`\n"
                f"🎙️ *Pronunciation (PR):* `{ielts_feedback.pronunciation}`\n\n"
                f"👨‍🏫 *Examiner Summary:*\n{ielts_feedback.examiner_summary}\n\n"
                f"✅ *Key Strengths:*\n{strengths_text}\n\n"
                f"⚠️ *Areas for Improvement:*\n{weaknesses_text}\n\n"
                f"🚀 *Roadmap to Next Band (+1.0):*\n{ielts_feedback.key_recommendations_for_band_plus}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🏆 *Exam Reward:* `+100 XP` | 🔥 Streak: `{streak_res.current_streak} Hari` (Total: `{streak_res.total_xp} XP`)"
            )

            await safe_edit_message_text(
                bot=bot,
                chat_id=chat_id,
                message_id=status_message_id,
                text=scorecard_msg,
                parse_mode="Markdown",
            )
            return {"status": "ielts_exam_finalized", "band": ielts_feedback.overall_band}

    # -------------------------------------------------------------
    # Branch A: Active Shadowing Challenge
    # -------------------------------------------------------------
    if active_shadow_target:
        shadow_feedback = await ai_coach_service.evaluate_shadowing_attempt(
            audio_bytes=audio_bytes,
            target_text=active_shadow_target,
            mime_type=mime_type,
        )
        await user_service.record_daily_eval(user_id)

        await user_service.clear_active_shadow_target(user_id)
        await user_service.record_shadowing_history(
            telegram_id=user_id,
            target_text=active_shadow_target,
            user_transcript=shadow_feedback.transcribed_text,
            match_score=shadow_feedback.match_score,
        )

        bonus_xp = 25 if shadow_feedback.match_score >= 80 else 10
        streak_res = await user_service.process_daily_streak_and_xp(
            telegram_id=user_id,
            activity_type="shadowing",
            bonus_xp=bonus_xp,
        )

        score = shadow_feedback.match_score
        stars = "⭐" * min(5, max(1, score // 20))
        streak_tag = f"🔥 `{streak_res.current_streak} Days Streak` (+`{streak_res.xp_earned} XP`)"

        text = (
            f"🎧 **Shadowing Evaluation** {stars}\n\n"
            f"🎯 **Target:**\n> *\"{active_shadow_target}\"*\n\n"
            f"📝 **What You Said:**\n> *\"{shadow_feedback.transcribed_text}\"*\n\n"
            f"📊 **Pronunciation Match:** `{score}%`\n"
        )
        if shadow_feedback.mispronounced_words:
            text += "\n🗣️ **Words to Polish:**\n"
            for w in shadow_feedback.mispronounced_words:
                text += f"🔍 `{w}`\n"
        text += f"\n🎶 **Cadence & Rhythm:**\n{shadow_feedback.cadence_feedback}\n"
        text += f"\n💬 **Coach:** {shadow_feedback.praise_message}\n"
        text += f"\n🏆 **Progress:** {streak_tag} | Total: `{streak_res.total_xp} XP`"

        await safe_edit_message_text(
            bot=bot,
            chat_id=chat_id,
            message_id=status_message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=get_shadowing_control_keyboard(),
        )
        return {"status": "shadowing_evaluated", "score": score}

    # -------------------------------------------------------------
    # Branch B: Active Phoneme Drill
    # -------------------------------------------------------------
    if active_phoneme_drill:
        phoneme_feedback = await ai_coach_service.evaluate_phoneme_attempt(
            audio_bytes=audio_bytes,
            target_drill=active_phoneme_drill,
            mime_type=mime_type,
        )
        await user_service.record_daily_eval(user_id)

        await user_service.clear_active_phoneme_drill(user_id)
        pair_id = active_phoneme_drill.get("id", "")
        cat_id = active_phoneme_drill.get("category_id", "")
        pair_label = active_phoneme_drill.get("label", f"{active_phoneme_drill.get('word_a')} vs {active_phoneme_drill.get('word_b')}")
        target_words = f"{active_phoneme_drill.get('word_a')} ({active_phoneme_drill.get('ipa_a')}) vs {active_phoneme_drill.get('word_b')} ({active_phoneme_drill.get('ipa_b')})"

        await user_service.record_phoneme_drill(
            telegram_id=user_id,
            category_id=cat_id,
            pair_id=pair_id,
            pair_label=pair_label,
            target_words=target_words,
            user_transcript=phoneme_feedback.detected_words,
            accuracy_score=phoneme_feedback.accuracy_score,
            is_distinction_clear=phoneme_feedback.is_distinction_clear,
            detected_ipa=phoneme_feedback.detected_ipa,
            mouth_position_tip=phoneme_feedback.mouth_position_tip,
        )

        bonus_xp = 10 if phoneme_feedback.accuracy_score >= 90 else 0
        streak_res = await user_service.process_daily_streak_and_xp(
            telegram_id=user_id,
            activity_type="phoneme",
            bonus_xp=bonus_xp,
        )

        badge = (
            "✅ **Kontras Terbedakan Sempurna!**"
            if phoneme_feedback.is_distinction_clear
            else ("⚠️ **Cukup Baik (Perlu Sedikit Pembersihan)**" if phoneme_feedback.accuracy_score >= 70 else "❌ **Bunyi Masih Tertukar / Samar**")
        )
        streak_tag = f"🔥 `{streak_res.current_streak} Days Streak` (+`{streak_res.xp_earned} XP`)"

        scorecard_text = (
            f"👄 **Phonetics Clinic: Evaluation Scorecard**\n\n"
            f"🎯 **Target Minimal Pair:**\n"
            f"🔊 `{active_phoneme_drill.get('word_a')}` ({active_phoneme_drill.get('ipa_a')}) vs "
            f"`{active_phoneme_drill.get('word_b')}` ({active_phoneme_drill.get('ipa_b')})\n\n"
            f"🗣️ **Yang Terdengar oleh AI:**\n"
            f"> *\"{phoneme_feedback.detected_words}\"*\n"
            f"🎯 **Target IPA:** `{phoneme_feedback.target_ipa}`\n"
            f"👂 **Detected IPA:** `{phoneme_feedback.detected_ipa}`\n\n"
            f"📊 **Akurasi Fonem:** `{phoneme_feedback.accuracy_score}%` | {badge}\n\n"
            f"👄 **Tips Posisi Mulut & Lidah:**\n"
            f"{phoneme_feedback.mouth_position_tip}\n\n"
            f"👨‍🏫 **Komentar Coach:**\n"
            f"{phoneme_feedback.coaching_summary}\n\n"
            f"🏆 **Progress:** {streak_tag} | Total: `{streak_res.total_xp} XP`"
        )

        await safe_edit_message_text(
            bot=bot,
            chat_id=chat_id,
            message_id=status_message_id,
            text=scorecard_text,
            parse_mode="Markdown",
            reply_markup=get_phoneme_result_keyboard(pair_id=pair_id, category_id=cat_id),
        )
        return {"status": "phoneme_evaluated", "accuracy": phoneme_feedback.accuracy_score}

    # -------------------------------------------------------------
    # Branch T: Active Tense Exercise
    # -------------------------------------------------------------
    if active_tense_drill:
        tense_id = active_tense_drill.get("id", "") if isinstance(active_tense_drill, dict) else str(active_tense_drill)
        tense_feedback = await ai_coach_service.evaluate_tense_exercise(
            audio_bytes=audio_bytes,
            tense_id=tense_id,
            mime_type=mime_type,
        )
        await user_service.record_daily_eval(user_id)
        await user_service.clear_active_tense_drill(user_id)

        tense_detail = ai_coach_service.get_tense_detail(tense_id) or {}
        tense_title = tense_detail.get("title", tense_id.replace("_", " ").title())

        await user_service.record_tense_exercise(
            telegram_id=user_id,
            tense_id=tense_id,
            tense_title=tense_title,
            user_transcript=tense_feedback.user_transcript,
            accuracy_score=tense_feedback.tense_accuracy,
            is_target_tense_used=tense_feedback.is_correct_tense,
            verb_form_analysis=tense_feedback.corrected_sentence,
            coaching_tip=tense_feedback.explanation,
        )

        bonus_xp = 15 if tense_feedback.tense_accuracy >= 85 else 0
        streak_res = await user_service.process_daily_streak_and_xp(
            telegram_id=user_id,
            activity_type="tenses",
            bonus_xp=bonus_xp,
        )

        badge = (
            "✅ **Penggunaan Tense Tepat & Akurat!**"
            if tense_feedback.is_correct_tense
            else ("⚠️ **Hampir Tepat (Ada Koreksi Minor)**" if tense_feedback.tense_accuracy >= 65 else "❌ **Bentuk Tense Belum Sesuai**")
        )
        streak_tag = f"🔥 `{streak_res.current_streak} Hari Streak` (+`{streak_res.xp_earned} XP`)"

        scorecard_text = (
            f"⏳ **Klinik Tenses: Scorecard Evaluasi**\n\n"
            f"🎯 **Topik Tense:** {tense_title}\n"
            f"🗣️ **Yang Anda Ucapkan:**\n"
            f"> *\"{tense_feedback.user_transcript}\"*\n\n"
            f"📊 **Akurasi Tense:** `{tense_feedback.tense_accuracy}%` | {badge}\n\n"
            f"✏️ **Kalimat Terbaik:**\n"
            f"`{tense_feedback.corrected_sentence}`\n\n"
            f"💡 **Penjelasan Grammar:**\n"
            f"{tense_feedback.explanation}\n\n"
            f"💬 **Komentar Coach:**\n"
            f"{tense_feedback.coaching_comment}\n\n"
            f"🏆 **Progress:** {streak_tag} | Total: `{streak_res.total_xp} XP`\n\n"
            f"🎙️ *Menghasilkan audio respon Coach...*"
        )

        await safe_edit_message_text(
            bot=bot,
            chat_id=chat_id,
            message_id=status_message_id,
            text=scorecard_text,
            parse_mode="Markdown",
            reply_markup=get_tense_result_keyboard(tense_id=tense_id),
        )

        tts_voice = (profile.get("tts_voice") if profile else None) or job_data.get("tts_voice") or "en-US-JennyNeural"
        tts_speed = (profile.get("tts_speed") if profile else None) or job_data.get("tts_speed") or "+0%"

        spoken_feedback = f"{tense_feedback.coaching_comment}. Correct pattern: {tense_feedback.corrected_sentence}"
        reply_audio = await tts_service.generate_speech(
            text=spoken_feedback,
            voice=tts_voice,
            rate=tts_speed,
        )

        if reply_audio:
            voice_file = BufferedInputFile(reply_audio, filename="tense_feedback.mp3")
            await bot.send_voice(
                chat_id=chat_id,
                voice=voice_file,
                caption=f"🗣️ *Audio Feedback Klinik Tenses ({tense_title})*",
                parse_mode="Markdown",
            )

        return {"status": "tense_evaluated", "accuracy": tense_feedback.tense_accuracy}

    # -------------------------------------------------------------
    # Branch C: Standard Conversation & Roleplay
    # -------------------------------------------------------------
    target_level = job_data.get("target_level", "Intermediate")
    scenario = job_data.get("scenario", "Free Conversation")
    tts_voice = (profile.get("tts_voice") if profile else None) or job_data.get("tts_voice") or "en-US-JennyNeural"
    tts_speed = (profile.get("tts_speed") if profile else None) or job_data.get("tts_speed") or "+0%"

    dialogue_history = job_data.get("dialogue_history")
    if dialogue_history is None and dialogue_service:
        try:
            dialogue_history = await dialogue_service.get_history(user_id, scenario=scenario, max_turns=10)
        except Exception as err:
            logger.warning("Failed to fetch dialogue history: %s", err)
            dialogue_history = []

    feedback = await ai_coach_service.evaluate_audio(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        target_level=target_level,
        scenario=scenario,
        dialogue_history=dialogue_history,
    )
    await user_service.record_daily_eval(user_id)

    if dialogue_service and feedback.transcript and feedback.conversational_reply:
        try:
            await dialogue_service.add_turn(
                telegram_id=user_id,
                scenario=scenario,
                user_text=feedback.transcript,
                ai_text=feedback.conversational_reply,
            )
        except Exception as err:
            logger.warning("Failed to save dialogue turn: %s", err)

    summary = f"Score: {feedback.fluency_score}/100 | CEFR: {feedback.cefr_level}"
    await user_service.record_session(
        telegram_id=user_id,
        duration_seconds=duration,
        transcript=feedback.transcript,
        feedback_summary=summary,
        fluency_score=feedback.fluency_score,
        cefr_level=feedback.cefr_level,
        ielts_band=feedback.ielts_band,
        scenario=scenario,
    )

    if feedback.grammar_slips:
        await user_service.save_grammar_slips_to_vocab_bank(
            telegram_id=user_id,
            slips=feedback.grammar_slips,
        )

    streak_res = await user_service.process_daily_streak_and_xp(
        telegram_id=user_id,
        activity_type="voice_note",
    )

    score_stars = "⭐" * min(5, max(1, feedback.fluency_score // 20))
    if streak_res.freeze_used:
        streak_notice = f"🔥 `{streak_res.current_streak} Days Streak` (❄️ *Streak Freeze Digunakan!*) (+`{streak_res.xp_earned} XP`)"
    elif not streak_res.is_broken:
        streak_notice = f"🔥 `{streak_res.current_streak} Days Streak` (+`{streak_res.xp_earned} XP`)"
    else:
        streak_notice = f"🔥 `Streak Reset: Day 1` (+`{streak_res.xp_earned} XP`)"

    badge_alert = ""
    if streak_res.newly_unlocked_badges:
        from src.services.user_service import BADGES_CATALOG
        b_names = [BADGES_CATALOG.get(b, {}).get("title", b) for b in streak_res.newly_unlocked_badges]
        badge_alert = f"\n🎖️ **Badge Baru Terbuka:** {', '.join(b_names)}!"

    text = (
        f"📝 **Transcript:**\n"
        f"> *\"{feedback.transcript}\"*\n\n"
        f"🎯 **Fluency:** `{feedback.fluency_score}/100` {score_stars}\n"
        f"📊 **Proficiency:** `{feedback.cefr_level}` (IELTS Band ~`{feedback.ielts_band}`)\n"
        f"🎭 **Scenario:** `{scenario}`\n"
    )

    if feedback.grammar_slips:
        text += "\n🛠️ **Grammar Improvements (Saved to /review):**\n"
        for slip in feedback.grammar_slips:
            exp = f" (*{slip.explanation}*)" if slip.explanation else ""
            text += f"✏️ ~{slip.original}~ ➔ `{slip.correction}`{exp}\n"

    if feedback.vocabulary_suggestions:
        text += "\n💡 **Vocabulary Upgrades:**\n"
        for item in feedback.vocabulary_suggestions:
            text += f"✨ {item}\n"

    if feedback.pronunciation_notes:
        text += "\n🗣️ **Pronunciation Guidance:**\n"
        for item in feedback.pronunciation_notes:
            text += f"🗣️ {item}\n"

    text += (
        f"\n💬 **Coach Reply:**\n"
        f"{feedback.conversational_reply}\n\n"
        f"🏆 **Status:** {streak_notice}{badge_alert} | Total: `{streak_res.total_xp} XP`\n\n"
        f"🎙️ *Generating voice note reply...*"
    )

    await safe_edit_message_text(
        bot=bot,
        chat_id=chat_id,
        message_id=status_message_id,
        text=text,
        parse_mode="Markdown",
    )

    reply_audio = await tts_service.generate_speech(
        text=feedback.conversational_reply,
        voice=tts_voice,
        rate=tts_speed,
    )

    if reply_audio:
        voice_file = BufferedInputFile(reply_audio, filename="coach_reply.mp3")
        await bot.send_voice(
            chat_id=chat_id,
            voice=voice_file,
            caption="🗣️ *Audio reply from your AI Coach*",
            parse_mode="Markdown",
        )

    return {"status": "conversation_evaluated", "fluency": feedback.fluency_score}


async def process_voice_job(ctx: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Arq task entry point called by the Arq background worker."""
    bot = ctx["bot"]
    user_service = ctx["user_service"]
    ai_coach_service = ctx["ai_coach_service"]
    tts_service = ctx["tts_service"]
    dialogue_service = ctx.get("dialogue_service")

    try:
        return await execute_voice_job(
            job_data=job_data,
            bot=bot,
            user_service=user_service,
            ai_coach_service=ai_coach_service,
            tts_service=tts_service,
            dialogue_service=dialogue_service,
        )
    except Exception as err:
        logger.error("Error executing Arq background voice job: %s", err, exc_info=True)
        chat_id = job_data.get("chat_id")
        status_message_id = job_data.get("status_message_id")
        if chat_id and status_message_id:
            await safe_edit_message_text(
                bot=bot,
                chat_id=chat_id,
                message_id=status_message_id,
                text=(
                    "⚠️ **Evaluation Error:**\n\n"
                    "Could not complete background audio analysis. Please try sending another voice note!"
                ),
                parse_mode="Markdown",
            )
        raise


async def startup(ctx: Dict[str, Any]) -> None:
    """Initialize resources for the Arq background worker."""
    settings = load_settings()
    logger.info("Initializing Speaking Coach Arq Worker...")

    repo, db_conn = create_coach_repository(
        database_url=settings.database_url,
        database_path=settings.database_path,
    )
    await db_conn.init_schema()

    user_service = UserService(repository=repo)
    ai_coach_service = AICoachService(
        api_key=settings.gemini_api_key,
        model_name=settings.gemini_model,
    )
    tts_service = TTSService()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    ctx["bot"] = bot
    ctx["user_service"] = user_service
    ctx["ai_coach_service"] = ai_coach_service
    ctx["tts_service"] = tts_service
    ctx["repo"] = repo
    logger.info("Arq Worker initialized successfully.")


async def shutdown(ctx: Dict[str, Any]) -> None:
    """Graceful shutdown for the Arq worker."""
    logger.info("Shutting down Speaking Coach Arq Worker...")
    bot: Optional[Bot] = ctx.get("bot")
    if bot:
        await bot.session.close()


class WorkerSettings:
    """Arq Worker settings configuration."""
    functions = [process_voice_job]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 60

    settings = load_settings()
    if RedisSettings and settings.redis_url:
        redis_settings = RedisSettings.from_dsn(settings.redis_url)


if __name__ == "__main__":
    from arq import run_worker
    run_worker(WorkerSettings)
