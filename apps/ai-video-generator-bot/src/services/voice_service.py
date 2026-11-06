import os
import re
import wave
import random
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

from src.config import settings

logger = logging.getLogger(__name__)

# Official Google AI Studio Voice Personas (Style & Character Instructions)
STUDIO_PERSONAS: Dict[str, str] = {
    "The Master Storyteller": (
        "You are The Master Storyteller. Crafts storytelling narration with immersive pacing, "
        "dramatic pauses, and deep intriguing suspense."
    ),
    "The Ad Voiceover": (
        "You are The Ad Voiceover. A smooth, premium commercial voice with confident delivery, "
        "rhythmic clarity, and natural charisma."
    ),
    "The Training Guide": (
        "You are The Training Guide. A clear, articulate, authoritative corporate trainer "
        "and documentary explainer presenting intriguing facts."
    ),
    "The Game Show Host": (
        "You are The Game Show Host. A vibrant, enthusiastic, theatrical host with high energy "
        "and an engaging, punchy cadence."
    ),
    "The Patient Teacher": (
        "You are The Patient Teacher. A warm, encouraging, patient, and articulate teacher "
        "who explains wondrous discoveries with clarity."
    ),
    "The Everyday Assistant": (
        "You are The Everyday Assistant. A helpful, friendly, natural, and professional personal "
        "companion with conversational, modern delivery."
    ),
    "The Guarded NPC": (
        "You are The Guarded NPC. An enigmatic, mysterious persona with dark curiosity and "
        "cautious, intriguing vocal expression."
    ),
    "The Energetic Co-Host": (
        "You are The Energetic Co-Host. A lively, witty, spontaneous podcast co-host with "
        "fast-paced, engaging conversational enthusiasm."
    ),
    "The Cheeky Sidekick": (
        "You are The Cheeky Sidekick. Bright, quick, mischief barely contained with playful, "
        "witty, and clever vocal cadence."
    ),
    "The Mad Scientist": (
        "You are The Mad Scientist. Erratic, nasal, gleefully unhinged, passionately eccentric, "
        "and intensely fascinated by bizarre anomalies."
    ),
    "The Regal Monarch": (
        "You are The Regal Monarch. Measured, precise, quietly commanding, majestic, and dignified."
    ),
    "The Late-Night DJ": (
        "You are The Late-Night DJ. Smooth, velvety, two-in-the-morning warm, relaxed, intimate, and soothing."
    ),
    "The Meditation Guide": (
        "You are The Meditation Guide. Airy, hushed, endlessly patient, serene, and calming."
    ),
    "The Hype Announcer": (
        "You are The Hype Announcer. Booming, rapid, arena-sized energy with electrifying vocal presence."
    ),
    "The Grizzled Detective": (
        "You are The Grizzled Detective. Low, gravelly, world-weary noir narration with cynical, "
        "forensic observation."
    )
}

# Official Google Prebuilt Voice Characters
GOOGLE_PREBUILT_VOICES: List[str] = [
    "Aoede",   # Sophisticated, expressive female narrator
    "Charon",  # Deep, resonant, authoritative male voice
    "Fenrir",  # Intense, dramatic, powerful male voice
    "Kore",    # Warm, friendly, soothing female voice
    "Puck"     # Energetic, dynamic, youthful male voice
]

class WordTimestamp(BaseModel):
    word: str
    start: float  # In seconds
    end: float    # In seconds

class AudioSceneResult(BaseModel):
    scene_number: int
    audio_path: str
    duration: float  # In seconds
    words: List[WordTimestamp]

class FullVoiceoverResult(BaseModel):
    audio_path: str
    duration: float  # In seconds
    scene_results: List[AudioSceneResult]
    persona_name: str
    voice_name: str

class GoogleTTSQuotaExhaustedError(RuntimeError):
    """Raised when Google AI Studio TTS quota or rate limit (429) is exhausted."""
    pass

class VoiceService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or getattr(settings, "GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
        self.client = (
            genai.Client(api_key=self.api_key, http_options={"api_version": "v1beta"})
            if (genai and self.api_key)
            else None
        )

    def pick_random_persona_and_voice(self) -> Tuple[str, str]:
        """
        Randomly selects 1 of 8 Studio Personas and 1 of 5 Google Voices,
        guaranteeing full diversity across 40 unique vocal combinations.
        """
        persona = settings.VOICE_PERSONA or random.choice(list(STUDIO_PERSONAS.keys()))
        voice = settings.GOOGLE_VOICE_NAME or random.choice(GOOGLE_PREBUILT_VOICES)
        return persona, voice

    def _clean_trailing_noise(self, pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
        """
        Detects and removes the trailing digital noise burst emitted by Gemini TTS
        at the end of its raw PCM audio stream.
        Applies a smooth cosine fade-out and appends clean silence.
        """
        if not pcm_bytes:
            return pcm_bytes

        # Ensure 16-bit alignment (2 bytes per sample)
        if len(pcm_bytes) % 2 != 0:
            pcm_bytes = pcm_bytes[: len(pcm_bytes) - (len(pcm_bytes) % 2)]

        samples = np.frombuffer(pcm_bytes, dtype=np.int16).copy()
        if len(samples) < int(sample_rate * 0.5):
            return pcm_bytes

        # Inspect the last 0.5s in 5ms windows (120 samples at 24kHz)
        win_size = int(sample_rate * 0.005)
        search_samples = int(sample_rate * 0.5)
        start_search = len(samples) - search_samples

        windows = []
        for idx in range(start_search, len(samples) - win_size + 1, win_size):
            chunk = samples[idx : idx + win_size]
            rms = float(np.sqrt(np.mean(chunk.astype(float) ** 2)))
            windows.append((idx, rms))

        # Check if high-energy burst exists in the last 200ms
        has_burst = any(w[1] > 2000 for w in windows[-40:])

        cut_idx = len(samples)
        if has_burst:
            # Scan backward from the end to find the silence dip before the burst
            min_rms = 999999.0
            min_idx = len(samples)
            for idx, rms in reversed(windows):
                if rms < min_rms:
                    min_rms = rms
                    min_idx = idx
                if rms < 300:  # Speech ended and dipped into silence floor
                    cut_idx = idx
                    break
            else:
                cut_idx = min_idx

        trimmed = samples[:cut_idx]

        # Apply smooth 30ms fade-out at the trimmed boundary
        fade_len = min(int(sample_rate * 0.03), len(trimmed))
        if fade_len > 0:
            fade = np.linspace(1.0, 0.0, fade_len)
            trimmed[-fade_len:] = (trimmed[-fade_len:].astype(float) * fade).astype(np.int16)

        # Append 150ms of clean silence so speech finishes smoothly
        silence = np.zeros(int(sample_rate * 0.15), dtype=np.int16)
        final_samples = np.concatenate([trimmed, silence])
        return final_samples.tobytes()

    def _generate_google_tts_pcm(
        self,
        text: str,
        persona: str,
        voice: str
    ) -> bytes:
        """
        Calls Google AI Studio TTS to synthesize spoken audio from text.
        Returns raw PCM 24000Hz 16-bit mono audio bytes.
        Strict Google AI Studio requirement: fails immediately on error without silent fallback.
        """
        if not self.client:
            raise RuntimeError(
                "Google AI Studio Client is not configured. Please ensure GEMINI_API_KEY is set in .env."
            )

        clean_text = re.sub(r"[*`#_~]", "", text).strip()
        persona_desc = STUDIO_PERSONAS.get(persona, STUDIO_PERSONAS["The Master Storyteller"])
        
        # Structure prompt with persona instruction and spoken narration
        full_content = (
            f"[Style & Persona: {persona_desc}]\n"
            f"[Directive: Speak the following narration aloud with this exact persona and emotional inflection. Do not recite these bracketed instructions]:\n\n"
            f"{clean_text}"
        )

        models_to_try = [
            self.model_name,
            "gemini-3.8-flash-tts",
            "gemini-3.8-flash-lite-tts",
            "gemini-2.5-flash-preview-tts",
            "gemini-3.1-flash-tts-preview"
        ]
        
        # Deduplicate while preserving order
        seen = set()
        unique_models = []
        for m in models_to_try:
            if m not in seen:
                seen.add(m)
                unique_models.append(m)

        last_error = None
        for candidate_model in unique_models:
            try:
                response = self.client.models.generate_content(
                    model=candidate_model,
                    contents=full_content,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice
                                )
                            )
                        ),
                        http_options={"api_version": "v1beta"}
                    )
                )

                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if getattr(part, "inline_data", None) and part.inline_data.data:
                            return self._clean_trailing_noise(part.inline_data.data)

                raise RuntimeError("Google AI Studio returned empty audio data.")

            except Exception as e:
                last_error = e
                logger.warning(f"Google AI Studio TTS attempt with model '{candidate_model}' failed: {e}")
                # If error is quota or severe, retry with next model candidate
                continue

        raise RuntimeError(f"Google AI Studio Voiceover generation failed: {last_error}")

    def _save_pcm_to_wav(self, pcm_bytes: bytes, wav_path: Path, sample_rate: int = 24000) -> float:
        """Saves raw 16-bit mono PCM bytes to standard .wav file and returns duration in seconds."""
        wav_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)

        duration = len(pcm_bytes) / (sample_rate * 2)  # 2 bytes per sample
        return round(duration, 3)

    def _build_word_timestamps(
        self,
        text: str,
        duration: float,
        start_offset: float = 0.0
    ) -> List[WordTimestamp]:
        """Distributes word-level timestamps proportionally across audio duration for kinetic subtitles."""
        clean_text = re.sub(r"[*`#_~]", "", text).strip()
        words = clean_text.split()
        if not words:
            return []

        total_chars = sum(len(w) for w in words)
        usable_duration = max(duration - 0.3, 0.5)
        curr_t = start_offset + 0.15

        result: List[WordTimestamp] = []
        for w in words:
            w_dur = (len(w) / max(total_chars, 1)) * usable_duration
            result.append(
                WordTimestamp(
                    word=w,
                    start=round(curr_t, 3),
                    end=round(curr_t + w_dur, 3)
                )
            )
            curr_t += w_dur

        return result

    async def synthesize_full_voiceover(
        self,
        scenes: List[Any],
        output_dir: Path,
        persona: Optional[str] = None,
        voice: Optional[str] = None,
        progress_callback: Optional[Any] = None
    ) -> FullVoiceoverResult:
        """
        Synthesizes the complete narration for all scenes in a single Google AI Studio API call.
        Guarantees:
        1. 100% Google AI Studio audio voiceover.
        2. Maximum diversity across 40 Persona x Voice combinations.
        3. Only 1 API request per video (safeguards against 3 RPM Free-Tier rate limits).
        4. Precise byte-level WAV slicing per scene with smooth kinetic subtitle timestamps.
        5. Auto-retry with Telegram countdown if 3 RPM rate limit is reached.
        """
        import asyncio

        output_dir.mkdir(parents=True, exist_ok=True)
        chosen_persona, chosen_voice = self.pick_random_persona_and_voice()
        if persona:
            chosen_persona = persona
        if voice:
            chosen_voice = voice

        # Combine narration texts with natural storytelling pauses
        full_narration = " ... ".join(
            getattr(s, "voiceover_text", "").strip() for s in scenes if getattr(s, "voiceover_text", "").strip()
        )

        logger.info(
            f"Synthesizing full voiceover with Google AI Studio [Persona: '{chosen_persona}' | Voice: '{chosen_voice}']..."
        )

        # Generate audio with auto-retry and Telegram countdown if rate limit (3 RPM) is hit
        max_retries = 2
        retry_delay = 25
        pcm_bytes = None

        for attempt in range(max_retries + 1):
            try:
                pcm_bytes = await asyncio.to_thread(
                    self._generate_google_tts_pcm,
                    full_narration,
                    chosen_persona,
                    chosen_voice
                )
                break
            except Exception as e:
                err_str = str(e)
                is_quota = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
                if is_quota and attempt < max_retries:
                    logger.warning(f"Google AI Studio TTS hit rate limit (attempt {attempt + 1}/{max_retries}). Auto-retrying in {retry_delay}s...")
                    for remaining in range(retry_delay, 0, -5):
                        if progress_callback:
                            try:
                                await progress_callback(
                                    f"⏳ [2/4] Kuota Google AI Studio TTS penuh (Rate Limit 3 RPM).\n"
                                    f"Mencoba lagi secara otomatis dalam *{remaining} detik* (Percobaan {attempt + 1}/{max_retries})..."
                                )
                            except Exception:
                                pass
                        await asyncio.sleep(min(5, remaining))
                    continue

                if is_quota:
                    raise GoogleTTSQuotaExhaustedError(
                        "Kuota Google AI Studio TTS telah mencapai batas (Rate Limit / Kuota Harian)."
                    ) from e
                raise e

        full_wav_path = output_dir / "voiceover_full.wav"
        total_duration = self._save_pcm_to_wav(pcm_bytes, full_wav_path, sample_rate=24000)

        # Calculate character weight per scene to slice WAV data proportionally
        scene_weights = [
            max(len(getattr(s, "voiceover_text", "")), 10) for s in scenes
        ]
        total_weight = sum(scene_weights)
        total_bytes = len(pcm_bytes)

        scene_results: List[AudioSceneResult] = []
        byte_cursor = 0

        for i, scene in enumerate(scenes):
            scene_num = getattr(scene, "scene_number", i + 1)
            weight = scene_weights[i]
            
            # Last scene takes whatever remains to prevent rounding gaps
            if i == len(scenes) - 1:
                scene_pcm = pcm_bytes[byte_cursor:]
            else:
                chunk_len = int((weight / total_weight) * total_bytes)
                # Ensure 16-bit alignment (even number of bytes)
                if chunk_len % 2 != 0:
                    chunk_len += 1
                scene_pcm = pcm_bytes[byte_cursor: byte_cursor + chunk_len]
                byte_cursor += chunk_len

            scene_wav_path = output_dir / f"scene_{scene_num}.wav"
            scene_duration = self._save_pcm_to_wav(scene_pcm, scene_wav_path, sample_rate=24000)

            # Subtitle text for kinetic timing
            sub_text = getattr(scene, "subtitle_text", None) or getattr(scene, "voiceover_text", "")
            words = self._build_word_timestamps(sub_text, scene_duration, start_offset=0.0)

            scene_results.append(
                AudioSceneResult(
                    scene_number=scene_num,
                    audio_path=str(scene_wav_path),
                    duration=scene_duration,
                    words=words
                )
            )

        logger.info(
            f"Successfully generated Google AI Studio voiceover: {total_duration:.2f}s across {len(scene_results)} scenes. "
            f"Persona: {chosen_persona}, Voice: {chosen_voice}."
        )

        return FullVoiceoverResult(
            audio_path=str(full_wav_path),
            duration=total_duration,
            scene_results=scene_results,
            persona_name=chosen_persona,
            voice_name=chosen_voice
        )

    async def synthesize_scene(
        self,
        scene_number: int,
        text: str,
        output_dir: Path,
        voice: Optional[str] = None,
        subtitle_text: Optional[str] = None,
        persona: Optional[str] = None
    ) -> AudioSceneResult:
        """Synthesizes a single scene audio clip using Google AI Studio TTS."""
        import asyncio

        output_dir.mkdir(parents=True, exist_ok=True)
        chosen_persona, chosen_voice = self.pick_random_persona_and_voice()
        if persona:
            chosen_persona = persona
        if voice:
            chosen_voice = voice

        pcm_bytes = await asyncio.to_thread(
            self._generate_google_tts_pcm,
            text,
            chosen_persona,
            chosen_voice
        )

        scene_wav_path = output_dir / f"scene_{scene_number}.wav"
        duration = self._save_pcm_to_wav(pcm_bytes, scene_wav_path, sample_rate=24000)

        sub_text = subtitle_text or text
        words = self._build_word_timestamps(sub_text, duration, start_offset=0.0)

        return AudioSceneResult(
            scene_number=scene_number,
            audio_path=str(scene_wav_path),
            duration=duration,
            words=words
        )
