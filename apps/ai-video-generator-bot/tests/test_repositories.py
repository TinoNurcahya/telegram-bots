import pytest
import os
import aiosqlite
from src.repositories.database import init_db, CREATE_TABLES_SQL
from src.repositories.video_repo import VideoRepository

@pytest.mark.asyncio
async def test_video_repository(tmp_path):
    test_db = tmp_path / "test.db"
    
    # Initialize DB schema
    async with aiosqlite.connect(test_db) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()

    repo = VideoRepository(db_path=str(test_db))

    # Test user upsert
    await repo.upsert_user(12345, "john_doe", "John")
    await repo.upsert_user(12345, "john_doe_updated", "Johnny")

    # Test save video
    vid_id = await repo.save_video(
        user_id=12345,
        topic="Secrets of Black Holes",
        title="Mind-Blowing Space Secrets 🚀 #Shorts",
        description="Deep space facts you never knew.",
        tags="#shorts #space",
        duration=48.5,
        video_path="/path/to/video.mp4"
    )
    assert vid_id > 0

    # Test get video by id
    record = await repo.get_video_by_id(vid_id)
    assert record is not None
    assert record["title"] == "Mind-Blowing Space Secrets 🚀 #Shorts"
    assert record["duration"] == 48.5

    # Test update youtube id
    await repo.update_youtube_id(vid_id, "dQw4w9WgXcQ")
    updated = await repo.get_video_by_id(vid_id)
    assert updated["youtube_id"] == "dQw4w9WgXcQ"

    # Test stats
    stats = await repo.get_stats()
    assert stats["total_users"] == 1
    assert stats["total_videos"] == 1
    assert stats["total_uploaded"] == 1
