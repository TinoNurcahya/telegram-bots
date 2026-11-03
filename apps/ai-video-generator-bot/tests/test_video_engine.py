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

def test_caption_size_and_position_safe_zone():
    engine = VideoEngine(width=720, height=1280)
    words = [
        WordTimestamp(word="DROP", start=0.0, end=0.4),
        WordTimestamp(word="OF", start=0.4, end=0.7),
        WordTimestamp(word="SALT", start=0.7, end=1.2)
    ]

    frame = engine.render_caption_frame(
        active_chunk=words,
        current_word_idx=2,
        width=720,
        height=1280
    )

    alpha = frame[:, :, 3]
    y_idx, x_idx = np.where(alpha > 50)
    assert len(y_idx) > 0, "No subtitle pixels rendered"

    pill_w = x_idx.max() - x_idx.min()
    pill_h = y_idx.max() - y_idx.min()
    center_y = (y_idx.max() + y_idx.min()) // 2
    center_x = (x_idx.max() + x_idx.min()) // 2

    # Viral Shorts bold subtitles should be prominent (>450px wide, >65px high on 720p)
    assert pill_w >= 450, f"Subtitle pill too narrow: {pill_w}px"
    assert pill_h >= 65, f"Subtitle pill too short: {pill_h}px"

    # Centered horizontally around 360
    assert abs(center_x - 360) <= 20, f"Subtitle not centered horizontally: X={center_x}"

    # Centered vertically in safe zone (~65% of 1280 = 832)
    assert abs(center_y - 832) <= 40, f"Subtitle not at safe zone 65%: Y={center_y}"

def test_chunk_balancing():
    engine = VideoEngine(width=720, height=1280)
    words_4 = [
        WordTimestamp(word=f"w{i}", start=float(i), end=float(i+1))
        for i in range(4)
    ]
    chunks = engine._group_words_into_chunks(words_4, chunk_size=3)
    # 4 words balanced into 2 and 2
    assert len(chunks) == 2
    assert len(chunks[0]) == 2
    assert len(chunks[1]) == 2

    words_5 = [
        WordTimestamp(word=f"w{i}", start=float(i), end=float(i+1))
        for i in range(5)
    ]
    chunks_5 = engine._group_words_into_chunks(words_5, chunk_size=3)
    # 5 words split into 3 and 2
    assert len(chunks_5) == 2
    assert len(chunks_5[0]) == 3
    assert len(chunks_5[1]) == 2

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
