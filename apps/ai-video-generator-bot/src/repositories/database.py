import aiosqlite
from pathlib import Path
from src.config import settings

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT,
    duration REAL DEFAULT 0,
    video_path TEXT,
    youtube_id TEXT,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS generation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT NOT NULL, -- 'manual' or 'scheduled'
    topic TEXT NOT NULL,
    status TEXT NOT NULL,       -- 'in_progress', 'success', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db() -> None:
    """Initialize database tables and indexes with high-concurrency WAL mode."""
    db_path = settings.abs_db_path
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode = WAL;")
        await db.execute("PRAGMA synchronous = NORMAL;")
        await db.execute("PRAGMA busy_timeout = 5000;")
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()
