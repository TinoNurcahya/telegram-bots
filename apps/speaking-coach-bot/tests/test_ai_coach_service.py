import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from src.repositories.coach_repository import ICoachRepository
from src.services.user_service import UserService
from src.services.ai_coach_service import (
    AICoachService,
    SpeakingFeedback,
    ShadowingFeedback,
    IELTSMockFeedback,
    PhonemeFeedback,
    GrammarSlip,
    IELTS_QUESTION_PACKS,
    get_phoneme_categories,
    get_phoneme_pairs_by_category,
    get_phoneme_pair,
    get_random_phoneme_pair,
)
from src.services.tts_service import TTSService, AVAILABLE_VOICES
from src.services.reminder_service import get_random_reminder_message, PERSONA_COLLECTION


class MockCoachRepository(ICoachRepository):
    """In-memory mock repository for unit testing."""

    def __init__(self):
        self.users: Dict[int, Dict[str, Any]] = {}
        self.sessions: List[Dict[str, Any]] = []
        self.vocab_bank: List[Dict[str, Any]] = []
        self.shadowing_history: List[Dict[str, Any]] = []
        self.ielts_sessions: List[Dict[str, Any]] = []
        self.ielts_results: List[Dict[str, Any]] = []
        self.phoneme_drills: List[Dict[str, Any]] = []
        self.dialogue_turns: List[Dict[str, Any]] = []
        self.referrals: List[Dict[str, Any]] = []

    async def upsert_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> None:
        if telegram_id not in self.users:
            self.users[telegram_id] = {
                "telegram_id": telegram_id,
                "username": username,
                "first_name": first_name,
                "target_level": "Intermediate",
                "active_scenario": "Free Conversation",
                "tts_voice": "en-US-JennyNeural",
                "total_voice_notes": 0,
                "current_streak": 0,
                "max_streak": 0,
                "last_practice_date": "",
                "total_xp": 0,
                "active_shadow_target": "",
                "active_phoneme_target": "",
                "reminder_time": "20:00",
                "reminder_enabled": 1,
                "reminder_timezone": "Asia/Jakarta",
                "last_reminded_date": "",
                "bonus_quota": 0,
                "invited_by": 0,
                "streak_freeze_count": 1,
                "is_premium": 0,
                "premium_tier": "",
                "premium_until": "",
                "has_used_trial": 0,
            }

    async def set_user_level(self, telegram_id: int, level: str) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["target_level"] = level

    async def set_user_scenario(self, telegram_id: int, scenario: str) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["active_scenario"] = scenario

    async def set_user_tts_voice(self, telegram_id: int, voice: str) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["tts_voice"] = voice

    async def set_user_tts_speed(self, telegram_id: int, speed: str) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["tts_speed"] = speed

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        return self.users.get(telegram_id)

    async def update_user_streak_and_xp(
        self,
        telegram_id: int,
        current_streak: int,
        max_streak: int,
        practice_date: str,
        total_xp: int,
    ) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["current_streak"] = current_streak
            self.users[telegram_id]["max_streak"] = max_streak
            self.users[telegram_id]["last_practice_date"] = practice_date
            self.users[telegram_id]["total_xp"] = total_xp

    async def set_active_shadow_target(self, telegram_id: int, target_text: str) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["active_shadow_target"] = target_text

    async def clear_active_shadow_target(self, telegram_id: int) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["active_shadow_target"] = ""

    async def record_shadowing_attempt(
        self,
        telegram_id: int,
        target_text: str,
        user_transcript: str,
        match_score: int,
    ) -> None:
        self.shadowing_history.append({
            "telegram_id": telegram_id,
            "target_text": target_text,
            "user_transcript": user_transcript,
            "match_score": match_score,
            "created_at": "2026-10-23T09:00:00",
        })

    async def get_recent_shadowing(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        user_items = [s for s in self.shadowing_history if s["telegram_id"] == telegram_id]
        return list(reversed(user_items))[:limit]

    async def record_practice_session(
        self,
        telegram_id: int,
        duration_seconds: int,
        transcript: str,
        feedback_summary: str,
        fluency_score: int,
        cefr_level: str = "B1",
        ielts_band: float = 6.0,
        scenario: str = "Free Conversation",
    ) -> None:
        self.sessions.append({
            "telegram_id": telegram_id,
            "duration_seconds": duration_seconds,
            "transcript": transcript,
            "feedback_summary": feedback_summary,
            "fluency_score": fluency_score,
            "cefr_level": cefr_level,
            "ielts_band": ielts_band,
            "scenario": scenario,
            "created_at": "2026-10-23T09:00:00",
        })
        if telegram_id in self.users:
            self.users[telegram_id]["total_voice_notes"] += 1

    async def get_recent_sessions(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        user_sessions = [s for s in self.sessions if s["telegram_id"] == telegram_id]
        return list(reversed(user_sessions))[:limit]

    async def add_vocab_item(
        self,
        telegram_id: int,
        original_phrase: str,
        correction: str,
        explanation: str = "",
    ) -> None:
        self.vocab_bank.append({
            "telegram_id": telegram_id,
            "original_phrase": original_phrase,
            "correction": correction,
            "explanation": explanation,
            "created_at": "2026-10-23T09:00:00",
        })

    async def get_user_vocab_bank(
        self, telegram_id: int, limit: int = 15
    ) -> List[Dict[str, Any]]:
        items = [v for v in self.vocab_bank if v["telegram_id"] == telegram_id]
        return list(reversed(items))[:limit]

    async def get_total_stats(self) -> Dict[str, int]:
        return {
            "total_users": len(self.users),
            "total_sessions": len(self.sessions),
            "total_vocab": len(self.vocab_bank),
        }

    async def create_ielts_session(
        self, telegram_id: int, exam_type: str, questions: List[Dict[str, Any]]
    ) -> int:
        for s in self.ielts_sessions:
            if s["telegram_id"] == telegram_id and s["status"] == "in_progress":
                s["status"] = "abandoned"
        session_id = len(self.ielts_sessions) + 1
        self.ielts_sessions.append({
            "id": session_id,
            "telegram_id": telegram_id,
            "exam_type": exam_type,
            "current_step": 0,
            "questions": questions,
            "questions_json": "[]",
            "responses": [],
            "responses_json": "[]",
            "status": "in_progress",
            "created_at": "2026-10-23T09:00:00",
        })
        return session_id

    async def get_active_ielts_session(
        self, telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        for s in reversed(self.ielts_sessions):
            if s["telegram_id"] == telegram_id and s["status"] == "in_progress":
                return dict(s)
        return None

    async def update_ielts_session_progress(
        self, session_id: int, current_step: int, responses: List[Dict[str, Any]]
    ) -> None:
        for s in self.ielts_sessions:
            if s["id"] == session_id:
                s["current_step"] = current_step
                s["responses"] = responses

    async def cancel_active_ielts_session(self, telegram_id: int) -> None:
        for s in self.ielts_sessions:
            if s["telegram_id"] == telegram_id and s["status"] == "in_progress":
                s["status"] = "abandoned"

    async def record_ielts_mock_result(
        self,
        telegram_id: int,
        exam_type: str,
        overall_band: float,
        fluency_coherence: float,
        lexical_resource: float,
        grammar_accuracy: float,
        pronunciation: float,
        examiner_commentary: str,
        target_improvements: str,
    ) -> None:
        self.ielts_results.append({
            "id": len(self.ielts_results) + 1,
            "telegram_id": telegram_id,
            "exam_type": exam_type,
            "overall_band": overall_band,
            "fluency_coherence": fluency_coherence,
            "lexical_resource": lexical_resource,
            "grammar_accuracy": grammar_accuracy,
            "pronunciation": pronunciation,
            "examiner_commentary": examiner_commentary,
            "target_improvements": target_improvements,
            "created_at": "2026-10-23T09:30:00",
        })
        for s in self.ielts_sessions:
            if s["telegram_id"] == telegram_id and s["status"] == "in_progress":
                s["status"] = "completed"

    async def get_recent_ielts_results(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        results = [r for r in self.ielts_results if r["telegram_id"] == telegram_id]
        return list(reversed(results))[:limit]

    async def set_user_reminder(
        self, telegram_id: int, reminder_time: str, enabled: bool
    ) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["reminder_time"] = reminder_time
            self.users[telegram_id]["reminder_enabled"] = 1 if enabled else 0

    async def get_users_due_for_reminder(
        self, current_hh_mm: str, today_str: str
    ) -> List[Dict[str, Any]]:
        due = []
        for u in self.users.values():
            if (
                u.get("reminder_enabled") == 1
                and u.get("reminder_time") == current_hh_mm
                and u.get("last_reminded_date") != today_str
                and u.get("last_practice_date") != today_str
            ):
                due.append(dict(u))
        return due

    async def mark_user_reminded(
        self, telegram_id: int, date_str: str
    ) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["last_reminded_date"] = date_str

    async def set_active_phoneme_target(
        self, telegram_id: int, target_json: str
    ) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["active_phoneme_target"] = target_json

    async def clear_active_phoneme_target(self, telegram_id: int) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["active_phoneme_target"] = ""

    async def record_phoneme_drill(
        self,
        telegram_id: int,
        category_id: str,
        pair_id: str,
        pair_label: str,
        target_words: str,
        user_transcript: str,
        accuracy_score: int,
        is_distinction_clear: bool,
        detected_ipa: str = "",
        mouth_position_tip: str = "",
    ) -> None:
        self.phoneme_drills.append({
            "id": len(self.phoneme_drills) + 1,
            "telegram_id": telegram_id,
            "category_id": category_id,
            "pair_id": pair_id,
            "pair_label": pair_label,
            "target_words": target_words,
            "user_transcript": user_transcript,
            "accuracy_score": accuracy_score,
            "is_distinction_clear": 1 if is_distinction_clear else 0,
            "detected_ipa": detected_ipa,
            "mouth_position_tip": mouth_position_tip,
            "created_at": "2026-10-23T10:00:00",
        })

    async def get_recent_phoneme_drills(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        drills = [d for d in self.phoneme_drills if d["telegram_id"] == telegram_id]
        return list(reversed(drills))[:limit]

    async def get_phoneme_stats(self, telegram_id: int) -> Dict[str, Any]:
        user_drills = [d for d in self.phoneme_drills if d["telegram_id"] == telegram_id]
        if not user_drills:
            return {"total_drills": 0, "avg_accuracy": 0.0, "clear_distinctions": 0}
        total = len(user_drills)
        avg = sum(d["accuracy_score"] for d in user_drills) / total
        clear = sum(1 for d in user_drills if d["is_distinction_clear"] == 1)
        return {
            "total_drills": total,
            "avg_accuracy": round(avg, 1),
            "clear_distinctions": clear,
        }

    async def claim_free_trial(self, telegram_id: int, days: int = 7) -> Dict[str, Any]:
        if telegram_id in self.users:
            if self.users[telegram_id].get("has_used_trial") == 1:
                return {"success": False, "message": "Sudah pernah trial."}
            self.users[telegram_id]["is_premium"] = 1
            self.users[telegram_id]["premium_tier"] = "trial_7d"
            expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            self.users[telegram_id]["premium_until"] = expires
            self.users[telegram_id]["has_used_trial"] = 1
            return {"success": True, "expires_at": expires, "days": days}
        return {"success": False, "message": "User not found"}

    async def grant_user_subscription(
        self,
        telegram_id: int,
        days: int,
        tier_name: str,
        is_lifetime: bool = False,
        bonus_freeze: int = 3,
        bonus_xp: int = 250,
    ) -> Dict[str, Any]:
        if telegram_id in self.users:
            self.users[telegram_id]["is_premium"] = 1
            self.users[telegram_id]["premium_tier"] = "lifetime" if is_lifetime else tier_name
            self.users[telegram_id]["streak_freeze_count"] = self.users[telegram_id].get("streak_freeze_count", 1) + bonus_freeze
            self.users[telegram_id]["total_xp"] = self.users[telegram_id].get("total_xp", 0) + bonus_xp
            if is_lifetime:
                self.users[telegram_id]["premium_until"] = ""
                return {"success": True, "tier": "lifetime", "is_lifetime": True, "expires_at": ""}
            else:
                expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
                self.users[telegram_id]["premium_until"] = expires
                return {"success": True, "tier": tier_name, "is_lifetime": False, "expires_at": expires}
        return {"success": False, "message": "User not found"}

    async def expire_user_premium(self, telegram_id: int) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["is_premium"] = 0
            self.users[telegram_id]["premium_tier"] = "expired"

    async def grant_user_premium(self, telegram_id: int) -> None:
        await self.grant_user_subscription(telegram_id, days=0, tier_name="lifetime", is_lifetime=True)

    async def increment_daily_eval(self, telegram_id: int, today_str: str) -> int:
        if telegram_id not in self.users:
            return 1
        user = self.users[telegram_id]
        if user.get("daily_eval_date") != today_str:
            user["daily_eval_date"] = today_str
            user["daily_eval_count"] = 1
        else:
            user["daily_eval_count"] = user.get("daily_eval_count", 0) + 1
        return user["daily_eval_count"]

    async def decrement_streak_freeze(self, telegram_id: int) -> None:
        if telegram_id in self.users:
            curr = self.users[telegram_id].get("streak_freeze_count", 1)
            self.users[telegram_id]["streak_freeze_count"] = max(0, curr - 1)

    async def add_user_badge(self, telegram_id: int, badge_id: str) -> None:
        if telegram_id in self.users:
            badges = self.users[telegram_id].get("badges", [])
            if badge_id not in badges:
                badges.append(badge_id)
                self.users[telegram_id]["badges"] = badges

    async def get_practice_dates(self, telegram_id: int, limit: int = 30) -> List[str]:
        dates = [s.get("created_at", "")[:10] for s in self.sessions if s["telegram_id"] == telegram_id]
        return list(dict.fromkeys(dates))[:limit]

    async def get_linguistic_radar_metrics(self, telegram_id: int) -> Dict[str, float]:
        return {"fluency": 75.0, "pronunciation": 80.0, "grammar": 78.0, "lexical": 72.0}

    async def add_dialogue_turn(
        self,
        telegram_id: int,
        scenario: str,
        role: str,
        content: str,
    ) -> None:
        self.dialogue_turns.append({
            "telegram_id": telegram_id,
            "scenario": scenario,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    async def get_dialogue_history(
        self,
        telegram_id: int,
        scenario: str,
        limit: int = 20,
        max_age_hours: int = 2,
    ) -> List[Dict[str, str]]:
        matched = [
            {"role": t["role"], "content": t["content"]}
            for t in self.dialogue_turns
            if t["telegram_id"] == telegram_id and t["scenario"] == scenario
        ]
        return matched[-limit:]

    async def clear_dialogue_history(
        self,
        telegram_id: int,
        scenario: Optional[str] = None,
    ) -> None:
        if scenario:
            self.dialogue_turns = [
                t for t in self.dialogue_turns
                if not (t["telegram_id"] == telegram_id and t["scenario"] == scenario)
            ]
        else:
            self.dialogue_turns = [
                t for t in self.dialogue_turns
                if t["telegram_id"] != telegram_id
            ]

    async def add_referral(self, inviter_id: int, invitee_id: int) -> bool:
        for r in self.referrals:
            if r["invitee_id"] == invitee_id:
                return False
        self.referrals.append({"inviter_id": inviter_id, "invitee_id": invitee_id})
        if invitee_id in self.users:
            self.users[invitee_id]["invited_by"] = inviter_id
        return True

    async def get_referral_stats(self, telegram_id: int) -> Dict[str, Any]:
        count = sum(1 for r in self.referrals if r["inviter_id"] == telegram_id)
        return {
            "total_referred": count,
            "bonus_quota_earned": count * 3,
            "streak_freezes_earned": count,
        }

    async def add_bonus_quota(self, telegram_id: int, amount: int) -> int:
        if telegram_id in self.users:
            self.users[telegram_id]["bonus_quota"] = self.users[telegram_id].get("bonus_quota", 0) + amount
            return self.users[telegram_id]["bonus_quota"]
        return 0

    async def add_streak_freeze(self, telegram_id: int, amount: int = 1) -> int:
        if telegram_id in self.users:
            self.users[telegram_id]["streak_freeze_count"] = self.users[telegram_id].get("streak_freeze_count", 1) + amount
            return self.users[telegram_id]["streak_freeze_count"]
        return 0

    async def add_xp(self, telegram_id: int, amount: int) -> int:
        if telegram_id in self.users:
            self.users[telegram_id]["total_xp"] = self.users[telegram_id].get("total_xp", 0) + amount
            return self.users[telegram_id]["total_xp"]
        return 0

    async def set_active_tense_drill(self, telegram_id: int, tense_id: str) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["active_tense_drill"] = tense_id

    async def clear_active_tense_drill(self, telegram_id: int) -> None:
        if telegram_id in self.users:
            self.users[telegram_id]["active_tense_drill"] = None

    async def record_tense_exercise(
        self,
        telegram_id: int,
        tense_id: str,
        user_transcript: str,
        tense_accuracy: int,
        is_correct_tense: bool,
        corrected_sentence: str,
        explanation: str,
    ) -> None:
        pass




class TestSpeakingCoach(unittest.TestCase):
    """Unit tests for Speaking Coach domain logic, shadowing mode, and daily streak engine."""

    def setUp(self):
        self.repo = MockCoachRepository()
        self.user_service = UserService(self.repo)
        self.ai_service = AICoachService(api_key="mock_key")
        self.tts_service = TTSService()

    def test_speaking_feedback_with_ielts_and_slips(self):
        """Verify SpeakingFeedback validation with CEFR, IELTS, and GrammarSlips."""
        slip = GrammarSlip(
            original="I am agree with you",
            correction="I agree with you",
            explanation="Agree is a verb",
        )
        feedback = SpeakingFeedback(
            transcript="I am agree with you about remote work.",
            fluency_score=85,
            cefr_level="B2",
            ielts_band=6.5,
            grammar_slips=[slip],
            vocabulary_suggestions=["Try 'firmly concur'."],
            pronunciation_notes=["Pronounce 'remote' with clear /oʊ/."],
            conversational_reply="I agree! How does remote work impact your daily productivity?",
        )
        self.assertEqual(feedback.cefr_level, "B2")
        self.assertEqual(feedback.ielts_band, 6.5)
        self.assertEqual(len(feedback.grammar_slips), 1)

    def test_shadowing_feedback_model(self):
        """Verify ShadowingFeedback validation."""
        shadow = ShadowingFeedback(
            match_score=94,
            transcribed_text="I would have called you earlier",
            mispronounced_words=["earlier"],
            cadence_feedback="Natural rhythm, minor pause before earlier.",
            praise_message="Excellent pronunciation match!",
        )
        self.assertEqual(shadow.match_score, 94)
        self.assertIn("earlier", shadow.mispronounced_words)

    def test_shadowing_target_selection(self):
        """Verify target sentences exist for each level."""
        for level in ["Beginner", "Intermediate", "Advanced"]:
            target = self.ai_service.get_shadowing_target(level=level)
            self.assertIsInstance(target, str)
            self.assertTrue(len(target) > 10)

    def test_streak_consecutive_progression(self):
        """Verify streak increments on consecutive days."""
        async def run():
            user_id = 101
            await self.user_service.ensure_user(user_id, username="streak_user")

            # Day 1: Yesterday
            yesterday_str = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
            await self.repo.update_user_streak_and_xp(user_id, current_streak=1, max_streak=1, practice_date=yesterday_str, total_xp=25)

            # Day 2: Today (consecutive practice)
            result = await self.user_service.process_daily_streak_and_xp(user_id, activity_type="voice_note")
            self.assertEqual(result.current_streak, 2)
            self.assertEqual(result.max_streak, 2)
            self.assertTrue(result.is_extended)
            self.assertFalse(result.is_broken)
            self.assertTrue(result.total_xp > 25)

        asyncio.run(run())

    def test_streak_same_day_practice(self):
        """Verify practicing multiple times in one day preserves the streak without double counting."""
        async def run():
            user_id = 102
            await self.user_service.ensure_user(user_id, username="busy_learner")

            # Practice 1 today
            res1 = await self.user_service.process_daily_streak_and_xp(user_id)
            self.assertEqual(res1.current_streak, 1)

            # Practice 2 today
            res2 = await self.user_service.process_daily_streak_and_xp(user_id)
            self.assertEqual(res2.current_streak, 1)  # Preserved, not incremented again today
            self.assertFalse(res2.is_first_today)
            self.assertEqual(res2.total_xp, res1.total_xp + 15)  # Earned extra XP

        asyncio.run(run())

    def test_streak_reset_after_missed_day(self):
        """Verify streak resets to 1 if a user missed a day."""
        async def run():
            user_id = 103
            await self.user_service.ensure_user(user_id, username="forgetful_user")

            # Practiced 3 days ago with a 5-day streak
            three_days_ago = (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
            await self.repo.update_user_streak_and_xp(user_id, current_streak=5, max_streak=5, practice_date=three_days_ago, total_xp=150)

            # Practice today
            res = await self.user_service.process_daily_streak_and_xp(user_id)
            self.assertEqual(res.current_streak, 1)
            self.assertEqual(res.max_streak, 5)  # All-time record preserved
            self.assertTrue(res.is_broken)

        asyncio.run(run())

    def test_active_shadow_target_flow(self):
        """Verify setting, checking, and clearing active shadow target."""
        async def run():
            user_id = 104
            await self.user_service.ensure_user(user_id)

            target = "The technological breakthrough accelerated their trajectory."
            await self.user_service.set_active_shadow_target(user_id, target)
            profile = await self.user_service.get_user_profile(user_id)
            self.assertEqual(profile["active_shadow_target"], target)

            # Record shadowing attempt
            await self.user_service.record_shadowing_history(user_id, target, "technological breakthrough", 88)
            history = await self.repo.get_recent_shadowing(user_id)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["match_score"], 88)

            # Clear
            await self.user_service.clear_active_shadow_target(user_id)
            cleared = await self.user_service.get_user_profile(user_id)
            self.assertEqual(cleared["active_shadow_target"], "")

        asyncio.run(run())

    def test_ielts_mock_feedback_validation(self):
        """Verify IELTSMockFeedback model constraints and criteria."""
        feedback = IELTSMockFeedback(
            overall_band=7.5,
            fluency_coherence=7.5,
            lexical_resource=8.0,
            grammar_accuracy=7.0,
            pronunciation=7.5,
            strengths=["Wide range of cohesive devices", "Accurate idiomatic usage"],
            weaknesses=["Minor hesitation with complex passive voice"],
            key_recommendations_for_band_plus="Focus on diverse grammatical inversion structures.",
            examiner_summary="A fluent, well-developed performance displaying strong operational command.",
        )
        self.assertEqual(feedback.overall_band, 7.5)
        self.assertEqual(feedback.lexical_resource, 8.0)
        self.assertEqual(len(feedback.strengths), 2)

    def test_ielts_question_packs_completeness(self):
        """Verify all question packs contain Part 1, Part 2 (Cue Card), and Part 3 questions."""
        self.assertTrue(len(IELTS_QUESTION_PACKS) >= 3)
        for pack in IELTS_QUESTION_PACKS:
            self.assertIn("topic", pack)
            self.assertEqual(len(pack["part1"]), 3)
            self.assertIn("prompt", pack["part2"])
            self.assertTrue(len(pack["part2"]["bullet_points"]) >= 3)
            self.assertEqual(len(pack["part3"]), 2)

    def test_build_ielts_questions_express_and_full(self):
        """Verify express exam builds 3 questions and full builds 6 questions."""
        express_qs = self.ai_service.build_ielts_questions(exam_type="express")
        self.assertEqual(len(express_qs), 3)
        self.assertEqual(express_qs[0]["part"], 1)
        self.assertEqual(express_qs[1]["part"], 2)
        self.assertEqual(express_qs[1]["type"], "cue_card")
        self.assertEqual(express_qs[2]["part"], 3)

        full_qs = self.ai_service.build_ielts_questions(exam_type="full")
        self.assertEqual(len(full_qs), 6)
        self.assertEqual(full_qs[0]["part"], 1)
        self.assertEqual(full_qs[3]["part"], 2)
        self.assertEqual(full_qs[3]["type"], "cue_card")
        self.assertEqual(full_qs[4]["part"], 3)

    def test_ielts_exam_lifecycle_and_xp_award(self):
        """Verify full IELTS session progression, scorecard generation, and +100 XP award."""
        async def run():
            user_id = 105
            await self.user_service.ensure_user(user_id, username="ielts_candidate")

            questions = self.ai_service.build_ielts_questions(exam_type="express")
            session_id = await self.user_service.start_ielts_exam(user_id, "express", questions)
            self.assertTrue(session_id > 0)

            active = await self.user_service.get_active_ielts_session(user_id)
            self.assertIsNotNone(active)
            self.assertEqual(active["current_step"], 0)

            # Record answer 1
            responses = [{"step_index": 0, "transcript": "I work as a software engineer."}]
            await self.user_service.record_ielts_answer(session_id, current_step=1, responses=responses)

            updated = await self.user_service.get_active_ielts_session(user_id)
            self.assertEqual(updated["current_step"], 1)

            # Finalize exam
            feedback = IELTSMockFeedback(
                overall_band=7.0,
                fluency_coherence=7.0,
                lexical_resource=7.5,
                grammar_accuracy=6.5,
                pronunciation=7.0,
                strengths=["Natural discourse"],
                weaknesses=["Slight grammar slips"],
                key_recommendations_for_band_plus="Practice conditional clauses.",
                examiner_summary="Fluent speaking performance.",
            )

            streak_res = await self.user_service.finalize_ielts_exam(user_id, "express", feedback)
            self.assertTrue(streak_res.xp_earned >= 100)
            self.assertEqual(streak_res.current_streak, 1)

            # Verify saved results
            results = await self.user_service.get_ielts_history(user_id)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["overall_band"], 7.0)

            # Active session should now be completed
            post_active = await self.user_service.get_active_ielts_session(user_id)
            self.assertIsNone(post_active)

        asyncio.run(run())

    def test_duolingo_persona_generator(self):
        """Verify that Duolingo-style persona generator produces varied, valid messages."""
        seen_personas = set()
        for _ in range(30):
            label, text = get_random_reminder_message(name="Budi", current_streak=5)
            seen_personas.add(label)
            self.assertTrue(len(text) > 20)
            self.assertTrue("5" in text or "Budi" in text or "streak" in text.lower())

        # Check all 4 personas were hit
        self.assertTrue(len(seen_personas) >= 3)

    def test_reminder_due_filtering_logic(self):
        """Verify only users due at current time who haven't practiced today are returned."""
        async def run():
            user1 = 201  # due, hasn't practiced
            user2 = 202  # due, but already practiced today
            user3 = 203  # disabled reminder
            user4 = 204  # different time

            await self.user_service.ensure_user(user1, first_name="UserOne")
            await self.user_service.ensure_user(user2, first_name="UserTwo")
            await self.user_service.ensure_user(user3, first_name="UserThree")
            await self.user_service.ensure_user(user4, first_name="UserFour")

            today = "2026-10-23"

            # Set user 2 as already practiced today
            self.repo.users[user2]["last_practice_date"] = today

            # Set user 3 as disabled
            await self.user_service.update_reminder_preferences(user3, "20:00", enabled=False)

            # Set user 4 to 08:00
            await self.user_service.update_reminder_preferences(user4, "08:00", enabled=True)

            # Check due at 20:00 today
            due = await self.user_service.get_due_reminders("20:00", today)
            due_ids = [u["telegram_id"] for u in due]

            self.assertIn(user1, due_ids)
            self.assertNotIn(user2, due_ids)  # already practiced today
            self.assertNotIn(user3, due_ids)  # disabled
            self.assertNotIn(user4, due_ids)  # time is 08:00

            # After marking user 1 as reminded, they should no longer be due
            await self.user_service.mark_reminded(user1, today)
            due_after = await self.user_service.get_due_reminders("20:00", today)
            self.assertEqual(len(due_after), 0)

        asyncio.run(run())

    def test_reminder_preferences_update(self):
        """Verify updating reminder time and toggle."""
        async def run():
            user_id = 301
            await self.user_service.ensure_user(user_id)

            await self.user_service.update_reminder_preferences(user_id, reminder_time="13:00", enabled=True)
            p1 = await self.user_service.get_user_profile(user_id)
            self.assertEqual(p1["reminder_time"], "13:00")
            self.assertEqual(p1["reminder_enabled"], 1)

            # Toggle off
            await self.user_service.update_reminder_preferences(user_id, reminder_time="13:00", enabled=False)
            p2 = await self.user_service.get_user_profile(user_id)
            self.assertEqual(p2["reminder_enabled"], 0)

        asyncio.run(run())

    def test_phoneme_catalog_integrity(self):
        """Verify all 6 phoneme minimal pair categories and pair items exist with required fields."""
        cats = get_phoneme_categories()
        self.assertEqual(len(cats), 6)
        cat_ids = {c["id"] for c in cats}
        expected_ids = {"th_vs_s", "v_vs_b", "l_vs_r", "sh_vs_s", "ae_vs_e", "p_vs_f"}
        self.assertEqual(cat_ids, expected_ids)

        for cat in cats:
            self.assertGreater(cat["pairs_count"], 0)
            pairs = get_phoneme_pairs_by_category(cat["id"])
            self.assertGreaterEqual(len(pairs), 3)
            for p in pairs:
                self.assertIn("id", p)
                self.assertIn("label", p)
                self.assertIn("word_a", p)
                self.assertIn("ipa_a", p)
                self.assertIn("word_b", p)
                self.assertIn("ipa_b", p)
                self.assertIn("sentence", p)
                self.assertIn("mouth_tip", p)

        # Direct retrieval
        pair = get_phoneme_pair("th_s_think_sink")
        self.assertIsNotNone(pair)
        self.assertEqual(pair["word_a"], "think")
        self.assertEqual(pair["word_b"], "sink")

        # Random retrieval
        random_pair = get_random_phoneme_pair()
        self.assertIn("id", random_pair)
        self.assertIn("sentence", random_pair)

    def test_phoneme_feedback_schema_validation(self):
        """Validate PhonemeFeedback Pydantic model serialization and fields."""
        feedback = PhonemeFeedback(
            accuracy_score=94,
            detected_words="think and sink",
            target_ipa="/θɪŋk/ vs /sɪŋk/",
            detected_ipa="[/θɪŋk/] vs [/sɪŋk/]",
            is_distinction_clear=True,
            mouth_position_tip="Place tongue between teeth for /θ/.",
            coaching_summary="Pristine articulation!",
        )
        self.assertEqual(feedback.accuracy_score, 94)
        self.assertTrue(feedback.is_distinction_clear)
        self.assertIn("/θɪŋk/", feedback.target_ipa)

    def test_active_phoneme_lifecycle(self):
        """Verify setting, retrieving, and clearing active phoneme drill in UserService."""
        async def run():
            user_id = 401
            await self.user_service.ensure_user(user_id)

            drill = get_phoneme_pair("v_b_very_berry")
            self.assertIsNotNone(drill)

            # Initially none
            none_drill = await self.user_service.get_active_phoneme_drill(user_id)
            self.assertIsNone(none_drill)

            # Set active drill
            await self.user_service.set_active_phoneme_drill(user_id, drill)
            active = await self.user_service.get_active_phoneme_drill(user_id)
            self.assertIsNotNone(active)
            self.assertEqual(active["id"], "v_b_very_berry")
            self.assertEqual(active["word_a"], "very")

            # Clear active drill
            await self.user_service.clear_active_phoneme_drill(user_id)
            cleared = await self.user_service.get_active_phoneme_drill(user_id)
            self.assertIsNone(cleared)

        asyncio.run(run())

    def test_phoneme_drill_persistence_and_xp(self):
        """Verify recording phoneme drill, XP award (+25 / +35 XP), and streak increment."""
        async def run():
            user_id = 402
            await self.user_service.ensure_user(user_id)

            # Record a completed drill
            await self.user_service.record_phoneme_drill(
                telegram_id=user_id,
                category_id="th_vs_s",
                pair_id="th_s_think_sink",
                pair_label="think vs sink",
                target_words="think (/θɪŋk/) vs sink (/sɪŋk/)",
                user_transcript="think sink",
                accuracy_score=95,
                is_distinction_clear=True,
                detected_ipa="[/θɪŋk/] vs [/sɪŋk/]",
                mouth_position_tip="Tongue between teeth.",
            )

            # Gamification award: Base 25 XP + 10 bonus (score >= 90) = 35 XP
            streak_res = await self.user_service.process_daily_streak_and_xp(
                telegram_id=user_id,
                activity_type="phoneme",
                bonus_xp=10,
            )
            self.assertEqual(streak_res.xp_earned, 35)
            self.assertEqual(streak_res.current_streak, 1)

            # Check stats
            stats = await self.user_service.get_phoneme_stats(user_id)
            self.assertEqual(stats["total_drills"], 1)
            self.assertEqual(stats["avg_accuracy"], 95.0)
            self.assertEqual(stats["clear_distinctions"], 1)

        asyncio.run(run())

    def test_phoneme_evaluation_mock(self):
        """Verify evaluate_phoneme_attempt handles mock responses and error states."""
        async def run():
            drill = get_phoneme_pair("th_s_thick_sick")

            # When client is None
            service_no_client = AICoachService(api_key="key")
            service_no_client.client = None
            with self.assertRaises(RuntimeError):
                await service_no_client.evaluate_phoneme_attempt(
                    audio_bytes=b"dummy_bytes",
                    target_drill=drill,
                )

            # When client is mocked
            from unittest.mock import MagicMock
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = '{"accuracy_score": 91, "detected_words": "thick and sick", "target_ipa": "/θɪk/ vs /sɪk/", "detected_ipa": "[/θɪk/] vs [/sɪk/]", "is_distinction_clear": true, "mouth_position_tip": "Tongue tip out.", "coaching_summary": "Clear distinction!"}'
            mock_client.models.generate_content.return_value = mock_response

            service_mock = AICoachService(api_key="key")
            service_mock.client = mock_client
            res = await service_mock.evaluate_phoneme_attempt(
                audio_bytes=b"dummy_audio",
                target_drill=drill,
            )
            self.assertEqual(res.accuracy_score, 91)
            self.assertTrue(res.is_distinction_clear)
            self.assertEqual(res.detected_words, "thick and sick")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()

