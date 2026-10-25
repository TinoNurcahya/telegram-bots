"""Services package."""
from src.services.ai_coach_service import (
    AICoachService,
    SpeakingFeedback,
    ShadowingFeedback,
    GrammarSlip,
)
from src.services.user_service import UserService, StreakUpdateResult
from src.services.tts_service import TTSService, AVAILABLE_VOICES, SPEED_PRESETS
from src.services.dialogue_service import DialogueService, SCENARIO_OPENINGS

__all__ = [
    "AICoachService",
    "SpeakingFeedback",
    "ShadowingFeedback",
    "GrammarSlip",
    "UserService",
    "StreakUpdateResult",
    "TTSService",
    "AVAILABLE_VOICES",
    "SPEED_PRESETS",
    "DialogueService",
    "SCENARIO_OPENINGS",
]
