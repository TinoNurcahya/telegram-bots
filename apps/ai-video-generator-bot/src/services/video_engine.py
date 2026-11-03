import os
import math
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import (
        ImageClip,
        AudioFileClip,
        CompositeVideoClip,
        concatenate_videoclips,
        CompositeAudioClip,
    )
except ImportError:
    try:
        from moviepy.editor import (
            ImageClip,
            AudioFileClip,
            CompositeVideoClip,
            concatenate_videoclips,
            CompositeAudioClip,
        )
    except ImportError:
        ImageClip = None
        AudioFileClip = None
        CompositeVideoClip = None
        concatenate_videoclips = None
        CompositeAudioClip = None

from src.services.voice_service import WordTimestamp, AudioSceneResult
from src.config import settings

logger = logging.getLogger(__name__)

class VideoSceneInput:
    def __init__(
        self,
        scene_number: int,
        image_path: str,
        audio_path: str,
        duration: float,
        words: List[WordTimestamp],
        character_emotion: Optional[str] = "happiness"
    ):
        self.scene_number = scene_number
        self.image_path = image_path
        self.audio_path = audio_path
        self.duration = duration
        self.words = words
        self.character_emotion = character_emotion

class VideoEngine:
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30
    ):
        self.width = width
        self.height = height
        self.fps = fps

    def render_caption_frame(
        self,
        active_chunk: List[WordTimestamp],
        current_word_idx: int,
        width: int,
        height: int,
        center_x: Optional[int] = None,
        max_w_ratio: float = 0.84
    ) -> np.ndarray:
        """
        Draws an ultra-crisp kinetic subtitle card using Pillow with word-level highlight.
        Returns a transparent RGBA numpy array suitable for MoviePy.
        """
        # RGBA canvas for transparent overlay
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Build words with spaces
        word_items = []
        for i, wt in enumerate(active_chunk):
            word_str = wt.word.upper()
            is_active = (i == current_word_idx)
            word_items.append((word_str, is_active))

        line_str = " ".join([w[0] for w in word_items])

        # Dynamic auto-scaling font to guarantee text fits within safe horizontal bounds
        max_allowed_w = int(width * max_w_ratio)
        padding_x = 30
        padding_y = 16

        possible_fonts = [
            settings.abs_assets_dir / "fonts" / "Montserrat-Black.ttf",
            settings.abs_assets_dir / "fonts" / "Arial-Bold.ttf",
            settings.abs_assets_dir / "fonts" / "Impact.ttf",
            settings.abs_assets_dir / "fonts" / "Poppins-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "arialbd.ttf",
            "impact.ttf",
            "arial.ttf",
            "Arial",
        ]

        font_size = 60
        font = None
        while font_size >= 36:
            for pf in possible_fonts:
                try:
                    font = ImageFont.truetype(str(pf), font_size)
                    break
                except Exception:
                    continue
            if not font:
                try:
                    font = ImageFont.load_default(size=font_size)
                except TypeError:
                    font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), line_str, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            if (text_w + padding_x * 2) <= max_allowed_w or font_size <= 36:
                break
            font_size -= 2

        # Subtitle positioning: Y ~ 65% height (Safe Zone above YouTube Shorts UI & Siesta avatar)
        target_center_x = (width // 2) if (center_x is None) else center_x
        center_y = int(height * 0.65)
        start_x = target_center_x - (text_w // 2)

        # Clamp horizontal boundaries so pill box never touches screen edges
        if start_x - padding_x < 16:
            start_x = 16 + padding_x
        if start_x + text_w + padding_x > width - 16:
            start_x = width - 16 - padding_x - text_w

        # Draw dark rounded background pill behind the subtitle card
        pill_box = [
            start_x - padding_x,
            center_y - padding_y,
            start_x + text_w + padding_x,
            center_y + text_h + padding_y
        ]
        draw.rounded_rectangle(pill_box, radius=22, fill=(15, 23, 42, 220))

        # Render each word
        curr_x = start_x
        space_bbox = draw.textbbox((0, 0), " ", font=font)
        space_w = space_bbox[2] - space_bbox[0]

        for word_str, is_active in word_items:
            wb = draw.textbbox((0, 0), word_str, font=font)
            w_width = wb[2] - wb[0]

            # Active word = Bright Yellow (#FACC15), Inactive = Pure White
            text_color = (250, 204, 21, 255) if is_active else (255, 255, 255, 255)
            stroke_color = (0, 0, 0, 255)

            # Draw word with crisp outline for readability
            draw.text(
                (curr_x, center_y),
                word_str,
                font=font,
                fill=text_color,
                stroke_width=4,
                stroke_fill=stroke_color
            )
            curr_x += w_width + space_w

        return np.array(img)

    def _group_words_into_chunks(
        self, words: List[WordTimestamp], chunk_size: int = 3
    ) -> List[List[WordTimestamp]]:
        """Groups words into 2-3 words per chunk for fast, readable kinetic subtitles."""
        if not words:
            return []
        chunks = []
        i = 0
        n = len(words)
        while i < n:
            remaining = n - i
            if remaining == 4:
                take = 2
            elif remaining >= 3:
                take = min(chunk_size, 3)
            else:
                take = remaining
            chunks.append(words[i : i + take])
            i += take
        return chunks

    def create_scene_clip(
        self,
        scene: VideoSceneInput,
        intro_thumbnail_path: Optional[Path] = None,
        intro_duration: float = 0.85
    ) -> CompositeVideoClip:
        """
        Creates a single composite scene with Ken Burns pan/zoom and kinetic captions.
        If intro_thumbnail_path is provided on Scene 1, bakes the thumbnail image
        into the opening 0.85s as a high-CTR hook and YouTube Shorts thumbnail.
        """
        if not ImageClip:
            raise RuntimeError("MoviePy is not installed.")

        # 1. Determine exact scene duration from audio file as ground truth
        audio_clip = None
        if os.path.exists(scene.audio_path) and os.path.getsize(scene.audio_path) > 100:
            try:
                audio_clip = AudioFileClip(scene.audio_path)
                scene_duration = float(audio_clip.duration)
            except Exception as ae:
                logger.warning(f"Could not load audio clip {scene.audio_path}: {ae}")
                scene_duration = max(float(scene.duration), 1.0)
        else:
            scene_duration = max(float(scene.duration), 1.0)

        # 2. Base Image Clip with exact matched duration
        img_path = scene.image_path
        with Image.open(img_path) as pil_img:
            pil_img = pil_img.convert("RGB")
            if pil_img.size != (self.width, self.height):
                pil_img = pil_img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                pil_img.save(img_path)

        base_clip = ImageClip(img_path).with_duration(scene_duration)

        # 3. Fast Ken Burns Effect (Zoom slowly in or out)
        zoom_direction = 1 if (scene.scene_number % 2 == 1) else -1
        
        # Pre-scale image ONCE to 1.08x to avoid resizing every single frame
        scaled_w = int(self.width * 1.08)
        scaled_h = int(self.height * 1.08)
        with Image.open(img_path) as pil_img:
            prescaled_img = pil_img.convert("RGB").resize((scaled_w, scaled_h), Image.Resampling.BILINEAR)
            prescaled_np = np.array(prescaled_img)

        diff_w = scaled_w - self.width
        diff_h = scaled_h - self.height

        def zoom_transform(get_frame, t):
            progress = min(1.0, max(0.0, t / max(scene_duration, 0.1)))
            if zoom_direction == 1:
                cur_x = int(diff_w * progress) // 2
                cur_y = int(diff_h * progress) // 2
            else:
                cur_x = int(diff_w * (1.0 - progress)) // 2
                cur_y = int(diff_h * (1.0 - progress)) // 2

            # Pure zero-copy numpy slice (lightning fast: <1ms)
            return prescaled_np[cur_y : cur_y + self.height, cur_x : cur_x + self.width]

        try:
            base_clip = base_clip.transform(zoom_transform)
        except Exception as e:
            logger.warning(f"Could not apply zoom transform, using static clip: {e}")

        # 4. Animated Avatar Host & Kinetic Subtitle Overlays
        has_avatar = bool(getattr(scene, "character_emotion", None))
        # At 65% vertical height, subtitles sit safely in horizontal center above avatar
        sub_center_x = self.width // 2
        sub_max_w_ratio = 0.82

        layers = [base_clip]

        # Add Animated Avatar Host (Floating in Bottom-Right Corner)
        if has_avatar:
            try:
                from src.services.avatar_service import avatar_service
                avatar_clip = avatar_service.create_animated_avatar_clip(
                    emotion=scene.character_emotion,
                    duration=scene_duration,
                    target_height=int(self.height * 0.28),
                    video_width=self.width,
                    video_height=self.height
                )
                if avatar_clip:
                    layers.append(avatar_clip)
            except Exception as e:
                logger.warning(f"Could not add animated avatar clip: {e}")

        # Kinetic Subtitle Overlays (Rendered on top of base and avatar for maximum clarity)
        word_chunks = self._group_words_into_chunks(scene.words, chunk_size=3)

        for chunk in word_chunks:
            for word_idx, active_word in enumerate(chunk):
                w_start = max(0.0, float(active_word.start))
                w_end = min(scene_duration, float(active_word.end))
                if w_end <= w_start:
                    continue
                w_duration = max(0.15, w_end - w_start)

                caption_frame = self.render_caption_frame(
                    active_chunk=chunk,
                    current_word_idx=word_idx,
                    width=self.width,
                    height=self.height,
                    center_x=sub_center_x,
                    max_w_ratio=sub_max_w_ratio
                )

                cap_clip = (
                    ImageClip(caption_frame)
                    .with_start(w_start)
                    .with_duration(w_duration)
                )
                layers.append(cap_clip)

        # 5. High-CTR Thumbnail Hook (Bakes thumbnail into Frame 0 for YouTube Shorts)
        if intro_thumbnail_path and os.path.exists(intro_thumbnail_path) and scene.scene_number == 1:
            try:
                actual_intro_dur = min(intro_duration, scene_duration * 0.35)
                intro_clip = (
                    ImageClip(str(intro_thumbnail_path))
                    .with_start(0.0)
                    .with_duration(actual_intro_dur)
                )
                layers.append(intro_clip)
                logger.info(f"Attached opening thumbnail hook to Scene 1 (duration={actual_intro_dur:.2f}s)")
            except Exception as ie:
                logger.warning(f"Could not attach opening thumbnail hook: {ie}")

        # 6. Composite layers and attach audio
        scene_clip = CompositeVideoClip(layers, size=(self.width, self.height)).with_duration(scene_duration)
        if audio_clip:
            scene_clip = scene_clip.with_audio(audio_clip)

        return scene_clip

    async def render_video(
        self,
        scenes: List[VideoSceneInput],
        output_path: Path,
        bgm_path: Optional[Path] = None,
        intro_thumbnail_path: Optional[Path] = None
    ) -> Path:
        """
        Assembles all scenes sequentially, bakes opening thumbnail into Frame 0,
        adds BGM with ducking, and exports final .mp4 in a non-blocking background thread.
        """
        import asyncio
        if not concatenate_videoclips:
            raise RuntimeError("MoviePy is not available.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Assembling {len(scenes)} scenes into final video...")

        clips = []
        final_clip = None
        bgm_clip = None

        try:
            for s in scenes:
                is_first = (s == scenes[0]) or (getattr(s, "scene_number", 1) == 1)
                thumb_to_pass = intro_thumbnail_path if is_first else None
                scene_clip = self.create_scene_clip(s, intro_thumbnail_path=thumb_to_pass)
                clips.append(scene_clip)

            final_clip = concatenate_videoclips(clips, method="compose")
            total_duration = final_clip.duration

            # Mix Background Music (BGM) if available
            if bgm_path and bgm_path.exists() and os.path.getsize(bgm_path) > 1000:
                try:
                    bgm_clip = AudioFileClip(str(bgm_path))
                    if bgm_clip.duration < total_duration:
                        from moviepy.audio.fx import AudioLoop
                        bgm_clip = AudioLoop(duration=total_duration).apply(bgm_clip)
                    else:
                        bgm_clip = bgm_clip.with_duration(total_duration)

                    bgm_clip = bgm_clip.with_volume_scaled(0.12)
                    if final_clip.audio:
                        mixed_audio = CompositeAudioClip([final_clip.audio, bgm_clip])
                        final_clip = final_clip.with_audio(mixed_audio)
                    else:
                        final_clip = final_clip.with_audio(bgm_clip)
                except Exception as e:
                    logger.warning(f"Failed to mix BGM, proceeding with voiceover only: {e}")

            # Apply smooth audio fadeout to prevent any sudden pops at the end of the video
            if final_clip.audio:
                try:
                    from moviepy.audio.fx import AudioFadeOut
                    final_clip = final_clip.with_audio(final_clip.audio.with_effects([AudioFadeOut(0.3)]))
                except Exception as e:
                    logger.warning(f"Failed to apply AudioFadeOut: {e}")

            logger.info(f"Writing video file to {output_path} (fps={self.fps}, duration={total_duration:.1f}s)...")

            # Run CPU-bound encoding in non-blocking thread
            def _write_file():
                final_clip.write_videofile(
                    str(output_path),
                    fps=self.fps,
                    codec="libx264",
                    audio_codec="aac",
                    preset="ultrafast",
                    threads=4,
                    logger=None
                )

            await asyncio.to_thread(_write_file)

            logger.info(f"Video rendering successfully completed: {output_path}")
            return output_path
        finally:
            if final_clip:
                try:
                    final_clip.close()
                except Exception:
                    pass
            if bgm_clip:
                try:
                    bgm_clip.close()
                except Exception:
                    pass
            for c in clips:
                try:
                    c.close()
                except Exception:
                    pass
