import io
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from src.services.user_service import UserService
from src.bot.handlers.monetization import process_pre_checkout, process_successful_payment, PLANS
from src.bot.handlers.voice import handle_voice_message
from src.worker.arq_worker import execute_voice_job
from tests.test_ai_coach_service import MockCoachRepository


class TestSecurityAndQAQC(unittest.IsolatedAsyncioTestCase):
    """Aggressive QA/QC & Security Test Suite covering anti-tamper, DoS, and logic boundaries."""

    def setUp(self):
        self.repo = MockCoachRepository()
        self.user_service = UserService(repository=self.repo)

    # -------------------------------------------------------------
    # 1. Telegram Stars Anti-Tampering & Financial Verification
    # -------------------------------------------------------------
    async def test_pre_checkout_rejects_non_xtr_currency(self):
        """Reject pre-checkout if currency is spoofed (not XTR)."""
        query = MagicMock()
        query.currency = "USD"
        query.invoice_payload = "plan_1m"
        query.total_amount = 40
        query.from_user.id = 1111
        query.answer = AsyncMock()

        await process_pre_checkout(query)
        query.answer.assert_awaited_once_with(
            ok=False,
            error_message="Mata uang transaksi tidak valid. Hanya Telegram Stars (XTR) yang didukung.",
        )

    async def test_pre_checkout_rejects_unknown_payload(self):
        """Reject pre-checkout if payload does not exist in PLANS catalog."""
        query = MagicMock()
        query.currency = "XTR"
        query.invoice_payload = "hack_unlimited_free"
        query.total_amount = 0
        query.from_user.id = 1111
        query.answer = AsyncMock()

        await process_pre_checkout(query)
        query.answer.assert_awaited_once_with(
            ok=False,
            error_message="Paket langganan tidak valid atau telah kedaluwarsa.",
        )

    async def test_pre_checkout_rejects_price_tampering(self):
        """Reject pre-checkout if Stars price is manipulated (e.g. 1 Star for Lifetime)."""
        query = MagicMock()
        query.currency = "XTR"
        query.invoice_payload = "plan_lifetime"
        query.total_amount = 1  # Attacker attempts to pay 1 Star instead of 150
        query.from_user.id = 1111
        query.answer = AsyncMock()

        await process_pre_checkout(query)
        query.answer.assert_awaited_once_with(
            ok=False,
            error_message="Jumlah Telegram Stars tidak cocok (diharapkan 150 Stars).",
        )

    async def test_pre_checkout_approves_valid_plans(self):
        """Approve legitimate pre-checkouts for 1m, 3m, and lifetime."""
        for plan_key, plan_info in PLANS.items():
            query = MagicMock()
            query.currency = "XTR"
            query.invoice_payload = plan_info["payload"]
            query.total_amount = plan_info["stars"]
            query.from_user.id = 2222
            query.answer = AsyncMock()

            await process_pre_checkout(query)
            query.answer.assert_awaited_once_with(ok=True)

    async def test_successful_payment_rejects_tampered_payload_or_amount(self):
        """Refuse to grant subscription if successful_payment contains tampered amount."""
        user_id = 3333
        await self.user_service.ensure_user(user_id, "attacker", "Attacker")

        message = MagicMock()
        message.from_user.id = user_id
        message.successful_payment.currency = "XTR"
        message.successful_payment.invoice_payload = "plan_lifetime"
        message.successful_payment.total_amount = 5  # Fraudulent amount
        message.answer = AsyncMock()

        await process_successful_payment(message, self.user_service)

        # Profile must NOT be upgraded
        profile = await self.user_service.get_user_profile(user_id)
        self.assertEqual(profile["is_premium"], 0)
        message.answer.assert_awaited_once()
        self.assertIn("tidak cocok dengan sistem kami", message.answer.call_args[0][0])

    async def test_successful_payment_fulfills_verified_purchase(self):
        """Grant 30-day subscription when 40 Stars payment for plan_1m is verified."""
        user_id = 4444
        await self.user_service.ensure_user(user_id, "buyer", "Buyer")

        message = MagicMock()
        message.from_user.id = user_id
        message.successful_payment.currency = "XTR"
        message.successful_payment.invoice_payload = "plan_1m"
        message.successful_payment.total_amount = 40
        message.answer = AsyncMock()

        await process_successful_payment(message, self.user_service)

        profile = await self.user_service.get_user_profile(user_id)
        self.assertEqual(profile["is_premium"], 1)
        self.assertGreaterEqual(profile["days_left"], 29)
        self.assertEqual(profile["premium_tier"], "1 Bulan")

    # -------------------------------------------------------------
    # 2. DoS & Resource Exhaustion Defense (Audio Guards)
    # -------------------------------------------------------------
    async def test_voice_guard_duration_too_short(self):
        """Reject voice note with duration < 1s before download."""
        bot = MagicMock()
        bot.download = AsyncMock()
        message = MagicMock()
        message.voice.duration = 0
        message.voice.file_size = 1000
        message.audio = None
        message.reply = AsyncMock()

        ai_coach_service = MagicMock()
        tts_service = MagicMock()

        await handle_voice_message(
            message=message,
            bot=bot,
            user_service=self.user_service,
            ai_coach_service=ai_coach_service,
            tts_service=tts_service,
        )

        bot.download.assert_not_awaited()
        message.reply.assert_awaited_once()
        self.assertIn("Rekaman Terlalu Singkat", message.reply.call_args[0][0])

    async def test_voice_guard_duration_too_long(self):
        """Reject voice note exceeding 90 seconds."""
        bot = MagicMock()
        bot.download = AsyncMock()
        message = MagicMock()
        message.voice.duration = 120  # 2 minutes
        message.voice.file_size = 10000
        message.audio = None
        message.reply = AsyncMock()

        ai_coach_service = MagicMock()
        tts_service = MagicMock()

        await handle_voice_message(
            message=message,
            bot=bot,
            user_service=self.user_service,
            ai_coach_service=ai_coach_service,
            tts_service=tts_service,
        )

        bot.download.assert_not_awaited()
        message.reply.assert_awaited_once()
        self.assertIn("Durasi Terlalu Panjang", message.reply.call_args[0][0])

    async def test_voice_guard_file_size_exceeded(self):
        """Reject audio file larger than 10MB."""
        bot = MagicMock()
        bot.download = AsyncMock()
        message = MagicMock()
        message.voice.duration = 45
        message.voice.file_size = 15 * 1024 * 1024  # 15 MB
        message.audio = None
        message.reply = AsyncMock()

        ai_coach_service = MagicMock()
        tts_service = MagicMock()

        await handle_voice_message(
            message=message,
            bot=bot,
            user_service=self.user_service,
            ai_coach_service=ai_coach_service,
            tts_service=tts_service,
        )

        bot.download.assert_not_awaited()
        message.reply.assert_awaited_once()
        self.assertIn("Ukuran File Melebihi Batas", message.reply.call_args[0][0])

    # -------------------------------------------------------------
    # 3. Quota Resilience & Atomic Quota Deduction
    # -------------------------------------------------------------
    async def test_quota_exceeded_no_name_error(self):
        """Verify quota exhaustion returns cleanly without NameError: profile."""
        user_id = 5555
        await self.user_service.ensure_user(user_id, "quota_tester", "Tester")

        # Exhaust 10 evaluations
        for _ in range(10):
            await self.user_service.record_daily_eval(user_id)

        bot = MagicMock()
        bot.edit_message_text = AsyncMock()
        ai_coach = MagicMock()
        tts = MagicMock()

        job_data = {
            "chat_id": 5555,
            "user_id": user_id,
            "status_message_id": 999,
            "audio_bytes": b"dummy_audio",
            "mime_type": "audio/ogg",
            "duration": 5,
        }

        # Must not raise NameError
        result = await execute_voice_job(
            job_data=job_data,
            bot=bot,
            user_service=self.user_service,
            ai_coach_service=ai_coach,
            tts_service=tts,
        )

        self.assertEqual(result.get("status"), "quota_exceeded")
        bot.edit_message_text.assert_awaited_once()
        self.assertIn("Batas Latihan Harian Tercapai", bot.edit_message_text.call_args[1]["text"])

    async def test_quota_not_incremented_when_gemini_fails(self):
        """Ensure daily quota is not consumed if Gemini throws an error."""
        user_id = 6666
        await self.user_service.ensure_user(user_id, "unlucky_user", "User")

        # Initial used count: 0
        _, used_before, _ = await self.user_service.check_daily_quota(user_id)
        self.assertEqual(used_before, 0)

        bot = MagicMock()
        bot.edit_message_text = AsyncMock()
        ai_coach = MagicMock()
        ai_coach.evaluate_audio = AsyncMock(side_effect=RuntimeError("Gemini 503 Overloaded"))
        tts = MagicMock()

        job_data = {
            "chat_id": 6666,
            "user_id": user_id,
            "status_message_id": 888,
            "audio_bytes": b"valid_audio",
            "mime_type": "audio/ogg",
            "duration": 5,
        }

        with self.assertRaises(RuntimeError):
            await execute_voice_job(
                job_data=job_data,
                bot=bot,
                user_service=self.user_service,
                ai_coach_service=ai_coach,
                tts_service=tts,
            )

        # Quota must still be 0 because AI failed!
        _, used_after, _ = await self.user_service.check_daily_quota(user_id)
        self.assertEqual(used_after, 0, "Quota was unfairly deducted when AI failed!")

    # -------------------------------------------------------------
    # 5. AI Spoken Voice Persistence & Mode Alignment
    # -------------------------------------------------------------
    async def test_male_voice_persistence_in_worker(self):
        """Worker must honor user's chosen male voice even if job_data had default female voice."""
        user_id = 5555
        await self.user_service.ensure_user(user_id)
        await self.user_service.update_tts_voice(user_id, "en-US-GuyNeural")

        bot = MagicMock()
        bot.send_voice = AsyncMock()

        ai_coach = MagicMock()
        feedback = MagicMock()
        feedback.transcript = "Hello coach"
        feedback.fluency_score = 85
        feedback.cefr_level = "B2"
        feedback.ielts_band = 6.5
        feedback.grammar_slips = []
        feedback.vocabulary_suggestions = []
        feedback.pronunciation_notes = []
        feedback.conversational_reply = "Great job! How was your morning?"
        ai_coach.evaluate_audio = AsyncMock(return_value=feedback)

        tts = MagicMock()
        tts.generate_speech = AsyncMock(return_value=b"male_audio_bytes")

        # job_data intentionally carries stale default voice
        job_data = {
            "chat_id": 5555,
            "user_id": user_id,
            "status_message_id": 99,
            "audio_bytes": b"voice",
            "mime_type": "audio/ogg",
            "duration": 5,
            "target_level": "Intermediate",
            "scenario": "Free Conversation",
            "tts_voice": "en-US-JennyNeural",  # Stale job data
            "tts_speed": "+0%",
        }

        with patch("src.worker.arq_worker.safe_edit_message_text", new_callable=AsyncMock):
            await execute_voice_job(
                job_data=job_data,
                bot=bot,
                user_service=self.user_service,
                ai_coach_service=ai_coach,
                tts_service=tts,
            )

        # Worker must have prioritized active database profile voice (Guy), NOT Jenny!
        tts.generate_speech.assert_awaited_once_with(
            text="Great job! How was your morning?",
            voice="en-US-GuyNeural",
            rate="+0%",
        )

    async def test_cb_shadow_uses_clicking_user_profile_not_bot_id(self):
        """Callback button for Shadowing must use the clicking learner's profile, not the Bot's ID."""
        from src.bot.handlers.common import cb_start_shadow

        user_id = 7777
        await self.user_service.ensure_user(user_id)
        await self.user_service.update_tts_voice(user_id, "en-US-GuyNeural")

        query = MagicMock()
        query.from_user.id = user_id
        query.answer = AsyncMock()

        # query.message is sent by the Bot
        message = MagicMock()
        message.from_user.id = 8929232068  # Bot ID
        message.reply_voice = AsyncMock()
        query.message = message

        ai_coach = MagicMock()
        ai_coach.get_shadowing_target = MagicMock(return_value="Consistency is the key to fluency.")

        tts = MagicMock()
        tts.generate_speech = AsyncMock(return_value=b"shadow_audio")

        await cb_start_shadow(
            query=query,
            bot=MagicMock(),
            user_service=self.user_service,
            ai_coach_service=ai_coach,
            tts_service=tts,
        )

        # Voice used MUST be Guy (user's chosen voice), NOT Jenny (fallback from bot ID)
        tts.generate_speech.assert_awaited_once_with(
            "Consistency is the key to fluency.",
            voice="en-US-GuyNeural",
            rate="+0%",
        )

        # Active target must be stored under user_id, NOT bot ID
        profile = await self.user_service.get_user_profile(user_id)
        self.assertEqual(profile["active_shadow_target"], "Consistency is the key to fluency.")

    async def test_ielts_step_uses_user_configured_voice(self):
        """IELTS examiner questions must adopt the user's preferred TTS voice."""
        from src.bot.handlers.ielts_mock import send_ielts_step

        user_id = 6666
        await self.user_service.ensure_user(user_id)
        await self.user_service.update_tts_voice(user_id, "en-US-GuyNeural")

        target_msg = MagicMock()
        target_msg.chat.id = user_id
        target_msg.answer_voice = AsyncMock()

        tts = MagicMock()
        tts.synthesize_speech = AsyncMock(return_value=b"ielts_audio")

        session = {
            "session_id": "mock_sess",
            "telegram_id": user_id,
            "questions": [{"text": "Do you prefer studying alone or in a group?", "part": 1, "part_title": "Part 1"}],
        }

        await send_ielts_step(
            target_msg=target_msg,
            user_service=self.user_service,
            tts_service=tts,
            session=session,
            step_index=0,
        )

        tts.synthesize_speech.assert_awaited_once_with(
            text="Do you prefer studying alone or in a group?",
            voice="en-US-GuyNeural",
            rate="+0%",
        )


class TestNativeProgressDashboard(unittest.IsolatedAsyncioTestCase):
    """Unit tests for 100% Native Telegram Progress Card and Navigation Keyboards."""

    def setUp(self):
        self.repo = MockCoachRepository()
        self.user_service = UserService(repository=self.repo)

    def test_generate_text_progress_bar(self):
        """Verify ASCII progress bar formatting at different percentages."""
        from src.bot.handlers.common import generate_text_progress_bar

        self.assertEqual(generate_text_progress_bar(0), "░░░░░░░░░░")
        self.assertEqual(generate_text_progress_bar(50), "█████░░░░░")
        self.assertEqual(generate_text_progress_bar(100), "██████████")

    async def test_render_native_progress_card(self):
        """Verify native card aggregates XP, level, streak, and badges."""
        from src.bot.handlers.common import render_native_progress_card

        user_id = 9876
        await self.user_service.ensure_user(user_id, first_name="Clara")
        await self.repo.update_user_streak_and_xp(
            telegram_id=user_id,
            current_streak=7,
            max_streak=10,
            practice_date="2026-10-25",
            total_xp=450,
        )

        card_text = await render_native_progress_card(user_id, self.user_service)

        self.assertIn("KARTU PROFIL & STATISTIK BELAJAR AI", card_text)
        self.assertIn("**Learner:** Clara", card_text)
        self.assertIn("450 XP", card_text)
        self.assertIn("7 Hari", card_text)

    async def test_cmd_progress_sends_native_card_and_markup(self):
        """Verify /progress command sends formatted native card with interactive keyboard."""
        from src.bot.handlers.common import cmd_progress

        user_id = 9876
        await self.user_service.ensure_user(user_id, first_name="Clara")

        message = MagicMock()
        message.from_user.id = user_id
        message.answer = AsyncMock()

        await cmd_progress(message, self.user_service)

        message.answer.assert_awaited_once()
        args, kwargs = message.answer.call_args
        self.assertIn("KARTU PROFIL & STATISTIK BELAJAR AI", args[0])
        self.assertEqual(kwargs.get("parse_mode"), "Markdown")
        self.assertIsNotNone(kwargs.get("reply_markup"))

    async def test_cb_refresh_progress_edits_card_in_place(self):
        """Verify refresh button updates progress card in-place."""
        from src.bot.handlers.common import cb_refresh_progress

        user_id = 9876
        await self.user_service.ensure_user(user_id, first_name="Clara")

        query = MagicMock()
        query.from_user.id = user_id
        query.answer = AsyncMock()
        message = MagicMock()
        message.edit_text = AsyncMock()
        query.message = message

        await cb_refresh_progress(query, self.user_service)

        query.answer.assert_awaited_once()
        message.edit_text.assert_awaited_once()
        args, kwargs = message.edit_text.call_args
        self.assertIn("KARTU PROFIL & STATISTIK BELAJAR AI", kwargs.get("text"))

    async def test_voice_preflight_quota_exhausted_rejects_before_download(self):
        """Pre-flight check in voice.py must reject and NOT download audio if quota exhausted."""
        user_id = 8881
        await self.user_service.ensure_user(user_id, "exhausted_user", "Exhausted")
        for _ in range(10):
            await self.user_service.record_daily_eval(user_id)

        bot = MagicMock()
        bot.download = AsyncMock()
        message = MagicMock()
        message.from_user.id = user_id
        message.voice.duration = 10
        message.voice.file_size = 50000
        message.voice.file_id = "test_file_id"
        message.audio = None
        message.reply = AsyncMock()

        ai_coach = MagicMock()
        tts = MagicMock()

        await handle_voice_message(
            message=message,
            bot=bot,
            user_service=self.user_service,
            ai_coach_service=ai_coach,
            tts_service=tts,
        )

        bot.download.assert_not_awaited()
        message.reply.assert_awaited_once()
        self.assertIn("Batas Latihan Harian Tercapai", message.reply.call_args[0][0])

    async def test_voice_ielts_session_bypasses_quota_exhaustion(self):
        """Active IELTS session allows voice note processing even when daily quota is exhausted."""
        user_id = 8882
        await self.user_service.ensure_user(user_id, "ielts_taker", "Candidate")
        for _ in range(10):
            await self.user_service.record_daily_eval(user_id)

        # Set active IELTS exam
        await self.user_service.start_ielts_exam(
            telegram_id=user_id,
            exam_type="express",
            questions=[{"step_index": 0, "part": 1, "text": "Where do you live?"}],
        )

        bot = MagicMock()
        bot.download = AsyncMock()
        message = MagicMock()
        message.chat.id = user_id
        message.from_user.id = user_id
        message.voice.duration = 15
        message.voice.file_size = 50000
        message.voice.file_id = "ielts_file_id"
        message.voice.mime_type = "audio/ogg"
        message.audio = None
        status_msg = MagicMock()
        status_msg.message_id = 123
        message.reply = AsyncMock(return_value=status_msg)

        ai_coach = MagicMock()
        ai_coach.transcribe_voice_note = AsyncMock(return_value="I live in Jakarta.")
        tts = MagicMock()
        tts.synthesize_speech = AsyncMock(return_value=b"tts_audio")

        dispatcher = MagicMock()
        dispatcher.dispatch = AsyncMock()

        await handle_voice_message(
            message=message,
            bot=bot,
            user_service=self.user_service,
            ai_coach_service=ai_coach,
            tts_service=tts,
            voice_dispatcher=dispatcher,
        )

        # bot.download MUST be called because quota check was bypassed for IELTS!
        bot.download.assert_awaited_once()
        dispatcher.dispatch.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
