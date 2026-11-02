import os
import math
import logging
from pathlib import Path
from typing import Optional, Dict

import numpy as np
from PIL import Image

try:
    from moviepy import ImageClip
except ImportError:
    from moviepy.editor import ImageClip

logger = logging.getLogger(__name__)

# Canonical 17 emotions based on the Siesta Expression Sheet
VALID_EMOTIONS = [
    "happiness", "sadness", "anger", "fear", "surprise",
    "disgust", "contempt", "embarrassment", "pride", "confusion",
    "concentration", "disappointment", "jealousy", "relief", "anxiety",
    "boredom", "anticipation"
]

# Mapping synonyms and narrative moods to canonical emotions
EMOTION_ALIASES = {
    # Joy / Happiness
    "joy": "happiness",
    "cheerful": "happiness",
    "smile": "happiness",
    "laugh": "happiness",
    "excited": "anticipation",
    "eager": "anticipation",
    "thrilled": "anticipation",
    "hopeful": "anticipation",
    # Wonder / Surprise
    "wonder": "surprise",
    "shock": "surprise",
    "astonished": "surprise",
    "stunned": "surprise",
    "amazed": "surprise",
    "curiosity": "surprise",
    "question": "confusion",
    "puzzled": "confusion",
    "confused": "confusion",
    # Thoughtful / Focus
    "thinking": "concentration",
    "focused": "concentration",
    "analyzing": "concentration",
    "serious": "concentration",
    "mystery": "concentration",
    "detective": "concentration",
    # Pride / Smug
    "smug": "pride",
    "confident": "pride",
    "proud": "pride",
    # Fear / Tension
    "terror": "fear",
    "scared": "fear",
    "panic": "fear",
    "creepy": "fear",
    "spooky": "fear",
    "tense": "anxiety",
    "nervous": "anxiety",
    "worried": "anxiety",
    # Sad / Gloomy
    "sad": "sadness",
    "crying": "sadness",
    "grief": "sadness",
    "depressed": "disappointment",
    "sigh": "relief",
    "calm": "relief",
    "peaceful": "relief",
    # Annoyed / Anger
    "furious": "anger",
    "annoyed": "anger",
    "irritated": "anger",
    "envy": "jealousy",
    "shy": "embarrassment",
    "blush": "embarrassment",
    "guilt": "embarrassment",
    "tired": "boredom",
    "sleepy": "boredom"
}

class AvatarService:
    def __init__(self, character_dir: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.character_dir = character_dir or (base_dir / "assets" / "characters" / "siesta")
        self.character_dir.mkdir(parents=True, exist_ok=True)

    def normalize_emotion(self, raw_emotion: Optional[str]) -> str:
        """Resolves raw emotion string to one of the 17 canonical sprite emotions."""
        if not raw_emotion:
            return "anticipation"
        
        clean = raw_emotion.strip().lower()
        if clean in VALID_EMOTIONS:
            return clean
        
        # Check alias dictionary
        for alias, canonical in EMOTION_ALIASES.items():
            if alias in clean:
                return canonical
                
        return "happiness"

    def get_sprite_path(self, emotion: str) -> Optional[Path]:
        """Returns path to the transparent PNG sprite for this emotion."""
        canonical = self.normalize_emotion(emotion)
        sprite_path = self.character_dir / f"{canonical}.png"
        if sprite_path.exists():
            return sprite_path
            
        # Fallback to happiness or any available sprite in the directory
        fallback_path = self.character_dir / "happiness.png"
        if fallback_path.exists():
            return fallback_path
            
        pngs = list(self.character_dir.glob("*.png"))
        if pngs:
            return pngs[0]
            
        return None

    def create_animated_avatar_clip(
        self,
        emotion: str,
        duration: float,
        target_height: int = 380,
        video_width: int = 720,
        video_height: int = 1280,
        margin_x: int = 16,
        margin_y: int = 18
    ) -> Optional[ImageClip]:
        """
        Creates an animated floating/bobbing avatar clip positioned at bottom-right.
        Applies subtle breathing sine motion: y(t) = base_y + 4 * sin(2 * pi * 0.8 * t)
        """
        sprite_path = self.get_sprite_path(emotion)
        if not sprite_path:
            logger.warning(f"No avatar sprite found for emotion '{emotion}'.")
            return None

        # Load image via PIL to compute dimensions and aspect ratio
        with Image.open(sprite_path) as pil_img:
            orig_w, orig_h = pil_img.size
            scale = target_height / orig_h
            sprite_w = int(orig_w * scale)
            sprite_h = target_height

        # Calculate base bottom-right position
        base_x = video_width - sprite_w - margin_x
        base_y = video_height - sprite_h - margin_y

        # Define dynamic position function with subtle bobbing
        def pos_func(t):
            # Breathing / bobbing vertical oscillation (4 pixels amplitude, ~0.8 Hz)
            bob_offset = int(4.0 * math.sin(2.0 * math.pi * 0.8 * t))
            return (base_x, base_y + bob_offset)

        try:
            # Create MoviePy ImageClip with duration and transparency
            clip = (
                ImageClip(str(sprite_path))
                .resized(height=target_height)
                .with_duration(duration)
                .with_position(pos_func)
            )
            return clip
        except Exception as e:
            logger.error(f"Failed to create avatar clip for {emotion}: {e}")
            return None

avatar_service = AvatarService()
