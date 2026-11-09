import pytest
from src.config import Settings

def test_config_defaults():
    s = Settings(
        BOT_TOKEN="test_token",
        GEMINI_API_KEY="test_gemini",
        TARGET_CHAT_ID=12345
    )
    assert s.BOT_TOKEN == "test_token"
    assert s.GEMINI_API_KEY == "test_gemini"
    assert s.VIDEO_WIDTH == 720
    assert s.VIDEO_HEIGHT == 1280
    assert s.FPS == 24
    assert s.DAILY_SCHEDULE_TIME == "13:00,16:00,19:00,21:30,23:30"
    assert s.daily_schedule_times == ["13:00", "16:00", "19:00", "21:30", "23:30"]
    assert s.MAX_DAILY_AUTO_VIDEOS == 5
    assert s.ENABLE_DAILY_SCHEDULER is True
    assert s.abs_temp_dir.exists()
    assert s.abs_output_dir.exists()
