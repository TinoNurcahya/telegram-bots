import pytest
import numpy as np
from pathlib import Path
from src.services.video_engine import VideoEngine
from src.services.voice_service import WordTimestamp
from src.services.image_service import ImageService

def test_caption_frame_rendering():
    engine = VideoEngine(width=1080, height=1920)
    words = [
        WordTimestamp(word="Did", start=0.0, end=0.3),
        WordTimestamp(word="you", start=0.3, end=0.6),
        WordTimestamp(word="know?", start=0.6, end=1.0)
    ]

    frame = engine.render_caption_frame(
        active_chunk=words,
        current_word_idx=1,
        width=1080,
        height=1920
    )

    assert isinstance(frame, np.ndarray)
    assert frame.shape == (1920, 1080, 4)

def test_fallback_canvas_generation(tmp_path):
    image_service = ImageService()
    target_file = tmp_path / "test_scene.jpg"

    image_service._generate_fallback_canvas(
        scene_number=1,
        keywords=["space", "galaxy"],
        target_path=target_file,
        width=1080,
        height=1920
    )

    assert target_file.exists()
    assert target_file.stat().st_size > 5000
