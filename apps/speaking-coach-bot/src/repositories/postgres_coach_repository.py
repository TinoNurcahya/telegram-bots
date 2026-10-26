import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

try:
    import asyncpg
except ImportError:
    asyncpg = None

from src.repositories.coach_repository import ICoachRepository

logger = logging.getLogger(__name__)


class PostgresCoachRepository(ICoachRepository):
    """PostgreSQL implementation of ICoachRepository using asyncpg connection pooling."""

    def __init__(self, dsn: str = "", pool: Optional[Any] = None):
        self.dsn = dsn
        self._pool = pool

    async def get_pool(self):
        """Get or initialize the asyncpg connection pool."""
        if self._pool is None:
            if not asyncpg:
                raise RuntimeError("asyncpg is not installed. Please install asyncpg>=0.30.0")
            self._pool = await asyncpg.create_pool(
                dsn=self.dsn,
                min_size=1,
                max_size=10,
                statement_cache_size=0,
            )
        return self._pool

    async def close(self) -> None:
        """Close connection pool gracefully."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def init_schema(self) -> None:
        """Initialize database tables and indexes for PostgreSQL."""
        if not asyncpg and self._pool is None:
            logger.warning("asyncpg is not installed. Skipping PostgreSQL schema initialization.")
            return

        pool = await self.get_pool()
        async with pool.acquire() as conn:
            # Users table
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    target_level TEXT DEFAULT 'Intermediate',
                    active_scenario TEXT DEFAULT 'Free Conversation',
                    tts_voice TEXT DEFAULT 'en-US-JennyNeural',
                    total_voice_notes INTEGER DEFAULT 0,
                    current_streak INTEGER DEFAULT 0,
                    max_streak INTEGER DEFAULT 0,
                    last_practice_date TEXT DEFAULT '',
                    total_xp INTEGER DEFAULT 0,
                    active_shadow_target TEXT DEFAULT '',
                    active_phoneme_target TEXT DEFAULT '',
                    active_tense_drill TEXT DEFAULT '',
                    reminder_time TEXT DEFAULT '20:00',
                    reminder_enabled INTEGER DEFAULT 1,
                    reminder_timezone TEXT DEFAULT 'Asia/Jakarta',
                    last_reminded_date TEXT DEFAULT '',
                    streak_freeze_count INTEGER DEFAULT 1,
                    is_premium INTEGER DEFAULT 0,
                    premium_until TEXT DEFAULT '',
                    premium_tier TEXT DEFAULT '',
                    has_used_trial INTEGER DEFAULT 0,
                    daily_eval_count INTEGER DEFAULT 0,
                    daily_eval_date TEXT DEFAULT '',
                    badges_json TEXT DEFAULT '[]',
                    tts_speed TEXT DEFAULT '+0%',
                    bonus_quota INTEGER DEFAULT 0,
                    invited_by BIGINT DEFAULT 0,
                    created_at TEXT,
                    last_active TEXT
                );
                """
            )

            # Practice sessions
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS practice_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    duration_seconds INTEGER DEFAULT 0,
                    transcript TEXT,
                    feedback_summary TEXT,
                    fluency_score INTEGER DEFAULT 0,
                    cefr_level TEXT DEFAULT 'B1',
                    ielts_band REAL DEFAULT 6.0,
                    scenario TEXT DEFAULT 'Free Conversation',
                    created_at TEXT
                );
                """
            )

            # Vocab bank
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vocab_bank (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    original_phrase TEXT NOT NULL,
                    correction TEXT NOT NULL,
                    explanation TEXT,
                    created_at TEXT
                );
                """
            )

            # Shadowing history
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS shadowing_history (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    target_text TEXT NOT NULL,
                    user_transcript TEXT NOT NULL,
                    match_score INTEGER NOT NULL,
                    created_at TEXT
                );
                """
            )

            # IELTS mock exam active sessions
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ielts_mock_sessions (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    exam_type TEXT NOT NULL,
                    current_step INTEGER DEFAULT 0,
                    questions_json TEXT NOT NULL,
                    responses_json TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'in_progress',
                    created_at TEXT
                );
                """
            )

            # IELTS mock results
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ielts_mock_results (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    exam_type TEXT NOT NULL,
                    overall_band REAL NOT NULL,
                    fluency_coherence REAL NOT NULL,
                    lexical_resource REAL NOT NULL,
                    grammar_accuracy REAL NOT NULL,
                    pronunciation REAL NOT NULL,
                    examiner_commentary TEXT,
                    target_improvements TEXT,
                    created_at TEXT
                );
                """
            )

            # Phoneme drills
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS phoneme_drills (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    category_id TEXT NOT NULL,
                    pair_id TEXT NOT NULL,
                    pair_label TEXT NOT NULL,
                    target_words TEXT NOT NULL,
                    user_transcript TEXT NOT NULL,
                    accuracy_score INTEGER NOT NULL,
                    is_distinction_clear INTEGER NOT NULL,
                    detected_ipa TEXT DEFAULT '',
                    mouth_position_tip TEXT DEFAULT '',
                    created_at TEXT
                );
                """
            )

            # Multi-turn Dialogue turns
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dialogue_turns (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    scenario TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )

            # Referrals and viral growth
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS referrals (
                    id BIGSERIAL PRIMARY KEY,
                    inviter_id BIGINT NOT NULL,
                    invitee_id BIGINT NOT NULL UNIQUE,
                    reward_claimed INTEGER DEFAULT 1,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )

            # Tense exercises
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tense_exercises (
                    id BIGSERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    tense_id TEXT NOT NULL,
                    tense_title TEXT NOT NULL,
                    user_transcript TEXT NOT NULL,
                    accuracy_score INTEGER NOT NULL,
                    is_target_tense_used INTEGER NOT NULL,
                    verb_form_analysis TEXT DEFAULT '',
                    coaching_tip TEXT DEFAULT '',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                """
            )

            # Column migrations for existing tables
            cols = [
                ("active_tense_drill", "TEXT DEFAULT ''"),
                ("tts_speed", "TEXT DEFAULT '+0%'"),
                ("premium_until", "TEXT DEFAULT ''"),
                ("premium_tier", "TEXT DEFAULT ''"),
                ("has_used_trial", "INTEGER DEFAULT 0"),
                ("bonus_quota", "INTEGER DEFAULT 0"),
                ("invited_by", "BIGINT DEFAULT 0"),
            ]
            for col, col_type in cols:
                try:
                    await conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type};")
                except Exception:
                    pass

            # Indexes
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_sessions_user ON practice_sessions(telegram_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_vocab_user ON vocab_bank(telegram_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_shadow_user ON shadowing_history(telegram_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_ielts_sessions_user ON ielts_mock_sessions(telegram_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_ielts_results_user ON ielts_mock_results(telegram_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_phoneme_user ON phoneme_drills(telegram_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_dialogue_user_scenario ON dialogue_turns(telegram_id, scenario);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_referrals_inviter ON referrals(inviter_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_tenses_user ON tense_exercises(telegram_id);")

        logger.info("PostgreSQL Speaking Coach schema and indexes initialized.")

    async def upsert_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
    ) -> None:
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (telegram_id, username, first_name, created_at, last_active)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (telegram_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_active = EXCLUDED.last_active;
                """,
                telegram_id,
                username,
                first_name,
                now,
                now,
            )

    async def set_user_level(self, telegram_id: int, level: str) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET target_level = $1 WHERE telegram_id = $2;",
                level,
                telegram_id,
            )

    async def set_user_scenario(self, telegram_id: int, scenario: str) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET active_scenario = $1 WHERE telegram_id = $2;",
                scenario,
                telegram_id,
            )

    async def set_user_tts_voice(self, telegram_id: int, voice: str) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET tts_voice = $1 WHERE telegram_id = $2;",
                voice,
                telegram_id,
            )

    async def set_user_tts_speed(self, telegram_id: int, speed: str) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET tts_speed = $1 WHERE telegram_id = $2;",
                speed,
                telegram_id,
            )

    async def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1;", telegram_id
            )
            return dict(row) if row else None

    async def update_user_streak_and_xp(
        self,
        telegram_id: int,
        current_streak: int,
        max_streak: int,
        practice_date: str,
        total_xp: int,
    ) -> None:
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users SET
                    current_streak = $1,
                    max_streak = $2,
                    last_practice_date = $3,
                    total_xp = $4,
                    last_active = $5
                WHERE telegram_id = $6;
                """,
                current_streak,
                max_streak,
                practice_date,
                total_xp,
                now,
                telegram_id,
            )

    async def set_active_shadow_target(self, telegram_id: int, target_text: str) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET active_shadow_target = $1 WHERE telegram_id = $2;",
                target_text,
                telegram_id,
            )

    async def clear_active_shadow_target(self, telegram_id: int) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET active_shadow_target = '' WHERE telegram_id = $1;",
                telegram_id,
            )

    async def record_shadowing_attempt(
        self,
        telegram_id: int,
        target_text: str,
        user_transcript: str,
        match_score: int,
    ) -> None:
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO shadowing_history (telegram_id, target_text, user_transcript, match_score, created_at)
                VALUES ($1, $2, $3, $4, $5);
                """,
                telegram_id,
                target_text,
                user_transcript,
                match_score,
                now,
            )

    async def get_recent_shadowing(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM shadowing_history 
                WHERE telegram_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2;
                """,
                telegram_id,
                limit,
            )
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
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO practice_sessions (
                    telegram_id, duration_seconds, transcript, feedback_summary, 
                    fluency_score, cefr_level, ielts_band, scenario, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
                """,
                telegram_id,
                duration_seconds,
                transcript,
                feedback_summary,
                fluency_score,
                cefr_level,
                ielts_band,
                scenario,
                now,
            )
            await conn.execute(
                """
                UPDATE users SET 
                    total_voice_notes = total_voice_notes + 1,
                    last_active = $1
                WHERE telegram_id = $2;
                """,
                now,
                telegram_id,
            )

    async def get_recent_sessions(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM practice_sessions 
                WHERE telegram_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2;
                """,
                telegram_id,
                limit,
            )
            return [dict(r) for r in rows]

    async def add_vocab_item(
        self,
        telegram_id: int,
        original_phrase: str,
        correction: str,
        explanation: str = "",
    ) -> None:
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO vocab_bank (telegram_id, original_phrase, correction, explanation, created_at)
                VALUES ($1, $2, $3, $4, $5);
                """,
                telegram_id,
                original_phrase,
                correction,
                explanation,
                now,
            )

    async def get_user_vocab_bank(
        self, telegram_id: int, limit: int = 15
    ) -> List[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM vocab_bank 
                WHERE telegram_id = $1 
                ORDER BY created_at DESC 
                LIMIT $2;
                """,
                telegram_id,
                limit,
            )
            return [dict(r) for r in rows]

    async def get_total_stats(self) -> Dict[str, int]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            u_count = await conn.fetchval("SELECT COUNT(*) FROM users;")
            s_count = await conn.fetchval("SELECT COUNT(*) FROM practice_sessions;")
            v_count = await conn.fetchval("SELECT COUNT(*) FROM vocab_bank;")
            return {
                "total_users": int(u_count or 0),
                "total_sessions": int(s_count or 0),
                "total_vocab": int(v_count or 0),
            }

    async def create_ielts_session(
        self, telegram_id: int, exam_type: str, questions: List[Dict[str, Any]]
    ) -> int:
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        q_json = json.dumps(questions, ensure_ascii=False)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE ielts_mock_sessions SET status = 'abandoned' WHERE telegram_id = $1 AND status = 'in_progress';",
                telegram_id,
            )
            row = await conn.fetchrow(
                """
                INSERT INTO ielts_mock_sessions (telegram_id, exam_type, current_step, questions_json, responses_json, status, created_at)
                VALUES ($1, $2, 0, $3, '[]', 'in_progress', $4)
                RETURNING id;
                """,
                telegram_id,
                exam_type,
                q_json,
                now,
            )
            return row["id"] if row else 0

    async def get_active_ielts_session(
        self, telegram_id: int
    ) -> Optional[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM ielts_mock_sessions
                WHERE telegram_id = $1 AND status = 'in_progress'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                telegram_id,
            )
            if not row:
                return None
            data = dict(row)
            data["questions"] = json.loads(data["questions_json"])
            data["responses"] = json.loads(data["responses_json"])
            return data

    async def update_ielts_session_progress(
        self, session_id: int, current_step: int, responses: List[Dict[str, Any]]
    ) -> None:
        pool = await self.get_pool()
        resp_json = json.dumps(responses, ensure_ascii=False)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE ielts_mock_sessions
                SET current_step = $1, responses_json = $2
                WHERE id = $3;
                """,
                current_step,
                resp_json,
                session_id,
            )

    async def cancel_active_ielts_session(self, telegram_id: int) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE ielts_mock_sessions SET status = 'abandoned' WHERE telegram_id = $1 AND status = 'in_progress';",
                telegram_id,
            )

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
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ielts_mock_results (
                    telegram_id, exam_type, overall_band, fluency_coherence,
                    lexical_resource, grammar_accuracy, pronunciation,
                    examiner_commentary, target_improvements, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10);
                """,
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
            )
            await conn.execute(
                "UPDATE ielts_mock_sessions SET status = 'completed' WHERE telegram_id = $1 AND status = 'in_progress';",
                telegram_id,
            )

    async def get_recent_ielts_results(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM ielts_mock_results
                WHERE telegram_id = $1
                ORDER BY created_at DESC
                LIMIT $2;
                """,
                telegram_id,
                limit,
            )
            return [dict(r) for r in rows]

    async def set_user_reminder(
        self, telegram_id: int, reminder_time: str, enabled: bool
    ) -> None:
        pool = await self.get_pool()
        enabled_int = 1 if enabled else 0
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users 
                SET reminder_time = $1, reminder_enabled = $2
                WHERE telegram_id = $3;
                """,
                reminder_time,
                enabled_int,
                telegram_id,
            )

    async def get_users_due_for_reminder(
        self, current_hh_mm: str, today_str: str
    ) -> List[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM users
                WHERE reminder_enabled = 1
                  AND reminder_time = $1
                  AND (last_reminded_date IS NULL OR last_reminded_date != $2)
                  AND (last_practice_date IS NULL OR last_practice_date != $3);
                """,
                current_hh_mm,
                today_str,
                today_str,
            )
            return [dict(r) for r in rows]

    async def mark_user_reminded(
        self, telegram_id: int, date_str: str
    ) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_reminded_date = $1 WHERE telegram_id = $2;",
                date_str,
                telegram_id,
            )

    async def set_active_phoneme_target(
        self, telegram_id: int, target_json: str
    ) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET active_phoneme_target = $1 WHERE telegram_id = $2;",
                target_json,
                telegram_id,
            )

    async def clear_active_phoneme_target(self, telegram_id: int) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET active_phoneme_target = '' WHERE telegram_id = $1;",
                telegram_id,
            )

    async def set_active_tense_drill(
        self, telegram_id: int, drill_json: str
    ) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET active_tense_drill = $1 WHERE telegram_id = $2;",
                drill_json,
                telegram_id,
            )

    async def clear_active_tense_drill(self, telegram_id: int) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET active_tense_drill = '' WHERE telegram_id = $1;",
                telegram_id,
            )

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
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tense_exercises (
                    telegram_id, tense_id, tense_title, user_transcript,
                    accuracy_score, is_target_tense_used, verb_form_analysis, coaching_tip
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
                """,
                telegram_id,
                tense_id,
                tense_title,
                user_transcript,
                accuracy_score,
                1 if is_target_tense_used else 0,
                verb_form_analysis,
                coaching_tip,
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
        pool = await self.get_pool()
        now = datetime.now(timezone.utc).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO phoneme_drills (
                    telegram_id, category_id, pair_id, pair_label, target_words,
                    user_transcript, accuracy_score, is_distinction_clear,
                    detected_ipa, mouth_position_tip, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11);
                """,
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
                now,
            )

    async def get_recent_phoneme_drills(
        self, telegram_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM phoneme_drills
                WHERE telegram_id = $1
                ORDER BY created_at DESC
                LIMIT $2;
                """,
                telegram_id,
                limit,
            )
            return [dict(r) for r in rows]

    async def get_phoneme_stats(self, telegram_id: int) -> Dict[str, Any]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_drills,
                    COALESCE(AVG(accuracy_score), 0.0) as avg_accuracy,
                    COALESCE(SUM(CASE WHEN is_distinction_clear = 1 THEN 1 ELSE 0 END), 0) as clear_distinctions
                FROM phoneme_drills
                WHERE telegram_id = $1;
                """,
                telegram_id,
            )
            if row:
                return {
                    "total_drills": int(row["total_drills"] or 0),
                    "avg_accuracy": round(float(row["avg_accuracy"] or 0.0), 1),
                    "clear_distinctions": int(row["clear_distinctions"] or 0),
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
        pool = await self.get_pool()
        now = datetime.now(timezone.utc)
        expires_dt = now + timedelta(days=days)
        expires_at = expires_dt.isoformat()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT has_used_trial, is_premium, premium_tier FROM users WHERE telegram_id = $1;",
                telegram_id,
            )
            if not row:
                return {"success": False, "message": "User belum terdaftar. Ketik /start terlebih dahulu."}
            if row.get("has_used_trial") == 1:
                return {"success": False, "message": "Anda sudah pernah mengklaim Free Trial 7 Hari sebelumnya."}

            await conn.execute(
                """
                UPDATE users
                SET is_premium = 1,
                    premium_tier = 'trial_7d',
                    premium_until = $1,
                    has_used_trial = 1
                WHERE telegram_id = $2;
                """,
                expires_at,
                telegram_id,
            )
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
        pool = await self.get_pool()
        now = datetime.now(timezone.utc)

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT is_premium, premium_tier, premium_until FROM users WHERE telegram_id = $1;",
                telegram_id,
            )

            if is_lifetime:
                await conn.execute(
                    """
                    UPDATE users
                    SET is_premium = 1,
                        premium_tier = 'lifetime',
                        premium_until = '',
                        streak_freeze_count = streak_freeze_count + $1,
                        total_xp = total_xp + $2
                    WHERE telegram_id = $3;
                    """,
                    bonus_freeze,
                    bonus_xp,
                    telegram_id,
                )
                return {"success": True, "tier": "lifetime", "is_lifetime": True, "expires_at": ""}

            existing_until_str = row.get("premium_until") if row and row.get("premium_until") else ""
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

            await conn.execute(
                """
                UPDATE users
                SET is_premium = 1,
                    premium_tier = $1,
                    premium_until = $2,
                    streak_freeze_count = streak_freeze_count + $3,
                    total_xp = total_xp + $4
                WHERE telegram_id = $5;
                """,
                tier_name,
                new_expires_str,
                bonus_freeze,
                bonus_xp,
                telegram_id,
            )
            return {
                "success": True,
                "tier": tier_name,
                "is_lifetime": False,
                "expires_at": new_expires_str,
                "days_added": days,
            }

    async def expire_user_premium(self, telegram_id: int) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET is_premium = 0, premium_tier = 'expired'
                WHERE telegram_id = $1;
                """,
                telegram_id,
            )

    async def increment_daily_eval(self, telegram_id: int, today_str: str) -> int:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT daily_eval_date, daily_eval_count FROM users WHERE telegram_id = $1;",
                telegram_id,
            )
            if not row or row["daily_eval_date"] != today_str:
                new_count = 1
            else:
                new_count = (row["daily_eval_count"] or 0) + 1

            await conn.execute(
                "UPDATE users SET daily_eval_date = $1, daily_eval_count = $2 WHERE telegram_id = $3;",
                today_str,
                new_count,
                telegram_id,
            )
            return new_count

    async def decrement_streak_freeze(self, telegram_id: int) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET streak_freeze_count = GREATEST(0, streak_freeze_count - 1) WHERE telegram_id = $1;",
                telegram_id,
            )

    async def add_user_badge(self, telegram_id: int, badge_id: str) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT badges_json FROM users WHERE telegram_id = $1;",
                telegram_id,
            )
            badges = []
            if row and row["badges_json"]:
                try:
                    badges = json.loads(row["badges_json"])
                except Exception:
                    badges = []
            if badge_id not in badges:
                badges.append(badge_id)
                await conn.execute(
                    "UPDATE users SET badges_json = $1 WHERE telegram_id = $2;",
                    json.dumps(badges),
                    telegram_id,
                )

    async def get_practice_dates(self, telegram_id: int, limit: int = 30) -> List[str]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT SUBSTRING(created_at FROM 1 FOR 10) as p_date 
                FROM practice_sessions 
                WHERE telegram_id = $1 
                ORDER BY p_date DESC 
                LIMIT $2;
                """,
                telegram_id,
                limit,
            )
            return [r["p_date"] for r in rows if r["p_date"]]

    async def get_linguistic_radar_metrics(self, telegram_id: int) -> Dict[str, float]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            f_val = await conn.fetchval(
                "SELECT AVG(fluency_score) FROM (SELECT fluency_score FROM practice_sessions WHERE telegram_id = $1 ORDER BY id DESC LIMIT 10) s;",
                telegram_id,
            )
            fluency = float(f_val) if f_val is not None else 65.0

            p_val = await conn.fetchval(
                "SELECT AVG(accuracy_score) FROM (SELECT accuracy_score FROM phoneme_drills WHERE telegram_id = $1 ORDER BY id DESC LIMIT 10) s;",
                telegram_id,
            )
            pron = float(p_val) if p_val is not None else 70.0

            slip_count = await conn.fetchval("SELECT COUNT(*) FROM vocab_bank WHERE telegram_id = $1;", telegram_id)
            slip_count = int(slip_count or 0)
            grammar = max(55.0, min(95.0, 90.0 - (slip_count * 2.0)))

            l_val = await conn.fetchval("SELECT AVG(lexical_resource) FROM ielts_mock_results WHERE telegram_id = $1;", telegram_id)
            if l_val is not None:
                lexical = min(100.0, float(l_val) * 10.0 + 10.0)
            else:
                lexical = min(90.0, 65.0 + (slip_count * 1.5))

            return {
                "fluency": round(fluency, 1),
                "pronunciation": round(pron, 1),
                "grammar": round(grammar, 1),
                "lexical": round(lexical, 1),
            }

    async def add_dialogue_turn(self, telegram_id: int, scenario: str, role: str, content: str) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO dialogue_turns (telegram_id, scenario, role, content)
                VALUES ($1, $2, $3, $4);
                """,
                telegram_id,
                scenario,
                role,
                content,
            )

    async def get_dialogue_history(
        self, telegram_id: int, scenario: str, limit: int = 20, max_age_hours: int = 2
    ) -> List[Dict[str, str]]:
        pool = await self.get_pool()
        cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content FROM (
                    SELECT id, role, content FROM dialogue_turns
                    WHERE telegram_id = $1 AND scenario = $2 AND created_at >= $3
                    ORDER BY id DESC
                    LIMIT $4
                ) s ORDER BY id ASC;
                """,
                telegram_id,
                scenario,
                cutoff_dt,
                limit,
            )
            return [{"role": r["role"], "content": r["content"]} for r in rows]

    async def clear_dialogue_history(self, telegram_id: int, scenario: Optional[str] = None) -> None:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if scenario:
                await conn.execute(
                    "DELETE FROM dialogue_turns WHERE telegram_id = $1 AND scenario = $2;",
                    telegram_id,
                    scenario,
                )
            else:
                await conn.execute(
                    "DELETE FROM dialogue_turns WHERE telegram_id = $1;",
                    telegram_id,
                )

    async def add_referral(self, inviter_id: int, invitee_id: int) -> bool:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            try:
                await conn.execute(
                    "INSERT INTO referrals (inviter_id, invitee_id) VALUES ($1, $2);",
                    inviter_id,
                    invitee_id,
                )
                await conn.execute(
                    "UPDATE users SET invited_by = $1 WHERE telegram_id = $2;",
                    inviter_id,
                    invitee_id,
                )
                return True
            except Exception as e:
                logger.warning("Could not add referral in Postgres (%s -> %s): %s", inviter_id, invitee_id, e)
                return False

    async def get_referral_stats(self, telegram_id: int) -> Dict[str, Any]:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM referrals WHERE inviter_id = $1;",
                telegram_id,
            )
            count = int(count or 0)
            return {
                "total_referred": count,
                "bonus_quota_earned": count * 3,
                "streak_freezes_earned": count,
            }

    async def add_bonus_quota(self, telegram_id: int, amount: int) -> int:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE users SET bonus_quota = bonus_quota + $1 WHERE telegram_id = $2 RETURNING bonus_quota;",
                amount,
                telegram_id,
            )
            return row["bonus_quota"] if row else 0

    async def add_streak_freeze(self, telegram_id: int, amount: int = 1) -> int:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE users SET streak_freeze_count = streak_freeze_count + $1 WHERE telegram_id = $2 RETURNING streak_freeze_count;",
                amount,
                telegram_id,
            )
            return row["streak_freeze_count"] if row else 0

    async def add_xp(self, telegram_id: int, amount: int) -> int:
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE users SET total_xp = total_xp + $1 WHERE telegram_id = $2 RETURNING total_xp;",
                amount,
                telegram_id,
            )
            return row["total_xp"] if row else 0

