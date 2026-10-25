import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock
from src.services.ai_coach_service import (
    AICoachService,
    TenseEvaluationFeedback,
    get_tenses_catalog,
    get_tense_detail,
    TENSES_CATALOG,
)
from src.repositories.database import DatabaseConnection
from src.repositories.coach_repository import CoachRepository
from src.services.user_service import UserService
import tempfile
import os


class TestTensesFeature(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create temp sqlite database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_tenses.db")
        self.db_conn = DatabaseConnection(db_path=self.db_path)
        await self.db_conn.init_schema()
        self.repo = CoachRepository(db_path=self.db_path)
        self.user_service = UserService(repository=self.repo)

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    def test_catalog_structure(self):
        catalog = get_tenses_catalog()
        self.assertEqual(len(catalog), 7)
        expected_ids = [
            "pres_cont",
            "simple_pres",
            "simple_past",
            "past_cont",
            "pres_perf",
            "future",
            "conditionals",
        ]
        cat_ids = list(catalog.keys())
        self.assertEqual(cat_ids, expected_ids)

        for item in catalog.values():
            self.assertIn("title", item)
            self.assertIn("formula", item)
            self.assertIn("concept", item)
            self.assertIn("example_sentence", item)
            self.assertIn("speaking_scenario", item)
            self.assertTrue(len(item["title"]) > 0)
            self.assertTrue(len(item["formula"]) > 0)

    def test_get_tense_detail(self):
        detail = get_tense_detail("pres_cont")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["title"], "Present Continuous")

        invalid = get_tense_detail("non_existent_tense")
        self.assertIsNone(invalid)

    async def test_user_active_tense_drill_lifecycle(self):
        user_id = 12345678
        await self.repo.upsert_user(telegram_id=user_id, username="tense_learner", first_name="Tino")

        # Initial should be empty
        active = await self.user_service.get_active_tense_drill(user_id)
        self.assertIsNone(active)

        # Set active tense drill
        item = get_tense_detail("past_cont")
        await self.user_service.set_active_tense_drill(user_id, item)

        # Retrieve active tense drill
        active = await self.user_service.get_active_tense_drill(user_id)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], "past_cont")

        # Record tense exercise
        await self.user_service.record_tense_exercise(
            telegram_id=user_id,
            tense_id="past_cont",
            tense_title="Past Continuous",
            user_transcript="I was studying English when you called.",
            accuracy_score=95,
            is_target_tense_used=True,
            verb_form_analysis="I was studying English when you called me.",
            coaching_tip="Past continuous describes an ongoing action interrupted by a past event.",
        )

        # Clear drill
        await self.user_service.clear_active_tense_drill(user_id)
        active_cleared = await self.user_service.get_active_tense_drill(user_id)
        self.assertIsNone(active_cleared)

        # Check user profile still valid
        profile = await self.user_service.get_user_profile(user_id)
        self.assertEqual(profile["telegram_id"], user_id)

    async def test_evaluate_tense_exercise_mock(self):
        service = AICoachService(api_key="TEST_FAKE_KEY")
        mock_response = MagicMock()
        mock_response.text = (
            '{\n'
            '  "user_transcript": "I am working on my project right now.",\n'
            '  "tense_accuracy": 92,\n'
            '  "is_correct_tense": true,\n'
            '  "target_tense_used": "Present Continuous (am working)",\n'
            '  "corrected_sentence": "I am currently working on my project right now.",\n'
            '  "explanation": "Great use of Subject + am + Verb-ing for ongoing activity.",\n'
            '  "coaching_comment": "Excellent sentence structure and natural delivery!"\n'
            '}'
        )

        service.client.models.generate_content = MagicMock(return_value=mock_response)

        fake_audio = b"fake_ogg_bytes"
        feedback = await service.evaluate_tense_exercise(audio_bytes=fake_audio, tense_id="pres_cont")

        self.assertIsInstance(feedback, TenseEvaluationFeedback)
        self.assertEqual(feedback.tense_accuracy, 92)
        self.assertTrue(feedback.is_correct_tense)
        self.assertEqual(feedback.user_transcript, "I am working on my project right now.")
        self.assertIn("am working", feedback.target_tense_used)


if __name__ == "__main__":
    unittest.main()
