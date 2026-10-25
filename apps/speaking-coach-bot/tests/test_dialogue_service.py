import unittest
from datetime import datetime, timedelta, timezone

from src.services.dialogue_service import DialogueService, SCENARIO_OPENINGS
from tests.test_ai_coach_service import MockCoachRepository


class TestDialogueService(unittest.IsolatedAsyncioTestCase):
    """Unit tests for Multi-Turn Dialogue Memory and Scenario Context."""

    def setUp(self):
        self.repo = MockCoachRepository()
        self.dialogue_service = DialogueService(repository=self.repo, redis_url="")

    async def test_record_and_fetch_history(self):
        """Verify recording turns into repository fallback and retrieving them."""
        uid = 12345
        scenario = "Job Interview"

        await self.dialogue_service.add_turn(
            telegram_id=uid,
            scenario=scenario,
            user_text="I have 5 years experience as a software engineer.",
            ai_text="That's impressive! Could you describe a challenging project you led?",
        )

        history = await self.dialogue_service.get_history(uid, scenario)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertIn("software engineer", history[0]["content"])
        self.assertEqual(history[1]["role"], "ai")
        self.assertIn("challenging project", history[1]["content"])

    async def test_clear_history(self):
        """Verify clearing history on /reset or scenario change."""
        uid = 12345
        scenario = "Job Interview"

        await self.dialogue_service.add_turn(
            telegram_id=uid,
            scenario=scenario,
            user_text="My name is Alice.",
            ai_text="Glad to have you, Alice.",
        )

        history_before = await self.dialogue_service.get_history(uid, scenario)
        self.assertEqual(len(history_before), 2)

        await self.dialogue_service.clear_history(uid, scenario)
        history_after = await self.dialogue_service.get_history(uid, scenario)
        self.assertEqual(len(history_after), 0)

    def test_scenario_openings(self):
        """Verify all standard scenarios have opening prompts."""
        self.assertIn("Free Conversation", SCENARIO_OPENINGS)
        self.assertIn("Job Interview", SCENARIO_OPENINGS)
        self.assertIn("Cafe & Dining", SCENARIO_OPENINGS)
        self.assertIn("Airport Immigration", SCENARIO_OPENINGS)
        self.assertIn("Tech Standup", SCENARIO_OPENINGS)
        self.assertTrue(len(self.dialogue_service.get_scenario_opening("Job Interview")) > 10)


if __name__ == "__main__":
    unittest.main()
