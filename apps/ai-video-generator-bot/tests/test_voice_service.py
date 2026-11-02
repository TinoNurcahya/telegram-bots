import pytest
from pathlib import Path
from src.services.voice_service import (
    VoiceService,
    STUDIO_PERSONAS,
    GOOGLE_PREBUILT_VOICES,
    WordTimestamp,
    AudioSceneResult,
    FullVoiceoverResult
)

def test_personas_and_voices_roster():
    assert len(STUDIO_PERSONAS) == 15
    expected_personas = [
        "The Master Storyteller",
        "The Ad Voiceover",
        "The Training Guide",
        "The Game Show Host",
        "The Patient Teacher",
        "The Everyday Assistant",
        "The Guarded NPC",
        "The Energetic Co-Host",
        "The Cheeky Sidekick",
        "The Mad Scientist",
        "The Regal Monarch",
        "The Late-Night DJ",
        "The Meditation Guide",
        "The Hype Announcer",
        "The Grizzled Detective"
    ]
    for p in expected_personas:
        assert p in STUDIO_PERSONAS

    assert len(GOOGLE_PREBUILT_VOICES) == 5
    for v in ["Aoede", "Charon", "Fenrir", "Kore", "Puck"]:
        assert v in GOOGLE_PREBUILT_VOICES

def test_random_persona_and_voice_diversity():
    service = VoiceService(api_key="mock_key")
    picks = set()
    for _ in range(30):
        p, v = service.pick_random_persona_and_voice()
        assert p in STUDIO_PERSONAS
        assert v in GOOGLE_PREBUILT_VOICES
        picks.add((p, v))

    # Over 30 trials, it should pick multiple different combinations
    assert len(picks) > 1

def test_word_timestamp_builder():
    service = VoiceService(api_key="mock_key")
    text = "The secret chamber remains unopened beneath the sands."
    words = service._build_word_timestamps(text, duration=4.0)

    assert len(words) == len(text.split())
    assert all(isinstance(w, WordTimestamp) for w in words)
    assert words[0].start >= 0.0
    assert words[-1].end <= 4.0
    # Check monotonic order
    for i in range(len(words) - 1):
        assert words[i].start <= words[i+1].start

def test_pcm_to_wav_conversion(tmp_path):
    service = VoiceService(api_key="mock_key")
    # 1 second of 24000Hz 16-bit mono silence (48000 bytes)
    sample_rate = 24000
    pcm_bytes = b"\x00\x00" * sample_rate
    target_wav = tmp_path / "test.wav"

    dur = service._save_pcm_to_wav(pcm_bytes, target_wav, sample_rate=sample_rate)
    assert dur == 1.0
    assert target_wav.exists()
    assert target_wav.stat().st_size > 48000

def test_clean_trailing_noise():
    import numpy as np
    service = VoiceService(api_key="mock_key")
    sample_rate = 24000

    # Simulate 1.5s speech + 0.2s silence + 0.15s loud burst (e.g. 25000 amplitude)
    speech = (np.sin(np.linspace(0, 100 * np.pi, int(sample_rate * 1.5))) * 10000).astype(np.int16)
    silence = np.zeros(int(sample_rate * 0.2), dtype=np.int16)
    burst = (np.random.uniform(-30000, 30000, int(sample_rate * 0.15))).astype(np.int16)
    
    noisy_pcm = np.concatenate([speech, silence, burst]).tobytes()
    cleaned_pcm = service._clean_trailing_noise(noisy_pcm, sample_rate=sample_rate)

    cleaned_samples = np.frombuffer(cleaned_pcm, dtype=np.int16)
    # The last 100ms should be clean silence (rms ~ 0)
    last_100ms = cleaned_samples[-int(sample_rate * 0.1):]
    rms_end = np.sqrt(np.mean(last_100ms.astype(float) ** 2))
    assert rms_end < 50.0

