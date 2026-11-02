import pytest
import os
from pathlib import Path
from src.services.video_engine import VideoEngine, VideoSceneInput
from src.services.voice_service import WordTimestamp
from src.services.image_service import ImageService

@pytest.mark.asyncio
async def test_end_to_end_render(tmp_path):
    output_mp4 = tmp_path / "test_short.mp4"
    image_service = ImageService()
    engine = VideoEngine(width=720, height=1280, fps=24)  # 720p for fast test execution

    # Create 2 dummy scenes
    scene_inputs = []
    for i in range(1, 3):
        img_path = tmp_path / f"scene_{i}.jpg"
        image_service._generate_fallback_canvas(
            scene_number=i,
            keywords=["cosmos", "stars"],
            target_path=img_path,
            width=720,
            height=1280
        )
        
        # Dummy audio file (silent mp3/wav or empty)
        audio_path = tmp_path / f"scene_{i}.mp3"
        # Create minimal valid mp3/wav or test with dummy words
        audio_path.touch()

        words = [
            WordTimestamp(word="Did", start=0.0, end=0.4),
            WordTimestamp(word="you", start=0.4, end=0.8),
            WordTimestamp(word="know?", start=0.8, end=1.5),
        ]
        scene_inputs.append(
            VideoSceneInput(
                scene_number=i,
                image_path=str(img_path),
                audio_path=str(audio_path),
                duration=2.0,
                words=words
            )
        )

    rendered_path = await engine.render_video(
        scenes=scene_inputs,
        output_path=output_mp4,
        bgm_path=None
    )

    assert rendered_path.exists()
    assert rendered_path.stat().st_size > 10000
