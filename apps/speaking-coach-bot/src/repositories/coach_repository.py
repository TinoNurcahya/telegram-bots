import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

try:
    import aiosqlite
except ImportError:
    aiosqlite = None


class ICoachRepository(ABC):
    """Abstract interface for speaking coach repository."""

    @abstractmethod
    async def upsert_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> None:
        pass

    @abstractmethod
    async def set_user_level(self, telegram_id: int, level: str) -> None:
        pass

    @abstractmethod
    async def set_user_scenario(self, telegram_id: int, scenario: str) -> None:
        pass

    @abstractmethod
    async def set_user_tts_voice(self, telegram_id: int, voice: str) -> None:
        pass

    @abstractmethod
    async def set_user_tts_speed(self, telegram_id: int, speed: str) -> None:
        pass

    @abstractmethod
    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_user_streak_and_xp(
        self,
        telegram_id: int,
        current_streak: int,
        max_streak: int,
        practice_date: str,
        total_xp: int,
    ) -> None:
        pass

    @abstractmethod
    async def set_active_shadow_target(self, telegram_id: int, target_text: str) -> None:
        pass

    @abstractmethod
    async def clear_active_shadow_target(self, telegram_id: int) -> None:
        pass

    @abstractmethod
    async def record_shadowing_attempt(
        self,
        telegram_id: int,
        target_text: str,
        user_transcript: str,
        match_score: int,
    ) -> None:
        pass

    @abstractmethod
    async def get_recent_shadowing(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_recent_sessions(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def add_vocab_item(
        self,
        telegram_id: int,
        original_phrase: str,
        correction: str,
        explanation: str = "",
    ) -> None:
        pass

    @abstractmethod
    async def get_user_vocab_bank(
        self, telegram_id: int, limit: int = 15
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_total_stats(self) -> Dict[str, int]:
        pass

    @abstractmethod
    async def create_ielts_session(
        self, telegram_id: int, exam_type: str, questions: List[Dict[str, Any]]
    ) -> int:
        pass

    @abstractmethod
    async def get_active_ielts_session(
        self, telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_ielts_session_progress(
        self, session_id: int, current_step: int, responses: List[Dict[str, Any]]
    ) -> None:
        pass

    @abstractmethod
    async def cancel_active_ielts_session(self, telegram_id: int) -> None:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_recent_ielts_results(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def set_user_reminder(
        self, telegram_id: int, reminder_time: str, enabled: bool
    ) -> None:
        pass

    @abstractmethod
    async def get_users_due_for_reminder(
        self, current_hh_mm: str, today_str: str
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def mark_user_reminded(
        self, telegram_id: int, date_str: str
    ) -> None:
        pass

    @abstractmethod
    async def set_active_phoneme_target(
        self, telegram_id: int, target_json: str
    ) -> None:
        pass

    @abstractmethod
    async def clear_active_phoneme_target(self, telegram_id: int) -> None:
        pass

    @abstractmethod
    async def set_active_tense_drill(
        self, telegram_id: int, drill_json: str
    ) -> None:
        pass

    @abstractmethod
    async def clear_active_tense_drill(self, telegram_id: int) -> None:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_recent_phoneme_drills(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_phoneme_stats(self, telegram_id: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def grant_user_premium(self, telegram_id: int) -> None:
        pass

    @abstractmethod
    async def claim_free_trial(self, telegram_id: int, days: int = 7) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def grant_user_subscription(
        self,
        telegram_id: int,
        days: int,
        tier_name: str,
        is_lifetime: bool = False,
        bonus_freeze: int = 3,
        bonus_xp: int = 250,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def expire_user_premium(self, telegram_id: int) -> None:
        pass

    @abstractmethod
    async def increment_daily_eval(self, telegram_id: int, today_str: str) -> int:
        pass

    @abstractmethod
    async def decrement_streak_freeze(self, telegram_id: int) -> None:
        pass

    @abstractmethod
    async def add_user_badge(self, telegram_id: int, badge_id: str) -> None:
        pass

    @abstractmethod
    async def get_practice_dates(self, telegram_id: int, limit: int = 30) -> List[str]:
        pass

    @abstractmethod
    async def get_linguistic_radar_metrics(self, telegram_id: int) -> Dict[str, float]:
        pass

    @abstractmethod
    async def add_dialogue_turn(self, telegram_id: int, scenario: str, role: str, content: str) -> None:
        pass

    @abstractmethod
    async def get_dialogue_history(
        self, telegram_id: int, scenario: str, limit: int = 20, max_age_hours: int = 2
    ) -> List[Dict[str, str]]:
        pass

    @abstractmethod
    async def clear_dialogue_history(self, telegram_id: int, scenario: Optional[str] = None) -> None:
        pass

    @abstractmethod
    async def add_referral(self, inviter_id: int, invitee_id: int) -> bool:
        pass

    @abstractmethod
    async def get_referral_stats(self, telegram_id: int) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def add_bonus_quota(self, telegram_id: int, amount: int) -> int:
        pass

    @abstractmethod
    async def add_streak_freeze(self, telegram_id: int, amount: int = 1) -> int:
        pass

    @abstractmethod
    async def add_xp(self, telegram_id: int, amount: int) -> int:
        pass


class CoachRepository(ICoachRepository):
    """SQLite implementation of ICoachRepository."""

    def __init__(self, db_path: str = "speaking_coach.db"):
        self.db_path = db_path

    async def upsert_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> None:
        if not aiosqlite:
            return
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (telegram_id, username, first_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_active = excluded.last_active;
                """,
                (telegram_id, username, first_name, now, now),
            )
            await db.commit()

    async def set_user_level(self, telegram_id: int, level: str) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET target_level = ? WHERE telegram_id = ?;",
                (level, telegram_id),
            )
            await db.commit()

    async def set_user_scenario(self, telegram_id: int, scenario: str) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET active_scenario = ? WHERE telegram_id = ?;",
                (scenario, telegram_id),
            )
            await db.commit()

    async def set_user_tts_voice(self, telegram_id: int, voice: str) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET tts_voice = ? WHERE telegram_id = ?;",
                (voice, telegram_id),
            )
            await db.commit()

    async def set_user_tts_speed(self, telegram_id: int, speed: str) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET tts_speed = ? WHERE telegram_id = ?;",
                (speed, telegram_id),
            )
            await db.commit()

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        if not aiosqlite:
            return None
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?;", (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_user_streak_and_xp(
        self,
        telegram_id: int,
        current_streak: int,
        max_streak: int,
        practice_date: str,
        total_xp: int,
    ) -> None:
        if not aiosqlite:
            return
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE users SET
                    current_streak = ?,
                    max_streak = ?,
                    last_practice_date = ?,
                    total_xp = ?,
                    last_active = ?
                WHERE telegram_id = ?;
                """,
                (current_streak, max_streak, practice_date, total_xp, now, telegram_id),
            )
            await db.commit()

    async def set_active_shadow_target(self, telegram_id: int, target_text: str) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET active_shadow_target = ? WHERE telegram_id = ?;",
                (target_text, telegram_id),
            )
            await db.commit()

    async def clear_active_shadow_target(self, telegram_id: int) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET active_shadow_target = '' WHERE telegram_id = ?;",
                (telegram_id,),
            )
            await db.commit()

    async def record_shadowing_attempt(
        self,
        telegram_id: int,
        target_text: str,
        user_transcript: str,
        match_score: int,
    ) -> None:
        if not aiosqlite:
            return
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO shadowing_history (telegram_id, target_text, user_transcript, match_score, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (telegram_id, target_text, user_transcript, match_score, now),
            )
            await db.commit()

    async def get_recent_shadowing(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not aiosqlite:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM shadowing_history 
                WHERE telegram_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?;
                """,
                (telegram_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

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
        if not aiosqlite:
            return
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO practice_sessions (
                    telegram_id, duration_seconds, transcript, feedback_summary, 
                    fluency_score, cefr_level, ielts_band, scenario, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    telegram_id,
                    duration_seconds,
                    transcript,
                    feedback_summary,
                    fluency_score,
                    cefr_level,
                    ielts_band,
                    scenario,
                    now,
                ),
            )
            await db.execute(
                """
                UPDATE users SET 
                    total_voice_notes = total_voice_notes + 1,
                    last_active = ?
                WHERE telegram_id = ?;
                """,
                (now, telegram_id),
            )
            await db.commit()

    async def get_recent_sessions(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not aiosqlite:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM practice_sessions 
                WHERE telegram_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?;
                """,
                (telegram_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def add_vocab_item(
        self,
        telegram_id: int,
        original_phrase: str,
        correction: str,
        explanation: str = "",
    ) -> None:
        if not aiosqlite:
            return
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO vocab_bank (telegram_id, original_phrase, correction, explanation, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (telegram_id, original_phrase, correction, explanation, now),
            )
            await db.commit()

    async def get_user_vocab_bank(
        self, telegram_id: int, limit: int = 15
    ) -> List[Dict[str, Any]]:
        if not aiosqlite:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM vocab_bank 
                WHERE telegram_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?;
                """,
                (telegram_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_total_stats(self) -> Dict[str, int]:
        if not aiosqlite:
            return {"total_users": 0, "total_sessions": 0, "total_vocab": 0}
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users;") as c1:
                u_count = (await c1.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM practice_sessions;") as c2:
                s_count = (await c2.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM vocab_bank;") as c3:
                v_count = (await c3.fetchone())[0]
            return {
                "total_users": u_count,
                "total_sessions": s_count,
                "total_vocab": v_count,
            }

    async def create_ielts_session(
        self, telegram_id: int, exam_type: str, questions: List[Dict[str, Any]]
    ) -> int:
        if not aiosqlite:
            return 0
        now = datetime.now(timezone.utc).isoformat()
        q_json = json.dumps(questions, ensure_ascii=False)
        async with aiosqlite.connect(self.db_path) as db:
            # Cancel any previous in_progress session for this user first
            await db.execute(
                "UPDATE ielts_mock_sessions SET status = 'abandoned' WHERE telegram_id = ? AND status = 'in_progress';",
                (telegram_id,),
            )
            cursor = await db.execute(
                """
                INSERT INTO ielts_mock_sessions (telegram_id, exam_type, current_step, questions_json, responses_json, status, created_at)
                VALUES (?, ?, 0, ?, '[]', 'in_progress', ?);
                """,
                (telegram_id, exam_type, q_json, now),
            )
            session_id = cursor.lastrowid
            await db.commit()
            return session_id

    async def get_active_ielts_session(
        self, telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        if not aiosqlite:
            return None
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM ielts_mock_sessions
                WHERE telegram_id = ? AND status = 'in_progress'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                data = dict(row)
                data["questions"] = json.loads(data["questions_json"])
                data["responses"] = json.loads(data["responses_json"])
                return data

    async def update_ielts_session_progress(
        self, session_id: int, current_step: int, responses: List[Dict[str, Any]]
    ) -> None:
        if not aiosqlite:
            return
        resp_json = json.dumps(responses, ensure_ascii=False)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE ielts_mock_sessions
                SET current_step = ?, responses_json = ?
                WHERE id = ?;
                """,
                (current_step, resp_json, session_id),
            )
            await db.commit()

    async def cancel_active_ielts_session(self, telegram_id: int) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE ielts_mock_sessions SET status = 'abandoned' WHERE telegram_id = ? AND status = 'in_progress';",
                (telegram_id,),
            )
            await db.commit()

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
        if not aiosqlite:
            return
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO ielts_mock_results (
                    telegram_id, exam_type, overall_band, fluency_coherence,
                    lexical_resource, grammar_accuracy, pronunciation,
                    examiner_commentary, target_improvements, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    telegram_id,
                    exam_type,
                    overall_band,
                    fluency_coherence,
                    lexical_resource,
                    grammar_accuracy,
                    pronunciation,
                    examiner_commentary,
                    target_improvements,
                    now,
                ),
            )
            # Mark session as completed
            await db.execute(
                "UPDATE ielts_mock_sessions SET status = 'completed' WHERE telegram_id = ? AND status = 'in_progress';",
                (telegram_id,),
            )
            await db.commit()

    async def get_recent_ielts_results(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not aiosqlite:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM ielts_mock_results
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (telegram_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def set_user_reminder(
        self, telegram_id: int, reminder_time: str, enabled: bool
    ) -> None:
        if not aiosqlite:
            return
        enabled_int = 1 if enabled else 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE users 
                SET reminder_time = ?, reminder_enabled = ?
                WHERE telegram_id = ?;
                """,
                (reminder_time, enabled_int, telegram_id),
            )
            await db.commit()

    async def get_users_due_for_reminder(
        self, current_hh_mm: str, today_str: str
    ) -> List[Dict[str, Any]]:
        if not aiosqlite:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM users
                WHERE reminder_enabled = 1
                  AND reminder_time = ?
                  AND (last_reminded_date IS NULL OR last_reminded_date != ?)
                  AND (last_practice_date IS NULL OR last_practice_date != ?);
                """,
                (current_hh_mm, today_str, today_str),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def mark_user_reminded(
        self, telegram_id: int, date_str: str
    ) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET last_reminded_date = ? WHERE telegram_id = ?;",
                (date_str, telegram_id),
            )
            await db.commit()

    async def set_active_phoneme_target(
        self, telegram_id: int, target_json: str
    ) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET active_phoneme_target = ? WHERE telegram_id = ?;",
                (target_json, telegram_id),
            )
            await db.commit()

    async def clear_active_phoneme_target(self, telegram_id: int) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET active_phoneme_target = '' WHERE telegram_id = ?;",
                (telegram_id,),
            )
            await db.commit()

    async def set_active_tense_drill(
        self, telegram_id: int, drill_json: str
    ) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET active_tense_drill = ? WHERE telegram_id = ?;",
                (drill_json, telegram_id),
            )
            await db.commit()

    async def clear_active_tense_drill(self, telegram_id: int) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET active_tense_drill = '' WHERE telegram_id = ?;",
                (telegram_id,),
            )
            await db.commit()

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
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO tense_exercises (
                    telegram_id, tense_id, tense_title, user_transcript,
                    accuracy_score, is_target_tense_used, verb_form_analysis, coaching_tip
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    telegram_id,
                    tense_id,
                    tense_title,
                    user_transcript,
                    accuracy_score,
                    1 if is_target_tense_used else 0,
                    verb_form_analysis,
                    coaching_tip,
                ),
            )
            await db.commit()

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
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO phoneme_drills (
                    telegram_id, category_id, pair_id, pair_label, target_words,
                    user_transcript, accuracy_score, is_distinction_clear,
                    detected_ipa, mouth_position_tip
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    telegram_id,
                    category_id,
                    pair_id,
                    pair_label,
                    target_words,
                    user_transcript,
                    accuracy_score,
                    1 if is_distinction_clear else 0,
                    detected_ipa,
                    mouth_position_tip,
                ),
            )
            await db.commit()

    async def get_recent_phoneme_drills(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        if not aiosqlite:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM phoneme_drills
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (telegram_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def get_phoneme_stats(self, telegram_id: int) -> Dict[str, Any]:
        if not aiosqlite:
            return {"total_drills": 0, "avg_accuracy": 0.0, "clear_distinctions": 0}
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT 
                    COUNT(*) as total_drills,
                    COALESCE(AVG(accuracy_score), 0.0) as avg_accuracy,
                    COALESCE(SUM(CASE WHEN is_distinction_clear = 1 THEN 1 ELSE 0 END), 0) as clear_distinctions
                FROM phoneme_drills
                WHERE telegram_id = ?;
                """,
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "total_drills": row[0],
                        "avg_accuracy": round(float(row[1]), 1),
                        "clear_distinctions": row[2],
                    }
                return {"total_drills": 0, "avg_accuracy": 0.0, "clear_distinctions": 0}

    async def grant_user_premium(self, telegram_id: int) -> None:
        await self.grant_user_subscription(
            telegram_id=telegram_id,
            days=0,
            tier_name="lifetime",
            is_lifetime=True,
            bonus_freeze=3,
            bonus_xp=250,
        )

    async def claim_free_trial(self, telegram_id: int, days: int = 7) -> Dict[str, Any]:
        if not aiosqlite:
            return {"success": False, "message": "Database tidak tersedia."}
        now = datetime.now(timezone.utc)
        expires_dt = now + timedelta(days=days)
        expires_at = expires_dt.isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT has_used_trial, is_premium, premium_tier FROM users WHERE telegram_id = ?;",
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return {"success": False, "message": "User belum terdaftar. Ketik /start terlebih dahulu."}
                if row["has_used_trial"] == 1:
                    return {"success": False, "message": "Anda sudah pernah mengklaim Free Trial 7 Hari sebelumnya."}

            await db.execute(
                """
                UPDATE users
                SET is_premium = 1,
                    premium_tier = 'trial_7d',
                    premium_until = ?,
                    has_used_trial = 1
                WHERE telegram_id = ?;
                """,
                (expires_at, telegram_id),
            )
            await db.commit()
            return {"success": True, "expires_at": expires_at, "days": days}

    async def grant_user_subscription(
        self,
        telegram_id: int,
        days: int,
        tier_name: str,
        is_lifetime: bool = False,
        bonus_freeze: int = 3,
        bonus_xp: int = 250,
    ) -> Dict[str, Any]:
        if not aiosqlite:
            return {"success": False, "message": "Database tidak tersedia."}

        now = datetime.now(timezone.utc)
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT is_premium, premium_tier, premium_until FROM users WHERE telegram_id = ?;",
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()

            if is_lifetime:
                await db.execute(
                    """
                    UPDATE users
                    SET is_premium = 1,
                        premium_tier = 'lifetime',
                        premium_until = '',
                        streak_freeze_count = streak_freeze_count + ?,
                        total_xp = total_xp + ?
                    WHERE telegram_id = ?;
                    """,
                    (bonus_freeze, bonus_xp, telegram_id),
                )
                await db.commit()
                return {"success": True, "tier": "lifetime", "is_lifetime": True, "expires_at": ""}

            # Akumulatif: jika masih ada sisa waktu aktif, tambahkan dari expiry lama
            existing_until_str = row["premium_until"] if row and row["premium_until"] else ""
            base_dt = now
            if existing_until_str:
                try:
                    existing_dt = datetime.fromisoformat(existing_until_str)
                    if existing_dt.tzinfo is None:
                        existing_dt = existing_dt.replace(tzinfo=timezone.utc)
                    if existing_dt > now:
                        base_dt = existing_dt
                except Exception:
                    base_dt = now

            new_expires_dt = base_dt + timedelta(days=days)
            new_expires_str = new_expires_dt.isoformat()

            await db.execute(
                """
                UPDATE users
                SET is_premium = 1,
                    premium_tier = ?,
                    premium_until = ?,
                    streak_freeze_count = streak_freeze_count + ?,
                    total_xp = total_xp + ?
                WHERE telegram_id = ?;
                """,
                (tier_name, new_expires_str, bonus_freeze, bonus_xp, telegram_id),
            )
            await db.commit()
            return {
                "success": True,
                "tier": tier_name,
                "is_lifetime": False,
                "expires_at": new_expires_str,
                "days_added": days,
            }

    async def expire_user_premium(self, telegram_id: int) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE users
                SET is_premium = 0, premium_tier = 'expired'
                WHERE telegram_id = ?;
                """,
                (telegram_id,),
            )
            await db.commit()

    async def increment_daily_eval(self, telegram_id: int, today_str: str) -> int:
        if not aiosqlite:
            return 1
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT daily_eval_date, daily_eval_count FROM users WHERE telegram_id = ?;", (telegram_id,)) as cursor:
                row = await cursor.fetchone()
                if not row or row["daily_eval_date"] != today_str:
                    new_count = 1
                else:
                    new_count = (row["daily_eval_count"] or 0) + 1

            await db.execute(
                "UPDATE users SET daily_eval_date = ?, daily_eval_count = ? WHERE telegram_id = ?;",
                (today_str, new_count, telegram_id),
            )
            await db.commit()
            return new_count

    async def decrement_streak_freeze(self, telegram_id: int) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET streak_freeze_count = MAX(0, streak_freeze_count - 1) WHERE telegram_id = ?;",
                (telegram_id,),
            )
            await db.commit()

    async def add_user_badge(self, telegram_id: int, badge_id: str) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT badges_json FROM users WHERE telegram_id = ?;", (telegram_id,)) as cursor:
                row = await cursor.fetchone()
                badges = []
                if row and row["badges_json"]:
                    try:
                        badges = json.loads(row["badges_json"])
                    except Exception:
                        badges = []
                if badge_id not in badges:
                    badges.append(badge_id)
                    await db.execute(
                        "UPDATE users SET badges_json = ? WHERE telegram_id = ?;",
                        (json.dumps(badges), telegram_id),
                    )
                    await db.commit()

    async def get_practice_dates(self, telegram_id: int, limit: int = 30) -> List[str]:
        if not aiosqlite:
            return []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT DISTINCT substr(created_at, 1, 10) as p_date 
                FROM practice_sessions 
                WHERE telegram_id = ? 
                ORDER BY p_date DESC 
                LIMIT ?;
                """,
                (telegram_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [r[0] for r in rows if r[0]]

    async def get_linguistic_radar_metrics(self, telegram_id: int) -> Dict[str, float]:
        if not aiosqlite:
            return {"fluency": 65.0, "pronunciation": 70.0, "grammar": 75.0, "lexical": 70.0}
        async with aiosqlite.connect(self.db_path) as db:
            # 1. Fluency from practice_sessions
            async with db.execute(
                "SELECT AVG(fluency_score) FROM (SELECT fluency_score FROM practice_sessions WHERE telegram_id = ? ORDER BY id DESC LIMIT 10);",
                (telegram_id,),
            ) as c1:
                f_row = await c1.fetchone()
                fluency = float(f_row[0]) if f_row and f_row[0] is not None else 65.0

            # 2. Pronunciation from phoneme_drills
            async with db.execute(
                "SELECT AVG(accuracy_score) FROM (SELECT accuracy_score FROM phoneme_drills WHERE telegram_id = ? ORDER BY id DESC LIMIT 10);",
                (telegram_id,),
            ) as c2:
                p_row = await c2.fetchone()
                pron = float(p_row[0]) if p_row and p_row[0] is not None else 70.0

            # 3. Grammar from recent session slips
            async with db.execute("SELECT COUNT(*) FROM vocab_bank WHERE telegram_id = ?;", (telegram_id,)) as c3:
                g_row = await c3.fetchone()
                slip_count = g_row[0] if g_row else 0
                grammar = max(55.0, min(95.0, 90.0 - (slip_count * 2.0)))

            # 4. Lexical resource
            async with db.execute("SELECT AVG(lexical_resource) FROM ielts_mock_results WHERE telegram_id = ?;", (telegram_id,)) as c4:
                l_row = await c4.fetchone()
                if l_row and l_row[0] is not None:
                    lexical = min(100.0, float(l_row[0]) * 10.0 + 10.0)
                else:
                    lexical = min(90.0, 65.0 + (slip_count * 1.5))

            return {
                "fluency": round(fluency, 1),
                "pronunciation": round(pron, 1),
                "grammar": round(grammar, 1),
                "lexical": round(lexical, 1),
            }

    async def add_dialogue_turn(self, telegram_id: int, scenario: str, role: str, content: str) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO dialogue_turns (telegram_id, scenario, role, content)
                VALUES (?, ?, ?, ?);
                """,
                (telegram_id, scenario, role, content),
            )
            await db.commit()

    async def get_dialogue_history(
        self, telegram_id: int, scenario: str, limit: int = 20, max_age_hours: int = 2
    ) -> List[Dict[str, str]]:
        if not aiosqlite:
            return []
        cutoff_dt = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content FROM dialogue_turns
                    WHERE telegram_id = ? AND scenario = ? AND created_at >= ?
                    ORDER BY id DESC
                    LIMIT ?
                ) ORDER BY id ASC;
                """,
                (telegram_id, scenario, cutoff_dt, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [{"role": r["role"], "content": r["content"]} for r in rows]

    async def clear_dialogue_history(self, telegram_id: int, scenario: Optional[str] = None) -> None:
        if not aiosqlite:
            return
        async with aiosqlite.connect(self.db_path) as db:
            if scenario:
                await db.execute(
                    "DELETE FROM dialogue_turns WHERE telegram_id = ? AND scenario = ?;",
                    (telegram_id, scenario),
                )
            else:
                await db.execute(
                    "DELETE FROM dialogue_turns WHERE telegram_id = ?;",
                    (telegram_id,),
                )
            await db.commit()

    async def add_referral(self, inviter_id: int, invitee_id: int) -> bool:
        if not aiosqlite:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    "INSERT INTO referrals (inviter_id, invitee_id) VALUES (?, ?);",
                    (inviter_id, invitee_id),
                )
                await db.execute(
                    "UPDATE users SET invited_by = ? WHERE telegram_id = ?;",
                    (inviter_id, invitee_id),
                )
                await db.commit()
                return True
            except Exception as e:
                logger.warning("Could not add referral (%s -> %s): %s", inviter_id, invitee_id, e)
                return False

    async def get_referral_stats(self, telegram_id: int) -> Dict[str, Any]:
        if not aiosqlite:
            return {"total_referred": 0, "bonus_quota_earned": 0, "streak_freezes_earned": 0}
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT COUNT(*) as count FROM referrals WHERE inviter_id = ?;",
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                count = row["count"] if row else 0
                return {
                    "total_referred": count,
                    "bonus_quota_earned": count * 3,
                    "streak_freezes_earned": count,
                }

    async def add_bonus_quota(self, telegram_id: int, amount: int) -> int:
        if not aiosqlite:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET bonus_quota = bonus_quota + ? WHERE telegram_id = ?;",
                (amount, telegram_id),
            )
            await db.commit()
            async with db.execute(
                "SELECT bonus_quota FROM users WHERE telegram_id = ?;",
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def add_streak_freeze(self, telegram_id: int, amount: int = 1) -> int:
        if not aiosqlite:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET streak_freeze_count = streak_freeze_count + ? WHERE telegram_id = ?;",
                (amount, telegram_id),
            )
            await db.commit()
            async with db.execute(
                "SELECT streak_freeze_count FROM users WHERE telegram_id = ?;",
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def add_xp(self, telegram_id: int, amount: int) -> int:
        if not aiosqlite:
            return 0
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET total_xp = total_xp + ? WHERE telegram_id = ?;",
                (amount, telegram_id),
            )
            await db.commit()
            async with db.execute(
                "SELECT total_xp FROM users WHERE telegram_id = ?;",
                (telegram_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0



