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
    service = ScriptGeneratorService(api_key="")
    t1 = service.get_random_trending_topic()
    assert isinstance(t1, str)
    assert len(t1) > 5

def test_five_daily_slots_use_distinct_categories():
    service = ScriptGeneratorService(api_key="")
    for day in [1, 10, 100, 313]:
        # Slots 0..4 (Shorts) + Slot 5 (Long-Form) = 6 distinct categories per day
        categories_for_day = [
            service.get_rotated_case_prompt(slot_index=slot, day_of_year=day)["category"]
            for slot in range(6)
        ]
        assert len(set(categories_for_day)) == 6

def test_fallback_longform_script():
    service = ScriptGeneratorService(api_key="")
    script = service._get_fallback_longform_script("Antikythera Mechanism")
    assert len(script.scenes) == 15
    assert "#shorts" not in script.title.lower()
    assert all("short" not in t.lower() for t in script.tags)
