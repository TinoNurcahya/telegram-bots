from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from src.repositories.video_repo import VideoRepository

class UserTrackingMiddleware(BaseMiddleware):
    def __init__(self, repo: VideoRepository):
        super().__init__()
        self.repo = repo

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user:
            try:
                await self.repo.upsert_user(
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name
                )
            except Exception:
                pass

        return await handler(event, data)
