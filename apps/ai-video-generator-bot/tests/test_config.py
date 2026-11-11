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
    assert s.LONGFORM_WIDTH == 1280
    assert s.LONGFORM_HEIGHT == 720
    assert s.FPS == 24
    assert s.DAILY_SCHEDULE_TIME == "08:00,10:30,13:00,15:30,18:00"
    assert s.LONGFORM_SCHEDULE_TIME == "20:00"
    assert s.daily_schedule_times == ["08:00", "10:30", "13:00", "15:30", "18:00"]
    assert s.MAX_DAILY_AUTO_VIDEOS == 5
    assert s.ENABLE_DAILY_SCHEDULER is True
    assert s.abs_temp_dir.exists()
    assert s.abs_output_dir.exists()
