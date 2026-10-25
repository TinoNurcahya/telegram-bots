import unittest
from src.services.user_service import UserService
from tests.test_ai_coach_service import MockCoachRepository


class TestReferralSystem(unittest.IsolatedAsyncioTestCase):
    """Unit tests for Telegram Referral & Viral Growth system."""

    def setUp(self):
        self.repo = MockCoachRepository()
        self.user_service = UserService(repository=self.repo)

    async def test_successful_referral_and_rewards(self):
        """Verify normal referral granting rewards to both inviter and invitee."""
        inviter_id = 1001
        invitee_id = 2002

        await self.user_service.ensure_user(inviter_id, username="inviter_bob", first_name="Bob")
        await self.user_service.ensure_user(invitee_id, username="invitee_alice", first_name="Alice")

        res = await self.user_service.process_referral(inviter_id=inviter_id, invitee_id=invitee_id)
        self.assertIsNotNone(res)
        self.assertTrue(res["success"])

        # Check inviter profile: +1 freeze, +3 bonus quota, +50 XP
        inviter_prof = await self.user_service.get_user_profile(inviter_id)
        self.assertEqual(inviter_prof["streak_freeze_count"], 2)  # 1 initial + 1
        self.assertEqual(inviter_prof["bonus_quota"], 3)
        self.assertEqual(inviter_prof["total_xp"], 50)

        # Check invitee profile: +3 bonus quota, +25 XP
        invitee_prof = await self.user_service.get_user_profile(invitee_id)
        self.assertEqual(invitee_prof["bonus_quota"], 3)
        self.assertEqual(invitee_prof["total_xp"], 25)
        self.assertEqual(invitee_prof["invited_by"], inviter_id)

    async def test_bonus_quota_in_daily_check(self):
        """Verify check_daily_quota includes bonus_quota from referrals."""
        uid = 3003
        await self.user_service.ensure_user(uid, username="bonus_boy", first_name="Bonus")

        # Initially 10
        can_eval, used, limit = await self.user_service.check_daily_quota(uid)
        self.assertEqual(limit, 10)

        # Add bonus quota of +3
        await self.repo.add_bonus_quota(uid, 3)
        can_eval, used, limit = await self.user_service.check_daily_quota(uid)
        self.assertEqual(limit, 13)

    async def test_self_referral_rejected(self):
        """Verify users cannot refer themselves."""
        uid = 4004
        await self.user_service.ensure_user(uid, username="myself", first_name="Me")

        res = await self.user_service.process_referral(inviter_id=uid, invitee_id=uid)
        self.assertIsNone(res)

    async def test_duplicate_referral_rejected(self):
        """Verify invitee cannot be referred multiple times."""
        inviter1 = 5001
        inviter2 = 5002
        invitee = 6001

        await self.user_service.ensure_user(inviter1, "user1", "U1")
        await self.user_service.ensure_user(inviter2, "user2", "U2")
        await self.user_service.ensure_user(invitee, "target", "Target")

        res1 = await self.user_service.process_referral(inviter_id=inviter1, invitee_id=invitee)
        self.assertIsNotNone(res1)
        self.assertTrue(res1["success"])

        # Second referral attempt on same invitee should be rejected
        res2 = await self.user_service.process_referral(inviter_id=inviter2, invitee_id=invitee)
        self.assertIsNone(res2)

    async def test_referral_info_and_share_link(self):
        """Verify generation of referral link and share text."""
        uid = 7007
        await self.user_service.ensure_user(uid, "sharer", "Sharer")

        info = await self.user_service.get_referral_info(uid, bot_username="MyEnglishCoach2000_bot")
        self.assertIn("ref_7007", info["referral_link"])
        self.assertIn("MyEnglishCoach2000_bot", info["referral_link"])
        self.assertIn("https://t.me/MyEnglishCoach2000_bot?start=ref_7007", info["share_text"])
        self.assertEqual(info["total_referred"], 0)


if __name__ == "__main__":
    unittest.main()
