import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from src.repositories.coach_repository import ICoachRepository
from src.services.ai_coach_service import GrammarSlip, IELTSMockFeedback

LEVEL_TIERS = [
    (1, "Novice Explorer", 0),
    (2, "Curious Beginner", 50),
    (3, "Language Explorer", 150),
    (4, "Active Conversationalist", 300),
    (5, "Confident Speaker", 500),
    (6, "Articulate Communicator", 750),
    (7, "Fluent Debater", 1100),
    (8, "Advanced Orator", 1500),
    (9, "Near-Native Speaker", 2000),
    (10, "Native Master", 3000),
]

BADGES_CATALOG = {
    "FIRST_STEP": {
        "title": "First Voice Note 🎙️",
        "description": "Send your first voice practice note",
        "icon": "🎙️",
    },
    "STREAK_3": {
        "title": "Spark of Consistency 🔥",
        "description": "Maintain a 3-day speaking streak",
        "icon": "🔥",
    },
    "STREAK_7": {
        "title": "7-Day Streak Warrior ⚡",
        "description": "Maintain a 7-day speaking streak",
        "icon": "⚡",
    },
    "STREAK_30": {
        "title": "Monthly Habit Champion 🏆",
        "description": "Achieve a 30-day streak",
        "icon": "🏆",
    },
    "IELTS_CANDIDATE": {
        "title": "IELTS Challenger 🏛️",
        "description": "Complete an official IELTS Mock Exam",
        "icon": "🏛️",
    },
    "IELTS_HIGH_BAND": {
        "title": "Band 7.0+ High-Flyer 🌟",
        "description": "Achieve overall Band 7.0 or higher in Mock Exam",
        "icon": "🌟",
    },
    "PHONEME_SPECIALIST": {
        "title": "Phonetics Virtuoso 👄",
        "description": "Complete 5 minimal pair drills with clear contrast",
        "icon": "👄",
    },
    "VOCAB_COLLECTOR": {
        "title": "Lexicon Builder 📖",
        "description": "Collect 10+ words and grammar fixes in Vocab Bank",
        "icon": "📖",
    },
    "PREMIUM_SUPPORTER": {
        "title": "Star Patron ⭐",
        "description": "Upgrade to Telegram Stars Premium Pass",
        "icon": "⭐",
    },
}


def calculate_user_level(total_xp: int) -> Dict[str, Any]:
    """Calculate level tier (1-10) and percentage progress to next tier."""
    current_tier = LEVEL_TIERS[0]
    next_tier = None
    for i, tier in enumerate(LEVEL_TIERS):
        if total_xp >= tier[2]:
            current_tier = tier
            next_tier = LEVEL_TIERS[i + 1] if i + 1 < len(LEVEL_TIERS) else None
        else:
            break

    xp_for_current = current_tier[2]
    xp_for_next = next_tier[2] if next_tier else current_tier[2]
    progress_pct = 100 if not next_tier else min(100, max(0, int(((total_xp - xp_for_current) / (xp_for_next - xp_for_current)) * 100)))

    return {
        "level": current_tier[0],
        "title": current_tier[1],
        "total_xp": total_xp,
        "next_level": next_tier[0] if next_tier else current_tier[0],
        "next_title": next_tier[1] if next_tier else "Maximum Level",
        "xp_needed": max(0, xp_for_next - total_xp) if next_tier else 0,
        "progress_percent": progress_pct,
    }


@dataclass
class StreakUpdateResult:
    """Outcome of processing daily practice activity for streaks and XP."""

    current_streak: int
    max_streak: int
    is_extended: bool
    is_broken: bool
    is_first_today: bool
    xp_earned: int
    total_xp: int
    freeze_used: bool = False
    newly_unlocked_badges: List[str] = field(default_factory=list)


class UserService:
    """Domain service managing learner profiles, scenarios, streaks, and session history."""

    def __init__(self, repository: ICoachRepository):
        self.repo = repository

    async def ensure_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> None:
        """Register user or touch last active timestamp."""
        await self.repo.upsert_user(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )

    async def get_user_profile(self, telegram_id: int) -> Dict[str, Any]:
        """Fetch user profile and settings, validating premium expiration."""
        record = await self.repo.get_user(telegram_id)
        if not record:
            return {
                "telegram_id": telegram_id,
                "first_name": "Learner",
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
                "streak_freeze_count": 1,
                "is_premium": 0,
                "premium_tier": "",
                "premium_until": "",
                "has_used_trial": 0,
                "days_left": 0,
                "is_lifetime": False,
                "daily_eval_count": 0,
                "daily_eval_date": "",
                "badges_json": "[]",
                "tts_speed": "+0%",
            }

        prof = dict(record)
        prof["tts_voice"] = prof.get("tts_voice") or "en-US-JennyNeural"
        prof["tts_speed"] = prof.get("tts_speed") or "+0%"
        is_prem = prof.get("is_premium", 0) == 1
        prof["is_premium"] = 1 if is_prem else 0
        tier = prof.get("premium_tier") or ""
        prof["premium_tier"] = tier
        until_str = prof.get("premium_until") or ""

        if is_prem:
            if tier == "lifetime":
                prof["is_lifetime"] = True
                prof["days_left"] = 99999
            elif until_str:
                try:
                    until_dt = datetime.fromisoformat(until_str)
                    if until_dt.tzinfo is None:
                        until_dt = until_dt.replace(tzinfo=timezone.utc)
                    now_utc = datetime.now(timezone.utc)
                    if until_dt < now_utc:
                        await self.repo.expire_user_premium(telegram_id)
                        prof["is_premium"] = 0
                        prof["premium_tier"] = "expired"
                        prof["days_left"] = 0
                        prof["is_lifetime"] = False
                    else:
                        remaining = until_dt - now_utc
                        days_rem = remaining.days
                        if remaining.seconds > 0:
                            days_rem += 1
                        prof["days_left"] = max(1, days_rem)
                        prof["is_lifetime"] = False
                except Exception:
                    prof["is_lifetime"] = True
                    prof["days_left"] = 99999
            else:
                prof["is_lifetime"] = True
                prof["days_left"] = 99999
        else:
            prof["is_lifetime"] = False
            prof["days_left"] = 0

        return prof

    async def update_target_level(self, telegram_id: int, level: str) -> None:
        """Change the learner's target proficiency level."""
        valid_levels = {"Beginner", "Intermediate", "Advanced"}
        if level not in valid_levels:
            level = "Intermediate"
        await self.repo.set_user_level(telegram_id, level)

    async def update_active_scenario(self, telegram_id: int, scenario: str) -> None:
        """Update roleplay scenario setting."""
        await self.repo.set_user_scenario(telegram_id, scenario)

    async def update_tts_voice(self, telegram_id: int, voice: str) -> None:
        """Update preferred neural TTS voice."""
        await self.repo.set_user_tts_voice(telegram_id, voice)

    async def update_tts_speed(self, telegram_id: int, speed: str) -> None:
        """Update preferred speech rate/speed."""
        await self.repo.set_user_tts_speed(telegram_id, speed)

    async def set_active_shadow_target(self, telegram_id: int, target_text: str) -> None:
        """Set current active shadowing exercise target."""
        await self.repo.set_active_shadow_target(telegram_id, target_text)

    async def clear_active_shadow_target(self, telegram_id: int) -> None:
        """Clear active shadowing target."""
        await self.repo.clear_active_shadow_target(telegram_id)

    async def record_shadowing_history(
        self, telegram_id: int, target_text: str, user_transcript: str, match_score: int
    ) -> None:
        """Log completed shadowing attempt."""
        await self.repo.record_shadowing_attempt(
            telegram_id=telegram_id,
            target_text=target_text,
            user_transcript=user_transcript,
            match_score=match_score,
        )

    async def check_daily_quota(self, telegram_id: int) -> Tuple[bool, int, int]:
        """Check if user has remaining evaluations today.
        
        Returns: (can_evaluate: bool, used_today: int, max_limit: int)
        """
        profile = await self.get_user_profile(telegram_id)
        if profile.get("is_premium", 0) == 1:
            return True, profile.get("daily_eval_count", 0), 9999

        today_str = datetime.now(timezone.utc).date().isoformat()
        last_eval_date = profile.get("daily_eval_date") or ""
        used_today = profile.get("daily_eval_count", 0) if last_eval_date == today_str else 0
        bonus_quota = profile.get("bonus_quota", 0)
        limit = 10 + bonus_quota
        return used_today < limit, used_today, limit

    async def process_referral(
        self, inviter_id: int, invitee_id: int
    ) -> Optional[Dict[str, Any]]:
        """Process referral link signup with instant rewards for both parties.
        
        Inviter gets: +1 Streak Freeze, +3 Bonus Quota, +50 XP
        Invitee gets: +3 Welcome Bonus Quota, +25 XP
        """
        if inviter_id == invitee_id:
            logger.info("Self-referral rejected for user %s", inviter_id)
            return None

        # Check inviter exists
        inviter = await self.repo.get_user(inviter_id)
        if not inviter:
            logger.info("Inviter %s does not exist", inviter_id)
            return None

        # Check invitee profile
        invitee = await self.get_user_profile(invitee_id)
        if invitee.get("invited_by", 0) != 0 or invitee.get("total_voice_notes", 0) > 0:
            logger.info("Invitee %s already registered with activity or referred", invitee_id)
            return None

        # Record referral
        added = await self.repo.add_referral(inviter_id, invitee_id)
        if not added:
            return None

        # Reward inviter: +1 freeze, +3 bonus quota, +50 XP
        await self.repo.add_streak_freeze(inviter_id, 1)
        await self.repo.add_bonus_quota(inviter_id, 3)
        await self.repo.add_xp(inviter_id, 50)

        # Reward invitee: +3 bonus quota, +25 XP
        await self.repo.add_bonus_quota(invitee_id, 3)
        await self.repo.add_xp(invitee_id, 25)

        logger.info("Referral rewarded successfully: %s invited %s", inviter_id, invitee_id)
        return {
            "success": True,
            "inviter_id": inviter_id,
            "invitee_id": invitee_id,
            "inviter_rewards": {"freeze": 1, "bonus_quota": 3, "xp": 50},
            "invitee_rewards": {"bonus_quota": 3, "xp": 25},
        }

    async def get_referral_info(
        self, telegram_id: int, bot_username: str = "MyEnglishCoach2000_bot"
    ) -> Dict[str, Any]:
        """Fetch referral stats and generate deep-link with pre-filled share pitch."""
        stats = await self.repo.get_referral_stats(telegram_id)
        profile = await self.get_user_profile(telegram_id)
        bonus_quota = profile.get("bonus_quota", 0)

        link = f"https://t.me/{bot_username}?start=ref_{telegram_id}"
        share_text = (
            "🗣️ Ayo latihan speaking bahasa Inggris bareng AI Native Speaker di Telegram! "
            "Dapatkan evaluasi pengucapan, skor IELTS, dan balasan suara AI interaktif 24/7. "
            f"Gabung lewat link ini untuk dapat +3 kuota suara ekstra: {link}"
        )

        return {
            "referral_link": link,
            "share_text": share_text,
            "total_referred": stats.get("total_referred", 0),
            "bonus_quota": bonus_quota,
            "streak_freezes_earned": stats.get("streak_freezes_earned", 0),
        }

    async def record_daily_eval(self, telegram_id: int) -> int:
        """Increment daily evaluation count for quota tracking."""
        today_str = datetime.now(timezone.utc).date().isoformat()
        return await self.repo.increment_daily_eval(telegram_id, today_str)

    async def claim_free_trial(self, telegram_id: int) -> Dict[str, Any]:
        """Activate a 7-day free trial for first-time learners."""
        return await self.repo.claim_free_trial(telegram_id, days=7)

    async def grant_subscription(self, telegram_id: int, plan_type: str) -> Dict[str, Any]:
        """Upgrade user based on chosen duration tier."""
        tier_mapping = {
            "plan_1m": (30, "1 Bulan", False),
            "plan_3m": (90, "3 Bulan", False),
            "plan_lifetime": (0, "Seumur Hidup", True),
            "payload_speaking_coach_premium": (0, "Seumur Hidup", True),
        }
        days, tier_name, is_lifetime = tier_mapping.get(plan_type, (30, "1 Bulan", False))

        result = await self.repo.grant_user_subscription(
            telegram_id=telegram_id,
            days=days,
            tier_name=tier_name,
            is_lifetime=is_lifetime,
            bonus_freeze=3,
            bonus_xp=250,
        )
        await self.repo.add_user_badge(telegram_id, "PREMIUM_SUPPORTER")
        return result

    async def grant_premium(self, telegram_id: int) -> None:
        """Upgrade user to Lifetime Premium Pass (backward-compatible)."""
        await self.grant_subscription(telegram_id, "plan_lifetime")

    async def check_and_award_badges(self, telegram_id: int, context_event: str = "") -> List[str]:
        """Evaluate criteria and award eligible milestone badges to the user."""
        profile = await self.get_user_profile(telegram_id)
        raw_badges = profile.get("badges_json") or "[]"
        try:
            existing_badges = set(json.loads(raw_badges))
        except Exception:
            existing_badges = set()

        new_unlocked: List[str] = []

        def _try_award(b_id: str):
            if b_id not in existing_badges:
                new_unlocked.append(b_id)
                existing_badges.add(b_id)

        # 1. First Voice Note
        if (profile.get("total_voice_notes", 0) or 0) >= 1:
            _try_award("FIRST_STEP")

        # 2. Streaks (3, 7, 30)
        streak = profile.get("current_streak", 0) or 0
        if streak >= 3:
            _try_award("STREAK_3")
        if streak >= 7:
            _try_award("STREAK_7")
        if streak >= 30:
            _try_award("STREAK_30")

        # 3. IELTS Exam
        if context_event.startswith("ielts:"):
            _try_award("IELTS_CANDIDATE")
            try:
                band = float(context_event.split(":")[1])
                if band >= 7.0:
                    _try_award("IELTS_HIGH_BAND")
            except Exception:
                pass

        # 4. Phoneme drills (5 clear distinctions)
        phoneme_stats = await self.repo.get_phoneme_stats(telegram_id)
        if phoneme_stats.get("clear_distinctions", 0) >= 5:
            _try_award("PHONEME_SPECIALIST")

        # 5. Vocab bank (10+ items)
        vocab_items = await self.repo.get_user_vocab_bank(telegram_id, limit=20)
        if len(vocab_items) >= 10:
            _try_award("VOCAB_COLLECTOR")

        # Persist new badges
        for b in new_unlocked:
            await self.repo.add_user_badge(telegram_id, b)

        return new_unlocked

    async def process_daily_streak_and_xp(
        self,
        telegram_id: int,
        activity_type: str = "voice_note",
        bonus_xp: int = 0,
        context_event: str = "",
    ) -> StreakUpdateResult:
        """Calculate streak progression with Streak Freeze protection and award XP."""
        profile = await self.get_user_profile(telegram_id)

        today_utc = datetime.now(timezone.utc).date()
        today_str = today_utc.isoformat()
        yesterday_str = (today_utc - timedelta(days=1)).isoformat()
        two_days_ago_str = (today_utc - timedelta(days=2)).isoformat()

        last_date = profile.get("last_practice_date") or ""
        current_streak = profile.get("current_streak") or 0
        max_streak = profile.get("max_streak") or 0
        total_xp = profile.get("total_xp") or 0
        streak_freezes = profile.get("streak_freeze_count", 1)

        # Base activity XP
        if activity_type == "ielts":
            base_xp = 100
        elif activity_type == "phoneme":
            base_xp = 25
        elif activity_type == "shadowing":
            base_xp = 20
        else:
            base_xp = 15
        earned_xp = base_xp + bonus_xp

        is_extended = False
        is_broken = False
        is_first_today = False
        freeze_used = False

        if last_date == today_str:
            is_first_today = False
            total_xp += earned_xp
        elif last_date == yesterday_str:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
            streak_bonus = 25
            earned_xp += streak_bonus
            total_xp += earned_xp
            is_extended = True
            is_first_today = True
        elif last_date == two_days_ago_str and streak_freezes > 0 and current_streak > 1:
            # ❄️ Streak Freeze Protection triggered!
            freeze_used = True
            await self.repo.decrement_streak_freeze(telegram_id)
            current_streak += 1
            max_streak = max(max_streak, current_streak)
            streak_bonus = 25
            earned_xp += streak_bonus
            total_xp += earned_xp
            is_extended = True
            is_first_today = True
        else:
            if current_streak > 1:
                is_broken = True
            current_streak = 1
            max_streak = max(max_streak, 1)
            total_xp += earned_xp
            is_extended = True
            is_first_today = True

        await self.repo.update_user_streak_and_xp(
            telegram_id=telegram_id,
            current_streak=current_streak,
            max_streak=max_streak,
            practice_date=today_str,
            total_xp=total_xp,
        )

        # Evaluate and award badges
        new_badges = await self.check_and_award_badges(telegram_id, context_event=context_event)

        return StreakUpdateResult(
            current_streak=current_streak,
            max_streak=max_streak,
            is_extended=is_extended,
            is_broken=is_broken,
            is_first_today=is_first_today,
            xp_earned=earned_xp,
            total_xp=total_xp,
            freeze_used=freeze_used,
            newly_unlocked_badges=new_badges,
        )

    async def record_session(
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
        """Save completed speaking session."""
        await self.repo.record_practice_session(
            telegram_id=telegram_id,
            duration_seconds=duration_seconds,
            transcript=transcript,
            feedback_summary=feedback_summary,
            fluency_score=fluency_score,
            cefr_level=cefr_level,
            ielts_band=ielts_band,
            scenario=scenario,
        )

    async def save_grammar_slips_to_vocab_bank(
        self, telegram_id: int, slips: List[GrammarSlip]
    ) -> None:
        """Save identified slips to user's personal review bank."""
        for slip in slips:
            await self.repo.add_vocab_item(
                telegram_id=telegram_id,
                original_phrase=slip.original,
                correction=slip.correction,
                explanation=slip.explanation,
            )

    async def get_practice_history(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve recent practice sessions."""
        return await self.repo.get_recent_sessions(telegram_id, limit=limit)

    async def get_vocab_review_items(
        self, telegram_id: int, limit: int = 15
    ) -> List[Dict[str, Any]]:
        """Get list of words/grammar slips for user review."""
        return await self.repo.get_user_vocab_bank(telegram_id, limit=limit)

    # Alias for convenience
    get_vocab_review = get_vocab_review_items

    async def start_ielts_exam(
        self, telegram_id: int, exam_type: str, questions: List[Dict[str, Any]]
    ) -> int:
        """Create a new official IELTS mock exam session."""
        return await self.repo.create_ielts_session(telegram_id, exam_type, questions)

    async def get_active_ielts_session(
        self, telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve active in-progress IELTS session if exists."""
        return await self.repo.get_active_ielts_session(telegram_id)

    async def record_ielts_answer(
        self, session_id: int, current_step: int, responses: List[Dict[str, Any]]
    ) -> None:
        """Save progress for current step of IELTS exam."""
        await self.repo.update_ielts_session_progress(session_id, current_step, responses)

    async def cancel_ielts_exam(self, telegram_id: int) -> None:
        """Abandon current active IELTS exam session."""
        await self.repo.cancel_active_ielts_session(telegram_id)

    async def finalize_ielts_exam(
        self,
        telegram_id: int,
        exam_type: str,
        feedback: IELTSMockFeedback,
    ) -> StreakUpdateResult:
        """Save official IELTS scorecard and award reward XP."""
        await self.repo.record_ielts_mock_result(
            telegram_id=telegram_id,
            exam_type=exam_type,
            overall_band=feedback.overall_band,
            fluency_coherence=feedback.fluency_coherence,
            lexical_resource=feedback.lexical_resource,
            grammar_accuracy=feedback.grammar_accuracy,
            pronunciation=feedback.pronunciation,
            examiner_commentary=feedback.examiner_summary,
            target_improvements=feedback.key_recommendations_for_band_plus,
        )

        return await self.process_daily_streak_and_xp(
            telegram_id=telegram_id,
            activity_type="ielts",
            context_event=f"ielts:{feedback.overall_band}",
        )

    async def get_ielts_history(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetch past IELTS mock exam scorecards."""
        return await self.repo.get_recent_ielts_results(telegram_id, limit=limit)

    async def update_reminder_preferences(
        self, telegram_id: int, reminder_time: str, enabled: bool
    ) -> None:
        """Save user's preferred reminder time and active state."""
        await self.repo.set_user_reminder(
            telegram_id=telegram_id,
            reminder_time=reminder_time,
            enabled=enabled,
        )

    async def get_due_reminders(
        self, current_hh_mm: str, today_str: str
    ) -> List[Dict[str, Any]]:
        """Fetch users whose reminder is scheduled for current time and haven't practiced today."""
        return await self.repo.get_users_due_for_reminder(
            current_hh_mm=current_hh_mm,
            today_str=today_str,
        )

    async def mark_reminded(self, telegram_id: int, today_str: str) -> None:
        """Mark user as reminded today to prevent duplicate reminders."""
        await self.repo.mark_user_reminded(telegram_id=telegram_id, date_str=today_str)

    async def set_active_phoneme_drill(
        self, telegram_id: int, drill: Dict[str, Any]
    ) -> None:
        """Store active minimal pair drill in user profile as JSON."""
        target_json = json.dumps(drill)
        await self.repo.set_active_phoneme_target(telegram_id, target_json)

    async def get_active_phoneme_drill(
        self, telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve active minimal pair drill for the user if set."""
        profile = await self.get_user_profile(telegram_id)
        raw = profile.get("active_phoneme_target") or ""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def clear_active_phoneme_drill(self, telegram_id: int) -> None:
        """Clear active minimal pair drill for user."""
        await self.repo.clear_active_phoneme_target(telegram_id)

    async def set_active_tense_drill(
        self, telegram_id: int, tense_data: Dict[str, Any]
    ) -> None:
        """Store active targeted English tense drill in user profile as JSON."""
        target_json = json.dumps(tense_data)
        await self.repo.set_active_tense_drill(telegram_id, target_json)

    async def get_active_tense_drill(
        self, telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve active targeted tense drill for the user if set."""
        profile = await self.get_user_profile(telegram_id)
        raw = profile.get("active_tense_drill") or ""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def clear_active_tense_drill(self, telegram_id: int) -> None:
        """Clear active targeted tense drill for user."""
        await self.repo.clear_active_tense_drill(telegram_id)

    async def reset_all_active_drills(self, telegram_id: int) -> None:
        """Clear all concurrent active learning states to prevent handler routing collisions."""
        await self.repo.clear_active_shadow_target(telegram_id)
        await self.repo.clear_active_phoneme_target(telegram_id)
        await self.repo.clear_active_tense_drill(telegram_id)
        try:
            active_ielts = await self.repo.get_active_ielts_session(telegram_id)
            if active_ielts:
                await self.repo.cancel_active_ielts_session(telegram_id)
        except Exception as err:
            logger.warning("Could not cancel active IELTS session during reset: %s", err)

    async def record_tense_exercise(
        self,
        telegram_id: int,
        tense_id: str,
        tense_title: str,
        user_transcript: str,
        accuracy_score: int,
        is_target_tense_used: bool,
        verb_form_analysis: str = "",
        coaching_tip: str = "",
    ) -> None:
        """Log completed targeted tense exercise."""
        await self.repo.record_tense_exercise(
            telegram_id=telegram_id,
            tense_id=tense_id,
            tense_title=tense_title,
            user_transcript=user_transcript,
            accuracy_score=accuracy_score,
            is_target_tense_used=is_target_tense_used,
            verb_form_analysis=verb_form_analysis,
            coaching_tip=coaching_tip,
        )

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
        """Log completed minimal pair drill."""
        await self.repo.record_phoneme_drill(
            telegram_id=telegram_id,
            category_id=category_id,
            pair_id=pair_id,
            pair_label=pair_label,
            target_words=target_words,
            user_transcript=user_transcript,
            accuracy_score=accuracy_score,
            is_distinction_clear=is_distinction_clear,
            detected_ipa=detected_ipa,
            mouth_position_tip=mouth_position_tip,
        )

    async def get_phoneme_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Fetch user's lifetime phoneme practice count and average accuracy."""
        return await self.repo.get_phoneme_stats(telegram_id)

    async def get_tma_dashboard_data(self, telegram_id: int) -> Dict[str, Any]:
        """Aggregate full companion dashboard payload for Telegram Mini App."""
        profile = await self.get_user_profile(telegram_id)
        total_xp = profile.get("total_xp", 0) or 0
        level_info = calculate_user_level(total_xp)

        # 1. Radar metrics
        radar_metrics = await self.repo.get_linguistic_radar_metrics(telegram_id)

        # 2. Activity dates for heatmap
        practice_dates = await self.repo.get_practice_dates(telegram_id, limit=30)

        # 3. Badges
        raw_badges = profile.get("badges_json") or "[]"
        try:
            unlocked_keys = json.loads(raw_badges)
        except Exception:
            unlocked_keys = []

        badges_list = []
        for b_id, meta in BADGES_CATALOG.items():
            badges_list.append({
                "id": b_id,
                "title": meta["title"],
                "description": meta["description"],
                "icon": meta["icon"],
                "unlocked": b_id in unlocked_keys,
            })

        # 4. Recent sessions
        recent_sessions = await self.repo.get_recent_sessions(telegram_id, limit=5)

        return {
            "user": {
                "telegram_id": telegram_id,
                "first_name": profile.get("first_name", "Learner"),
                "username": profile.get("username", ""),
                "target_level": profile.get("target_level", "Intermediate"),
                "active_scenario": profile.get("active_scenario", "Free Conversation"),
                "current_streak": profile.get("current_streak", 0) or 0,
                "max_streak": profile.get("max_streak", 0) or 0,
                "streak_freeze_count": profile.get("streak_freeze_count", 1) or 0,
                "is_premium": profile.get("is_premium", 0) == 1,
            },
            "level": level_info,
            "radar": radar_metrics,
            "activity_dates": practice_dates,
            "badges": badges_list,
            "recent_sessions": recent_sessions,
        }
