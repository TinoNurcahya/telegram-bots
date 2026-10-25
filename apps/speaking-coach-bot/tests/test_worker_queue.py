import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.worker.dispatcher import VoiceJobDispatcher
from src.worker.arq_worker import process_voice_job, execute_voice_job
from src.services.ai_coach_service import SpeakingFeedback, ShadowingFeedback, PhonemeFeedback


class TestWorkerQueue(unittest.IsolatedAsyncioTestCase):
    """Unit tests for Arq VoiceJobDispatcher and background worker logic."""

    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_bot.edit_message_text = AsyncMock()
        self.mock_bot.send_voice = AsyncMock()
        self.mock_bot.send_message = AsyncMock()
        self.mock_bot.session = MagicMock()
        self.mock_bot.session.close = AsyncMock()

        self.mock_user_service = MagicMock()
        self.mock_user_service.record_session = AsyncMock()
        self.mock_user_service.save_grammar_slips_to_vocab_bank = AsyncMock()
        self.mock_user_service.check_daily_quota = AsyncMock(return_value=(True, 0, 10))
        self.mock_user_service.record_daily_eval = AsyncMock(return_value=1)
        streak_result = MagicMock()
        streak_result.current_streak = 3
        streak_result.is_broken = False
        streak_result.xp_earned = 15
        streak_result.total_xp = 75
        streak_result.freeze_used = False
        streak_result.newly_unlocked_badges = []
        self.mock_user_service.process_daily_streak_and_xp = AsyncMock(return_value=streak_result)

        self.mock_ai_coach_service = MagicMock()
        self.mock_tts_service = MagicMock()
        self.mock_tts_service.generate_speech = AsyncMock(return_value=b"fake-mp3-bytes")

    async def test_dispatcher_enqueues_to_arq_when_available(self):
        mock_arq_pool = MagicMock()
        mock_arq_pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="job-12345"))

        dispatcher = VoiceJobDispatcher(arq_pool=mock_arq_pool)
        job_data = {"user_id": 12345, "chat_id": 999, "status_message_id": 1, "audio_bytes": b"fake"}

        await dispatcher.dispatch(
            job_data=job_data,
            bot=self.mock_bot,
            user_service=self.mock_user_service,
            ai_coach_service=self.mock_ai_coach_service,
            tts_service=self.mock_tts_service,
        )

        mock_arq_pool.enqueue_job.assert_called_once_with("process_voice_job", job_data)

    async def test_dispatcher_falls_back_to_in_process_when_pool_is_none(self):
        dispatcher = VoiceJobDispatcher(arq_pool=None)
        job_data = {
            "user_id": 12345,
            "chat_id": 999,
            "status_message_id": 1,
            "audio_bytes": b"fake",
            "scenario": "Cafe & Dining",
            "target_level": "Intermediate",
            "tts_voice": "en-US-JennyNeural",
        }

        self.mock_ai_coach_service.evaluate_audio = AsyncMock(
            return_value=SpeakingFeedback(
                transcript="I would like a coffee",
                fluency_score=85,
                cefr_level="B2",
                ielts_band=6.5,
                grammar_slips=[],
                vocabulary_suggestions=["I would like a cappuccino"],
                pronunciation_notes=[],
                conversational_reply="Sure! What size would you prefer?",
            )
        )

        await dispatcher.dispatch(
            job_data=job_data,
            bot=self.mock_bot,
            user_service=self.mock_user_service,
            ai_coach_service=self.mock_ai_coach_service,
            tts_service=self.mock_tts_service,
        )

        self.mock_ai_coach_service.evaluate_audio.assert_called_once()
        self.mock_user_service.record_session.assert_called_once()
        self.mock_bot.edit_message_text.assert_called_once()
        self.mock_bot.send_voice.assert_called_once()

    async def test_execute_voice_job_shadowing_branch(self):
        self.mock_ai_coach_service.evaluate_shadowing_attempt = AsyncMock(
            return_value=ShadowingFeedback(
                transcribed_text="The quick brown fox",
                match_score=92,
                mispronounced_words=[],
                cadence_feedback="Excellent rhythm and cadence",
                praise_message="Well done!",
            )
        )
        self.mock_user_service.clear_active_shadow_target = AsyncMock()
        self.mock_user_service.record_shadowing_history = AsyncMock()

        job_data = {
            "user_id": 12345,
            "chat_id": 999,
            "status_message_id": 1,
            "audio_bytes": b"fake",
            "active_shadow_target": "The quick brown fox jumps",
        }

        result = await execute_voice_job(
            job_data=job_data,
            bot=self.mock_bot,
            user_service=self.mock_user_service,
            ai_coach_service=self.mock_ai_coach_service,
            tts_service=self.mock_tts_service,
        )

        self.assertEqual(result["status"], "shadowing_evaluated")
        self.assertEqual(result["score"], 92)
        self.mock_user_service.clear_active_shadow_target.assert_called_once_with(12345)
        self.mock_user_service.record_shadowing_history.assert_called_once()
        self.mock_bot.edit_message_text.assert_called_once()


if __name__ == "__main__":
    unittest.main()
