"""Handlers package."""
from aiogram import Dispatcher
from src.bot.handlers.common import router as common_router
from src.bot.handlers.voice import router as voice_router
from src.bot.handlers.ielts_mock import router as ielts_router
from src.bot.handlers.reminder import router as reminder_router
from src.bot.handlers.phonemes import router as phonemes_router
from src.bot.handlers.tenses import router as tenses_router
from src.bot.handlers.monetization import router as monetization_router


def register_handlers(dp: Dispatcher) -> None:
    """Register presentation routers to the dispatcher."""
    dp.include_router(common_router)
    dp.include_router(ielts_router)
    dp.include_router(reminder_router)
    dp.include_router(phonemes_router)
    dp.include_router(tenses_router)
    dp.include_router(monetization_router)
    dp.include_router(voice_router)



__all__ = ["register_handlers"]
