import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

try:
    import edge_tts
except ImportError:
    edge_tts = None

from src.config import settings

logger = logging.getLogger(__name__)

class WordTimestamp(BaseModel):
    word: str
    start: float  # In seconds
    end: float    # In seconds

class AudioSceneResult(BaseModel):
    scene_number: int
    audio_path: str
    duration: float  # In seconds
    words: List[WordTimestamp]

class VoiceService:
    def __init__(
        self,
        default_voice: Optional[str] = None,
        default_rate: Optional[str] = None,
        default_pitch: Optional[str] = None
    ):
        self.default_voice = default_voice or settings.VOICE_NAME
        self.default_rate = default_rate or settings.VOICE_RATE
        self.default_pitch = default_pitch or settings.VOICE_PITCH

    async def synthesize_scene(
        self,
        scene_number: int,
        text: str,
        output_dir: Path,
        voice: Optional[str] = None,
        subtitle_text: Optional[str] = None
    ) -> AudioSceneResult:
        """
        Synthesizes audio for a single scene, extracting exact word timestamps
        for kinetic subtitle synchronization. Supports Japanese narration with
        English kinetic subtitle timing.
        """
        if not edge_tts:
            raise RuntimeError("edge-tts library is not installed.")

        output_dir.mkdir(parents=True, exist_ok=True)
        audio_path = output_dir / f"scene_{scene_number}.mp3"
        
        target_voice = voice or self.default_voice
        clean_text = re.sub(r"[*`#_~]", "", text)
        # Keep ASCII printable characters as well as Japanese Unicode blocks (Hiragana, Katakana, CJK Kanji, JP punctuation)
        clean_text = re.sub(
            r"[^\x20-\x7E\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+",
            " ",
            clean_text
        )
        clean_text = re.sub(r"\s+", " ", clean_text).strip()

        communicate = edge_tts.Communicate(
            text=clean_text,
            voice=target_voice,
            rate=self.default_rate,
            pitch=self.default_pitch
        )

        raw_words: List[WordTimestamp] = []
        audio_bytes = bytearray()
        sentence_boundaries = []

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset and duration are given in 100ns units (ticks)
                offset_sec = chunk["offset"] / 10_000_000.0
                duration_sec = chunk["duration"] / 10_000_000.0
                word_text = chunk["text"]
                raw_words.append(
                    WordTimestamp(
                        word=word_text,
                        start=round(offset_sec, 3),
                        end=round(offset_sec + duration_sec, 3)
                    )
                )
            elif chunk["type"] == "SentenceBoundary":
                sentence_boundaries.append(chunk)

        with open(audio_path, "wb") as f:
            f.write(audio_bytes)

        # Determine audio duration from Edge-TTS boundaries or rough fallback
        if raw_words:
            total_duration = max(w.end for w in raw_words) + 0.3
        elif sentence_boundaries:
            last_sb = sentence_boundaries[-1]
            total_duration = (last_sb["offset"] + last_sb["duration"]) / 10_000_000.0 + 0.3
        else:
            word_count = len(clean_text)
            total_duration = max(3.0, word_count / 5.0)

        words: List[WordTimestamp] = []

        # If an English subtitle_text is provided, distribute English words proportionally
        # across the actual audio duration so kinetic subtitles highlight smoothly
        if subtitle_text and subtitle_text.strip():
            clean_sub = re.sub(r"[*`#_~]", "", subtitle_text).strip()
            sub_words = clean_sub.split()
            if sub_words:
                total_chars = sum(len(w) for w in sub_words)
                usable_duration = max(total_duration - 0.4, 1.0)
                curr_t = 0.2
                for w in sub_words:
                    w_dur = (len(w) / max(total_chars, 1)) * usable_duration
                    words.append(
                        WordTimestamp(
                            word=w,
                            start=round(curr_t, 3),
                            end=round(curr_t + w_dur, 3)
                        )
                    )
                    curr_t += w_dur
        else:
            # Fallback to raw Japanese word or sentence boundaries
            if raw_words:
                words = raw_words
            elif sentence_boundaries:
                for sb in sentence_boundaries:
                    s_start = sb["offset"] / 10_000_000.0
                    s_dur = sb["duration"] / 10_000_000.0
                    s_text = sb.get("text", "")
                    s_words = s_text.strip().split()
                    if not s_words:
                        continue
                    total_chars = sum(len(w) for w in s_words)
                    curr_t = s_start
                    for w in s_words:
                        w_dur = (len(w) / max(total_chars, 1)) * s_dur
                        words.append(
                            WordTimestamp(
                                word=w,
                                start=round(curr_t, 3),
                                end=round(curr_t + w_dur, 3)
                            )
                        )
                        curr_t += w_dur
            else:
                split_words = clean_text.split()
                if split_words:
                    w_dur = total_duration / len(split_words)
                    curr_t = 0.0
                    for w in split_words:
                        words.append(
                            WordTimestamp(
                                word=w,
                                start=round(curr_t, 3),
                                end=round(curr_t + w_dur, 3)
                            )
                        )
                        curr_t += w_dur

        logger.info(
            f"Synthesized scene {scene_number} audio: {total_duration:.2f}s with {len(words)} word timestamps."
        )

        return AudioSceneResult(
            scene_number=scene_number,
            audio_path=str(audio_path),
            duration=round(total_duration, 2),
            words=words
        )
