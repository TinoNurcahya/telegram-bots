import io
import logging
from typing import Optional, Dict, Any

try:
    import edge_tts
except ImportError:
    edge_tts = None

logger = logging.getLogger(__name__)

AVAILABLE_VOICES: Dict[str, str] = {
    "Jenny (Female, US)": "en-US-JennyNeural",
    "Guy (Male, US)": "en-US-GuyNeural",
    "Sonia (Female, UK)": "en-GB-SoniaNeural",
    "Ryan (Male, UK)": "en-GB-RyanNeural",
}

SPEED_PRESETS: Dict[str, Dict[str, str]] = {
    "0.75x": {"rate": "-25%", "label": "🐢 0.75x (Sangat Lambat)"},
    "0.85x": {"rate": "-15%", "label": "🎧 0.85x (Santai & Jelas)"},
    "1.0x":  {"rate": "+0%",  "label": "⚡ 1.0x (Normal Standar)"},
    "1.15x": {"rate": "+15%", "label": "🚀 1.15x (Agak Cepat)"},
    "1.25x": {"rate": "+25%", "label": "🏎️ 1.25x (Cepat)"},
}


class TTSService:
    """Asynchronous Neural Text-to-Speech service using edge-tts (Zero API Key required)."""

    def __init__(self, default_voice: str = "en-US-JennyNeural", default_rate: str = "+0%"):
        self.default_voice = default_voice
        self.default_rate = default_rate

    async def generate_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
    ) -> Optional[bytes]:
        """Synthesize natural spoken audio bytes from text with customizable voice and speech rate."""
        if not edge_tts:
            logger.warning("edge-tts library is not installed. Skipping voice synthesis.")
            return None

        selected_voice = voice or self.default_voice
        selected_rate = rate or self.default_rate

        # Clean text of markdown asterisks or special characters for cleaner speech
        clean_text = text.replace("*", "").replace("`", "").replace("#", "").strip()
        if not clean_text:
            return None

        try:
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=selected_voice,
                rate=selected_rate,
            )
            buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])

            audio_data = buffer.getvalue()
            return audio_data if len(audio_data) > 0 else None
        except Exception as err:
            logger.error("Failed to generate TTS audio with edge-tts: %s", err)
            return None

    # Alias for generate_speech
    synthesize_speech = generate_speech

    async def synthesize_phoneme_contrast_audio(
        self,
        word_a: str,
        word_b: str,
        sentence: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
    ) -> Optional[bytes]:
        """Synthesize a structured minimal pair demonstration: word A, pause, word B, pause, sentence."""
        text = f"{word_a}. ... {word_b}. ... {sentence}"
        return await self.generate_speech(text=text, voice=voice, rate=rate)
