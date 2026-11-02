import aiosqlite
from typing import Optional, Dict, Any, List
from src.config import settings

class VideoRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.abs_db_path)

    async def upsert_user(self, user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_active_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_active_at = CURRENT_TIMESTAMP
                """,
                (user_id, username, first_name)
            )
            await db.commit()

    async def save_video(
        self,
        user_id: Optional[int],
        topic: str,
        title: str,
        description: str,
        tags: str,
        duration: float,
        video_path: str,
        youtube_id: Optional[str] = None
    ) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO videos (user_id, topic, title, description, tags, duration, video_path, youtube_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, topic, title, description, tags, duration, video_path, youtube_id)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_video_by_id(self, video_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM videos WHERE id = ?", (video_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_recent_videos(self, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM videos ORDER BY created_at DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def update_youtube_id(self, video_id: int, youtube_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE videos SET youtube_id = ? WHERE id = ?", (youtube_id, video_id)
            )
            await db.commit()

    async def log_generation(
        self, trigger_type: str, topic: str, status: str, error_message: Optional[str] = None
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO generation_logs (trigger_type, topic, status, error_message)
                VALUES (?, ?, ?, ?)
                """,
                (trigger_type, topic, status, error_message)
            )
            await db.commit()

    async def get_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as c1:
                total_users = (await c1.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM videos") as c2:
                total_videos = (await c2.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM videos WHERE youtube_id IS NOT NULL") as c3:
                total_uploaded = (await c3.fetchone())[0]
            return {
                "total_users": total_users,
                "total_videos": total_videos,
                "total_uploaded": total_uploaded
            }
