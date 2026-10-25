import logging
from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from src.services.user_service import UserService

logger = logging.getLogger(__name__)


class UserTrackerMiddleware(BaseMiddleware):
    """Intercept updates and ensure user is registered in SQLite."""

    def __init__(self, user_service: UserService):
        super().__init__()
        self.user_service = user_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: Optional[User] = data.get("event_from_user")
        if user:
            try:
                await self.user_service.ensure_user(
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                )
            except Exception as err:
                logger.warning("Failed to track user in Speaking Coach: %s", err)

        return await handler(event, data)
