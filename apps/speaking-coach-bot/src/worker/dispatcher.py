import logging
from typing import Dict, Any, Optional

try:
    from aiogram import Bot
except ImportError:
    Bot = Any  # type: ignore
from src.services.user_service import UserService
from src.services.ai_coach_service import AICoachService
from src.services.tts_service import TTSService
from src.worker.arq_worker import execute_voice_job

logger = logging.getLogger(__name__)


class VoiceJobDispatcher:
    """Hybrid Dispatcher routing voice evaluation jobs to Arq Redis Queue or In-Process fallback."""

    def __init__(self, arq_pool: Optional[Any] = None):
        self.arq_pool = arq_pool

    async def dispatch(
        self,
        job_data: Dict[str, Any],
        bot: Bot,
        user_service: UserService,
        ai_coach_service: AICoachService,
        tts_service: TTSService,
        dialogue_service: Optional[Any] = None,
    ) -> None:
        """Enqueue job to Arq if Redis is active, or execute in-process as fallback."""
        user_id = job_data.get("user_id")

        if self.arq_pool is not None:
            try:
                job = await self.arq_pool.enqueue_job("process_voice_job", job_data)
                logger.info("Enqueued voice job %s to Arq Redis queue for user %s", getattr(job, "job_id", ""), user_id)
                return
            except Exception as e:
                logger.warning(
                    "Failed to enqueue to Redis Arq queue (%s). Falling back to in-process execution.",
                    e,
                )

        # Fallback: In-process direct execution
        logger.debug("Executing voice job in-process fallback for user %s", user_id)
        await execute_voice_job(
            job_data=job_data,
            bot=bot,
            user_service=user_service,
            ai_coach_service=ai_coach_service,
            tts_service=tts_service,
            dialogue_service=dialogue_service,
        )
