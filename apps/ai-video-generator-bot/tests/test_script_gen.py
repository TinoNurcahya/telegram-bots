import pytest
from src.services.script_gen import ScriptGeneratorService, VideoScript, Scene

@pytest.mark.asyncio
async def test_fallback_script():
    service = ScriptGeneratorService(api_key="")
    script = await service.generate_script("Bermuda Triangle")

    assert isinstance(script, VideoScript)
    assert "Bermuda Triangle" in script.title or "Bermuda Triangle" in script.topic
    assert len(script.scenes) >= 5
    assert all(isinstance(s, Scene) for s in script.scenes)
    assert all(s.voiceover_text for s in script.scenes)
    assert all(s.visual_prompt for s in script.scenes)

def test_random_topic():
    service = ScriptGeneratorService()
    t1 = service.get_random_trending_topic()
    assert isinstance(t1, str)
    assert len(t1) > 5
