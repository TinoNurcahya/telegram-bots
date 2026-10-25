import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta

from src.repositories.coach_repository import ICoachRepository

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)

SCENARIO_OPENINGS: Dict[str, str] = {
    "Free Conversation": (
        "Hi there! I'm your AI speaking coach. What's on your mind today? "
        "Feel free to talk about your day, hobbies, or anything you'd like to practice!"
    ),
    "Job Interview": (
        "Welcome to your interview session! Let's begin with a classic opening question: "
        "Could you please introduce yourself and share a brief overview of your background?"
    ),
    "Cafe & Dining": (
        "Hello! Welcome to our specialty cafe. What can I get started for you today, "
        "or would you like to hear today's pastry and coffee recommendations?"
    ),
    "Airport Immigration": (
        "Good day. International Border Control. Could you state the primary purpose "
        "of your visit and how long you plan to stay in the country?"
    ),
    "Tech Standup": (
        "Good morning team! Let's begin our daily agile standup. "
        "What did you wrap up yesterday, what are your plans for today, and do you have any blockers?"
    ),
}


class DialogueService:
    """Dual-layer Multi-Turn Dialogue Memory (Redis Cache + DB Fallback with 2-hour TTL)."""

    def __init__(self, repository: ICoachRepository, redis_url: str = ""):
        self.repo = repository
        self.redis_url = redis_url
        self._redis_client: Optional[Any] = None
        self._redis_available = False

    async def _get_redis(self) -> Optional[Any]:
        if not aioredis or not self.redis_url:
            return None
        if self._redis_client is None:
            try:
                self._redis_client = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis_client.ping()
                self._redis_available = True
                logger.info("Connected to Redis for Multi-Turn Dialogue Cache: %s", self.redis_url)
            except Exception as err:
                logger.warning("Redis dialogue cache unavailable (%s). Falling back to SQLite/Postgres.", err)
                self._redis_client = None
                self._redis_available = False
        return self._redis_client

    def _cache_key(self, telegram_id: int, scenario: str) -> str:
        # Sanitize scenario name for key
        safe_scen = scenario.lower().replace(" ", "_").replace("&", "and")
        return f"dialogue:{telegram_id}:{safe_scen}"

    async def get_history(
        self, telegram_id: int, scenario: str, max_turns: int = 10
    ) -> List[Dict[str, str]]:
        """Fetch recent dialogue turns (up to max_turns pairs / 20 messages)."""
        limit = max_turns * 2
        redis = await self._get_redis()

        if redis and self._redis_available:
            try:
                key = self._cache_key(telegram_id, scenario)
                raw_items = await redis.lrange(key, 0, -1)
                if raw_items:
                    history = [json.loads(item) for item in raw_items]
                    return history[-limit:]
            except Exception as err:
                logger.warning("Error reading dialogue history from Redis: %s", err)

        # Fallback to persistent repository (records created within last 2 hours)
        return await self.repo.get_dialogue_history(
            telegram_id=telegram_id,
            scenario=scenario,
            limit=limit,
            max_age_hours=2,
        )

    async def add_turn(
        self, telegram_id: int, scenario: str, user_text: str, ai_text: str
    ) -> None:
        """Record a completed conversation turn (User + AI reply) with 2-hour TTL."""
        # 1. Persist to DB
        await self.repo.add_dialogue_turn(telegram_id, scenario, "user", user_text)
        await self.repo.add_dialogue_turn(telegram_id, scenario, "ai", ai_text)

        # 2. Update Redis Cache if available
        redis = await self._get_redis()
        if redis and self._redis_available:
            try:
                key = self._cache_key(telegram_id, scenario)
                user_item = json.dumps({"role": "user", "content": user_text})
                ai_item = json.dumps({"role": "ai", "content": ai_text})

                await redis.rpush(key, user_item, ai_item)
                # Keep up to 20 messages (10 pairs)
                await redis.ltrim(key, -20, -1)
                # 2-hour TTL (7200 seconds)
                await redis.expire(key, 7200)
            except Exception as err:
                logger.warning("Error caching dialogue turn in Redis: %s", err)

    async def clear_history(self, telegram_id: int, scenario: Optional[str] = None) -> None:
        """Clear active dialogue memory (triggered by /reset, scenario switch, or timeout)."""
        # 1. Clear DB
        await self.repo.clear_dialogue_history(telegram_id, scenario)

        # 2. Clear Redis
        redis = await self._get_redis()
        if redis and self._redis_available:
            try:
                if scenario:
                    key = self._cache_key(telegram_id, scenario)
                    await redis.delete(key)
                else:
                    keys = await redis.keys(f"dialogue:{telegram_id}:*")
                    if keys:
                        await redis.delete(*keys)
            except Exception as err:
                logger.warning("Error clearing Redis dialogue history: %s", err)

    def get_scenario_opening(self, scenario: str) -> str:
        """Get contextual opening icebreaker for a scenario."""
        return SCENARIO_OPENINGS.get(scenario, SCENARIO_OPENINGS["Free Conversation"])
