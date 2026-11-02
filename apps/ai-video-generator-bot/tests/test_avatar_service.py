import pytest
from pathlib import Path
from src.services.avatar_service import avatar_service, VALID_EMOTIONS

def test_emotion_normalization():
    assert avatar_service.normalize_emotion("happiness") == "happiness"
    assert avatar_service.normalize_emotion("joy") == "happiness"
    assert avatar_service.normalize_emotion("cheerful") == "happiness"
    assert avatar_service.normalize_emotion("mystery") == "concentration"
    assert avatar_service.normalize_emotion("shock") == "surprise"
    assert avatar_service.normalize_emotion("unknown_xyz") == "happiness"

def test_all_17_sprites_exist():
    for emotion in VALID_EMOTIONS:
        sprite = avatar_service.get_sprite_path(emotion)
        assert sprite is not None, f"Sprite for emotion '{emotion}' was not found!"
        assert sprite.exists(), f"File {sprite} does not exist!"

def test_animated_avatar_clip_creation():
    clip = avatar_service.create_animated_avatar_clip(
        emotion="surprise",
        duration=3.0,
        target_height=350,
        video_width=720,
        video_height=1280
    )
    assert clip is not None
    assert clip.duration == 3.0
    # Test position at t=0 and t=1.0
    pos_0 = clip.pos(0)
    pos_1 = clip.pos(1.0)
    assert isinstance(pos_0, tuple)
    assert len(pos_0) == 2
    assert pos_0[0] > 0  # Placed on right side
    assert pos_0[1] > 0  # Placed on bottom side
    clip.close()
