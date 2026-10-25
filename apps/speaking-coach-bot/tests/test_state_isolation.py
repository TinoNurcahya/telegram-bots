import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from src.repositories.database import DatabaseConnection
from src.repositories.coach_repository import CoachRepository
from src.services.user_service import UserService
from src.services.ai_coach_service import (
    AICoachService,
    get_tense_detail,
    get_phoneme_pair,
)
import tempfile
import os


class TestStateIsolationAndReset(unittest.IsolatedAsyncioTestCase):
    """Test suite ensuring zero routing collisions between concurrent learning modes."""

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_isolation.db")
        self.db_conn = DatabaseConnection(db_path=self.db_path)
        await self.db_conn.init_schema()
        self.repo = CoachRepository(db_path=self.db_path)
        self.user_service = UserService(repository=self.repo)

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_reset_all_active_drills_clears_everything(self):
        user_id = 999111
        await self.repo.upsert_user(telegram_id=user_id, username="multitasker", first_name="Alex")

        # 1. Setup multiple conflicting active states
        await self.user_service.set_active_shadow_target(user_id, "The weather is lovely today.")
        phoneme_drill = get_phoneme_pair("th_unvoiced_vs_s") or {"id": "th_unvoiced_vs_s", "label": "think vs sink"}
        await self.user_service.set_active_phoneme_drill(user_id, phoneme_drill)
        tense_item = get_tense_detail("pres_cont") or {"id": "pres_cont", "title": "Present Continuous"}
        await self.user_service.set_active_tense_drill(user_id, tense_item)

        dummy_questions = [
            {"part": 1, "text": "Do you enjoy cooking?", "type": "interview"},
            {"part": 2, "text": "Describe your house", "type": "cue_card", "cue_card": {"prompt": "house"}},
        ]
        ielts_id = await self.user_service.start_ielts_exam(
            telegram_id=user_id,
            exam_type="express",
            questions=dummy_questions,
        )

        # Verify all are active
        profile = await self.user_service.get_user_profile(user_id)
        self.assertEqual(profile.get("active_shadow_target"), "The weather is lovely today.")
        self.assertIsNotNone(await self.user_service.get_active_phoneme_drill(user_id))
        self.assertIsNotNone(await self.user_service.get_active_tense_drill(user_id))
        active_ielts = await self.user_service.get_active_ielts_session(user_id)
        self.assertIsNotNone(active_ielts)
        self.assertEqual(active_ielts["status"], "in_progress")

        # 2. Trigger reset_all_active_drills
        await self.user_service.reset_all_active_drills(user_id)

        # 3. Verify EVERYTHING is cleanly cleared
        updated_profile = await self.user_service.get_user_profile(user_id)
        self.assertEqual(updated_profile.get("active_shadow_target", ""), "")
        self.assertIsNone(await self.user_service.get_active_phoneme_drill(user_id))
        self.assertIsNone(await self.user_service.get_active_tense_drill(user_id))
        self.assertIsNone(await self.user_service.get_active_ielts_session(user_id))

    async def test_switching_to_tenses_cancels_ielts_and_shadowing(self):
        user_id = 999222
        await self.repo.upsert_user(telegram_id=user_id, username="switcher", first_name="Sam")

        # Start IELTS session
        dummy_q = [{"part": 1, "text": "Where are you from?", "type": "interview"}]
        await self.user_service.start_ielts_exam(user_id, "express", dummy_q)
        self.assertIsNotNone(await self.user_service.get_active_ielts_session(user_id))

        # User now switches to Tenses drill
        await self.user_service.reset_all_active_drills(user_id)
        tense_item = get_tense_detail("simple_past") or {"id": "simple_past", "title": "Simple Past"}
        await self.user_service.set_active_tense_drill(user_id, tense_item)

        # IELTS must be cancelled
        self.assertIsNone(await self.user_service.get_active_ielts_session(user_id))
        # Tense drill must be the only active mode
        active_tense = await self.user_service.get_active_tense_drill(user_id)
        self.assertIsNotNone(active_tense)
        self.assertEqual(active_tense["id"], "simple_past")

    async def test_switching_from_phonemes_to_shadowing(self):
        user_id = 999333
        await self.repo.upsert_user(telegram_id=user_id, username="accent_learner", first_name="Chris")

        # Start phoneme drill
        p_drill = get_phoneme_pair("p_vs_f") or {"id": "p_vs_f", "label": "pan vs fan"}
        await self.user_service.set_active_phoneme_drill(user_id, p_drill)
        self.assertIsNotNone(await self.user_service.get_active_phoneme_drill(user_id))

        # Switch to Shadowing
        await self.user_service.reset_all_active_drills(user_id)
        await self.user_service.set_active_shadow_target(user_id, "Practice makes perfect.")

        # Phoneme must be None, Shadowing must be active
        self.assertIsNone(await self.user_service.get_active_phoneme_drill(user_id))
        profile = await self.user_service.get_user_profile(user_id)
        self.assertEqual(profile.get("active_shadow_target"), "Practice makes perfect.")


if __name__ == "__main__":
    unittest.main()
