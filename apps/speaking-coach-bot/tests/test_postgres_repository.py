import unittest
from unittest.mock import AsyncMock, MagicMock
from src.repositories.postgres_coach_repository import PostgresCoachRepository
from src.repositories import create_coach_repository, CoachRepository


class MockAsyncpgConnection:
    """Mock asyncpg connection simulating queries and responses."""

    def __init__(self):
        self.execute = AsyncMock(return_value="EXECUTE 1")
        self.fetchrow = AsyncMock(return_value=None)
        self.fetch = AsyncMock(return_value=[])
        self.fetchval = AsyncMock(return_value=0)


class MockAsyncpgPool:
    """Mock asyncpg Pool simulating acquire context manager."""

    def __init__(self, conn: MockAsyncpgConnection):
        self.conn = conn
        self.close = AsyncMock()

    def acquire(self):
        conn = self.conn
        class _AcquireContext:
            async def __aenter__(self):
                return conn
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return _AcquireContext()


class TestPostgresCoachRepository(unittest.IsolatedAsyncioTestCase):
    """Unit tests for PostgresCoachRepository utilizing mocked asyncpg pool."""

    def setUp(self):
        self.mock_conn = MockAsyncpgConnection()
        self.mock_pool = MockAsyncpgPool(self.mock_conn)
        self.repo = PostgresCoachRepository(dsn="postgresql://mock:mock@localhost/mock", pool=self.mock_pool)

    async def test_init_schema(self):
        await self.repo.init_schema()
        self.assertGreater(self.mock_conn.execute.call_count, 5)

    async def test_upsert_user(self):
        await self.repo.upsert_user(12345, username="johndoe", first_name="John")
        self.mock_conn.execute.assert_called()
        call_args = self.mock_conn.execute.call_args[0]
        self.assertIn("INSERT INTO users", call_args[0])
        self.assertEqual(call_args[1], 12345)
        self.assertEqual(call_args[2], "johndoe")

    async def test_get_user(self):
        self.mock_conn.fetchrow.return_value = {
            "telegram_id": 12345,
            "target_level": "Intermediate",
            "active_scenario": "Job Interview",
            "current_streak": 5,
            "total_xp": 120,
        }
        user = await self.repo.get_user(12345)
        self.assertIsNotNone(user)
        self.assertEqual(user["target_level"], "Intermediate")
        self.assertEqual(user["current_streak"], 5)

    async def test_set_user_level(self):
        await self.repo.set_user_level(12345, "Advanced")
        self.mock_conn.execute.assert_called()
        call_args = self.mock_conn.execute.call_args[0]
        self.assertIn("UPDATE users SET target_level", call_args[0])
        self.assertEqual(call_args[1], "Advanced")
        self.assertEqual(call_args[2], 12345)

    async def test_record_practice_session(self):
        await self.repo.record_practice_session(
            telegram_id=12345,
            duration_seconds=30,
            transcript="Hello world",
            feedback_summary="Great job",
            fluency_score=85,
            cefr_level="B2",
            ielts_band=6.5,
            scenario="Cafe",
        )
        self.assertEqual(self.mock_conn.execute.call_count, 2)

    async def test_ielts_session_flow(self):
        self.mock_conn.fetchrow.side_effect = [
            {"id": 42},  # create_ielts_session returning id
            {            # get_active_ielts_session
                "id": 42,
                "telegram_id": 12345,
                "exam_type": "express",
                "current_step": 0,
                "questions_json": '[{"text": "Q1"}]',
                "responses_json": "[]",
                "status": "in_progress",
            },
        ]

        session_id = await self.repo.create_ielts_session(12345, "express", [{"text": "Q1"}])
        self.assertEqual(session_id, 42)

        active = await self.repo.get_active_ielts_session(12345)
        self.assertIsNotNone(active)
        self.assertEqual(len(active["questions"]), 1)

    async def test_phoneme_stats(self):
        self.mock_conn.fetchrow.return_value = {
            "total_drills": 10,
            "avg_accuracy": 88.5,
            "clear_distinctions": 8,
        }
        stats = await self.repo.get_phoneme_stats(12345)
        self.assertEqual(stats["total_drills"], 10)
        self.assertEqual(stats["avg_accuracy"], 88.5)
        self.assertEqual(stats["clear_distinctions"], 8)

    async def test_factory_creation(self):
        pg_repo, _ = create_coach_repository(database_url="postgresql://user:pass@host:5432/db")
        self.assertIsInstance(pg_repo, PostgresCoachRepository)

        sqlite_repo, _ = create_coach_repository(database_url="")
        self.assertIsInstance(sqlite_repo, CoachRepository)


if __name__ == "__main__":
    unittest.main()
