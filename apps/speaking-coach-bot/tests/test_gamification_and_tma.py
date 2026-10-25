import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from src.services.user_service import (
    UserService,
    calculate_user_level,
    BADGES_CATALOG,
    LEVEL_TIERS,
)
from tests.test_ai_coach_service import MockCoachRepository


class TestGamificationAndTMA(unittest.IsolatedAsyncioTestCase):
    """Unit tests for Phase 3/4 Gamification, Streak Freeze, Badges, Quota, and TMA Dashboard."""

    def setUp(self):
        self.repo = MockCoachRepository()
        self.user_service = UserService(repository=self.repo)

    def test_level_calculation(self):
        # Novice (0 XP)
        lvl1 = calculate_user_level(0)
        self.assertEqual(lvl1["level"], 1)
        self.assertEqual(lvl1["title"], "Novice Explorer")
        self.assertEqual(lvl1["next_level"], 2)

        # Level 4: Active Conversationalist (350 XP)
        lvl4 = calculate_user_level(350)
        self.assertEqual(lvl4["level"], 4)
        self.assertEqual(lvl4["title"], "Active Conversationalist")
        self.assertEqual(lvl4["next_level"], 5)

        # Max Level (3500 XP)
        lvl10 = calculate_user_level(3500)
        self.assertEqual(lvl10["level"], 10)
        self.assertEqual(lvl10["title"], "Native Master")
        self.assertEqual(lvl10["progress_percent"], 100)

    async def test_streak_freeze_protection(self):
        uid = 991
        today_utc = datetime.now(timezone.utc).date()
        two_days_ago = (today_utc - timedelta(days=2)).isoformat()

        # Setup user with 5-day streak whose last practice was 2 days ago (missed yesterday)
        await self.user_service.ensure_user(uid, "frosty", "Frosty")
        self.repo.users[uid]["current_streak"] = 5
        self.repo.users[uid]["max_streak"] = 5
        self.repo.users[uid]["last_practice_date"] = two_days_ago
        self.repo.users[uid]["streak_freeze_count"] = 1

        # Practice today -> Streak freeze should protect and increment streak to 6!
        res = await self.user_service.process_daily_streak_and_xp(uid, activity_type="voice_note")

        self.assertTrue(res.freeze_used, "Expected streak freeze to be used")
        self.assertEqual(res.current_streak, 6, "Streak should be preserved and incremented")
        self.assertEqual(self.repo.users[uid]["streak_freeze_count"], 0, "Freeze count should be decremented")

    async def test_freemium_quota_limit_and_premium_bypass(self):
        uid = 992
        await self.user_service.ensure_user(uid, "freeuser", "Free")

        # Initial: 0 used
        can_eval, used, limit = await self.user_service.check_daily_quota(uid)
        self.assertTrue(can_eval)
        self.assertEqual(used, 0)
        self.assertEqual(limit, 10)

        # Use 10 evaluations
        for _ in range(10):
            await self.user_service.record_daily_eval(uid)

        # 11th evaluation should be blocked
        can_eval, used, limit = await self.user_service.check_daily_quota(uid)
        self.assertFalse(can_eval)
        self.assertEqual(used, 10)

        # Upgrade to premium
        await self.user_service.grant_premium(uid)
        can_eval, _, _ = await self.user_service.check_daily_quota(uid)
        self.assertTrue(can_eval, "Premium user should bypass quota limit")

    async def test_badge_awards(self):
        uid = 993
        await self.user_service.ensure_user(uid, "badgeboy", "Badge")

        # 1. First Step badge after 1 practice note
        self.repo.users[uid]["total_voice_notes"] = 1
        new_badges = await self.user_service.check_and_award_badges(uid)
        self.assertIn("FIRST_STEP", new_badges)

        # 2. IELTS high band
        new_ielts = await self.user_service.check_and_award_badges(uid, context_event="ielts:7.5")
        self.assertIn("IELTS_CANDIDATE", new_ielts)
        self.assertIn("IELTS_HIGH_BAND", new_ielts)

    async def test_tma_dashboard_data_structure(self):
        uid = 994
        await self.user_service.ensure_user(uid, "tmaviewer", "TMA")
        self.repo.users[uid]["total_xp"] = 320
        self.repo.users[uid]["current_streak"] = 4

        data = await self.user_service.get_tma_dashboard_data(uid)

        self.assertIn("user", data)
        self.assertIn("level", data)
        self.assertIn("radar", data)
        self.assertIn("activity_dates", data)
        self.assertIn("badges", data)
        self.assertIn("recent_sessions", data)

        self.assertEqual(data["level"]["level"], 4)
        self.assertEqual(data["user"]["current_streak"], 4)
    async def test_free_trial_one_time_claim(self):
        uid = 995
        await self.user_service.ensure_user(uid, "trialuser", "Trial")

        # 1. First claim should succeed
        res = await self.user_service.claim_free_trial(uid)
        self.assertTrue(res["success"])
        self.assertEqual(res["days"], 7)

        profile = await self.user_service.get_user_profile(uid)
        self.assertEqual(profile["is_premium"], 1)
        self.assertEqual(profile["premium_tier"], "trial_7d")
        self.assertEqual(profile["has_used_trial"], 1)

        # 2. Second claim must be blocked
        res2 = await self.user_service.claim_free_trial(uid)
        self.assertFalse(res2["success"])

    async def test_duration_subscription_stacking(self):
        uid = 996
        await self.user_service.ensure_user(uid, "stacker", "Stacker")

        # 1 Month plan
        res1 = await self.user_service.grant_subscription(uid, "plan_1m")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["tier"], "1 Bulan")

        profile = await self.user_service.get_user_profile(uid)
        self.assertEqual(profile["is_premium"], 1)
        self.assertGreaterEqual(profile["days_left"], 29)
        self.assertEqual(profile["streak_freeze_count"], 4)  # 1 initial + 3 bonus

        # 3 Month plan stacking
        res2 = await self.user_service.grant_subscription(uid, "plan_3m")
        self.assertTrue(res2["success"])

        # Upgrade to Lifetime
        res3 = await self.user_service.grant_subscription(uid, "plan_lifetime")
        self.assertTrue(res3["success"])
        self.assertTrue(res3["is_lifetime"])

        profile_final = await self.user_service.get_user_profile(uid)
        self.assertTrue(profile_final["is_lifetime"])

    async def test_voice_speed_configuration(self):
        uid = 997
        await self.user_service.ensure_user(uid, "speedster", "Speedster")

        # Default speed is +0% (1.0x)
        profile = await self.user_service.get_user_profile(uid)
        self.assertEqual(profile.get("tts_speed"), "+0%")

        # Update speed to -25% (0.75x)
        await self.user_service.update_tts_speed(uid, "-25%")
        profile_slow = await self.user_service.get_user_profile(uid)
        self.assertEqual(profile_slow.get("tts_speed"), "-25%")

        # Update speed to +15% (1.15x)
        await self.user_service.update_tts_speed(uid, "+15%")
        profile_fast = await self.user_service.get_user_profile(uid)
        self.assertEqual(profile_fast.get("tts_speed"), "+15%")


if __name__ == "__main__":
    unittest.main()


