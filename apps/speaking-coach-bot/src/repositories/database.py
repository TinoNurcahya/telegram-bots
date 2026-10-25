import logging

try:
    import aiosqlite
except ImportError:
    aiosqlite = None

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Async SQLite Database Connection and schema initialization for Speaking Coach."""

    def __init__(self, db_path: str = "speaking_coach.db"):
        self.db_path = db_path

    async def init_schema(self) -> None:
        """Initialize database tables for users, practice sessions, vocab bank, and shadowing history."""
        if not aiosqlite:
            logger.warning("aiosqlite is not installed. Skipping schema initialization.")
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Users table with active scenario, voice, streak, and XP
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
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
                    invited_by INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # Practice sessions with CEFR and IELTS metrics
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS practice_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    duration_seconds INTEGER DEFAULT 0,
                    transcript TEXT,
                    feedback_summary TEXT,
                    fluency_score INTEGER DEFAULT 0,
                    cefr_level TEXT DEFAULT 'B1',
                    ielts_band REAL DEFAULT 6.0,
                    scenario TEXT DEFAULT 'Free Conversation',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )

            # Vocabulary bank for words/grammar to review
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS vocab_bank (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    original_phrase TEXT NOT NULL,
                    correction TEXT NOT NULL,
                    explanation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )

            # Shadowing history table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS shadowing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    target_text TEXT NOT NULL,
                    user_transcript TEXT NOT NULL,
                    match_score INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )

            # IELTS mock exam active sessions table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS ielts_mock_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    exam_type TEXT NOT NULL,
                    current_step INTEGER DEFAULT 0,
                    questions_json TEXT NOT NULL,
                    responses_json TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'in_progress',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )

            # IELTS mock exam completed scorecards table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS ielts_mock_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    exam_type TEXT NOT NULL,
                    overall_band REAL NOT NULL,
                    fluency_coherence REAL NOT NULL,
                    lexical_resource REAL NOT NULL,
                    grammar_accuracy REAL NOT NULL,
                    pronunciation REAL NOT NULL,
                    examiner_commentary TEXT,
                    target_improvements TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )

            # Mode C: Phoneme-Level Diffing and Minimal Pairs drills table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS phoneme_drills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    category_id TEXT NOT NULL,
                    pair_id TEXT NOT NULL,
                    pair_label TEXT NOT NULL,
                    target_words TEXT NOT NULL,
                    user_transcript TEXT NOT NULL,
                    accuracy_score INTEGER NOT NULL,
                    is_distinction_clear INTEGER NOT NULL,
                    detected_ipa TEXT DEFAULT '',
                    mouth_position_tip TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )

            await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON practice_sessions(telegram_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_vocab_user ON vocab_bank(telegram_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_shadow_user ON shadowing_history(telegram_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ielts_sessions_user ON ielts_mock_sessions(telegram_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_ielts_results_user ON ielts_mock_results(telegram_id);")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_phoneme_user ON phoneme_drills(telegram_id);")

            # Multi-Turn Dialogue Memory table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS dialogue_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    scenario TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_dialogue_user_scenario ON dialogue_turns(telegram_id, scenario);")

            # Referrals and viral growth table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id INTEGER NOT NULL,
                    invitee_id INTEGER NOT NULL UNIQUE,
                    reward_claimed INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inviter_id) REFERENCES users(telegram_id),
                    FOREIGN KEY (invitee_id) REFERENCES users(telegram_id)
                );
                """
            )
            # Targeted English Tenses drills table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tense_exercises (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    tense_id TEXT NOT NULL,
                    tense_title TEXT NOT NULL,
                    user_transcript TEXT NOT NULL,
                    accuracy_score INTEGER NOT NULL,
                    is_target_tense_used INTEGER NOT NULL,
                    verb_form_analysis TEXT DEFAULT '',
                    coaching_tip TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
                );
                """
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_tenses_user ON tense_exercises(telegram_id);")

            # Column migrations for existing databases
            columns_to_add = [
                ("users", "active_scenario", "TEXT DEFAULT 'Free Conversation'"),
                ("users", "tts_voice", "TEXT DEFAULT 'en-US-JennyNeural'"),
                ("users", "current_streak", "INTEGER DEFAULT 0"),
                ("users", "max_streak", "INTEGER DEFAULT 0"),
                ("users", "last_practice_date", "TEXT DEFAULT ''"),
                ("users", "total_xp", "INTEGER DEFAULT 0"),
                ("users", "active_shadow_target", "TEXT DEFAULT ''"),
                ("users", "active_phoneme_target", "TEXT DEFAULT ''"),
                ("users", "active_tense_drill", "TEXT DEFAULT ''"),
                ("users", "reminder_time", "TEXT DEFAULT '20:00'"),
                ("users", "reminder_enabled", "INTEGER DEFAULT 1"),
                ("users", "reminder_timezone", "TEXT DEFAULT 'Asia/Jakarta'"),
                ("users", "last_reminded_date", "TEXT DEFAULT ''"),
                ("users", "streak_freeze_count", "INTEGER DEFAULT 1"),
                ("users", "is_premium", "INTEGER DEFAULT 0"),
                ("users", "premium_until", "TEXT DEFAULT ''"),
                ("users", "premium_tier", "TEXT DEFAULT ''"),
                ("users", "has_used_trial", "INTEGER DEFAULT 0"),
                ("users", "daily_eval_count", "INTEGER DEFAULT 0"),
                ("users", "daily_eval_date", "TEXT DEFAULT ''"),
                ("users", "badges_json", "TEXT DEFAULT '[]'"),
                ("users", "tts_speed", "TEXT DEFAULT '+0%'"),
                ("users", "bonus_quota", "INTEGER DEFAULT 0"),
                ("users", "invited_by", "INTEGER DEFAULT 0"),
                ("practice_sessions", "cefr_level", "TEXT DEFAULT 'B1'"),
                ("practice_sessions", "ielts_band", "REAL DEFAULT 6.0"),
                ("practice_sessions", "scenario", "TEXT DEFAULT 'Free Conversation'"),
            ]

            for table, col, col_type in columns_to_add:
                try:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
                except Exception:
                    pass

            await db.commit()
            logger.info("Speaking coach schema initialized with Streaks, XP, Shadowing, IELTS & Phonemes at %s", self.db_path)

