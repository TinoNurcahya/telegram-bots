import os
import uuid
import random
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from src.config import settings
from src.services.script_gen import ScriptGeneratorService, VideoScript
from src.services.voice_service import VoiceService, AudioSceneResult
from src.services.image_service import ImageService
from src.services.video_engine import VideoEngine, VideoSceneInput
from src.services.youtube_service import YouTubeService
from src.services.thumbnail_service import ThumbnailService
from src.repositories.video_repo import VideoRepository

logger = logging.getLogger(__name__)

class FullVideoResult(BaseModel):
    video_id: int
    topic: str
    title: str
    description: str
    tags: List[str]
    duration: float
    video_path: str
    youtube_id: Optional[str] = None
    youtube_error: Optional[str] = None
    thumbnail_path: Optional[str] = None
    voice_persona: Optional[str] = None
    voice_name: Optional[str] = None

class VideoOrchestrator:
    def __init__(
        self,
        script_service: Optional[ScriptGeneratorService] = None,
        voice_service: Optional[VoiceService] = None,
        image_service: Optional[ImageService] = None,
        video_engine: Optional[VideoEngine] = None,
        youtube_service: Optional[YouTubeService] = None,
        thumbnail_service: Optional[ThumbnailService] = None,
        repo: Optional[VideoRepository] = None
    ):
        self.script_service = script_service or ScriptGeneratorService()
        self.voice_service = voice_service or VoiceService()
        self.image_service = image_service or ImageService()
        self.video_engine = video_engine or VideoEngine(
            width=settings.VIDEO_WIDTH,
            height=settings.VIDEO_HEIGHT,
            fps=settings.FPS
        )
        self.youtube_service = youtube_service or YouTubeService()
        self.thumbnail_service = thumbnail_service or ThumbnailService()
        self.repo = repo or VideoRepository()

    async def create_short_video(
        self,
        topic: Optional[str] = None,
        user_id: Optional[int] = None,
        trigger_type: str = "manual",
        auto_upload_youtube: bool = False,
        progress_callback = None
    ) -> FullVideoResult:
        """
        Executes end-to-end pipeline:
        1. Gemini Scripting -> 2. Edge-TTS -> 3. Pollinations FLUX -> 4. MoviePy Render -> 5. DB save
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job_temp_dir = settings.abs_temp_dir / job_id
        job_temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting Video Generation Job [{job_id}] for topic: {topic or 'Trending Auto'}")
        await self.repo.log_generation(trigger_type, topic or "Auto", "in_progress")

        try:
            # 1. Gather recent topics from DB to prevent duplicates and generate Structured Script with Gemini
            excluded_topics: List[str] = []
            try:
                recent_videos = await self.repo.get_recent_videos(limit=50)
                for rv in recent_videos:
                    if rv.get("topic"):
                        excluded_topics.append(rv["topic"])
                    if rv.get("title"):
                        excluded_topics.append(rv["title"])
            except Exception:
                pass

            script: VideoScript = await self.script_service.generate_script(
                topic=topic,
                excluded_topics=excluded_topics
            )
            logger.info(f"[{job_id}] Script generated: '{script.title}' (Category: {script.category}) with {len(script.scenes)} scenes.")

            # Pick persona & voice for varied studio delivery
            chosen_persona, chosen_voice = self.voice_service.pick_random_persona_and_voice()

            if progress_callback:
                await progress_callback(
                    f"🎙️ [2/4] Naskah siap: *\"{script.title[:30]}...\"*\n"
                    f"Sedang merekam suara Google AI Studio: *{chosen_persona}* (Suara: *{chosen_voice}*)..."
                )

            # 2. Synthesize complete narration with Google AI Studio TTS (1 Request for entire video)
            voice_result = await self.voice_service.synthesize_full_voiceover(
                scenes=script.scenes,
                output_dir=job_temp_dir,
                persona=chosen_persona,
                voice=chosen_voice,
                progress_callback=progress_callback
            )
            audio_map = {res.scene_number: res for res in voice_result.scene_results}

            # 3. Process scenes: Visuals matched with Google AI Studio audio slices
            scene_inputs: List[VideoSceneInput] = []
            total_duration = 0.0
            used_media_ids = set()

            for scene in script.scenes:
                audio_res = audio_map.get(scene.scene_number)
                if not audio_res:
                    raise RuntimeError(f"Missing Google AI Studio voiceover audio for scene {scene.scene_number}")

                # Visual Image with deduplication
                img_path = await self.image_service.fetch_scene_visual(
                    scene_number=scene.scene_number,
                    prompt=scene.visual_prompt,
                    keywords=scene.keywords,
                    output_dir=job_temp_dir,
                    width=settings.VIDEO_WIDTH,
                    height=settings.VIDEO_HEIGHT,
                    used_media_ids=used_media_ids
                )

                scene_inputs.append(
                    VideoSceneInput(
                        scene_number=scene.scene_number,
                        image_path=str(img_path),
                        audio_path=audio_res.audio_path,
                        duration=audio_res.duration,
                        words=audio_res.words,
                        character_emotion=getattr(scene, "character_emotion", "happiness")
                    )
                )
                total_duration += audio_res.duration

            if progress_callback:
                await progress_callback(
                    f"🎞️ [3/4] Audio & visual lengkap! Merender video vertikal 9:16...\n"
                    f"Efek Ken Burns pan/zoom & subtitle kinetik sedang disusun..."
                )

            # 4. Smart Mood-Aware Background Music (BGM) Selection
            bgm_file = None
            bgm_dir = settings.abs_assets_dir / "bgm"
            if bgm_dir.exists():
                audio_files = list(bgm_dir.glob("*.mp3")) + list(bgm_dir.glob("*.wav"))
                if audio_files:
                    topic_lower = (topic or script.topic).lower()
                    if any(k in topic_lower for k in ["mystery", "dark", "secret", "creepy", "pharaoh", "forbidden", "unsolved", "terrifying"]):
                        candidates = [f for f in audio_files if "mystery" in f.name.lower() or "dark" in f.name.lower()]
                    elif any(k in topic_lower for k in ["universe", "space", "galaxy", "future", "brain", "superpower", "discover"]):
                        candidates = [f for f in audio_files if "cinematic" in f.name.lower()]
                    else:
                        candidates = [f for f in audio_files if "lofi" in f.name.lower()]

                    bgm_file = random.choice(candidates) if candidates else random.choice(audio_files)
                    logger.info(f"Selected BGM for job [{job_id}]: {bgm_file.name}")

            # 5. Generate High-CTR Siesta Thumbnail (To be baked into Frame 0 for YouTube Shorts)
            thumbnail_path = settings.abs_output_dir / f"thumb_{job_id}.jpg"
            try:
                first_bg = scene_inputs[0].image_path if scene_inputs else None
                first_emotion = getattr(script.scenes[0], "character_emotion", "concentration")
                await self.thumbnail_service.generate_thumbnail(
                    title=script.title,
                    category=script.category,
                    output_path=thumbnail_path,
                    emotion=first_emotion,
                    bg_image_path=first_bg,
                    width=settings.VIDEO_WIDTH,
                    height=settings.VIDEO_HEIGHT
                )
            except Exception as te:
                logger.warning(f"[{job_id}] Thumbnail generation failed: {te}")
                thumbnail_path = None

            # 6. Composite and Render Video with MoviePy (Bakes thumbnail into Frame 0)
            output_filename = f"short_{job_id}.mp4"
            final_output_path = settings.abs_output_dir / output_filename

            await self.video_engine.render_video(
                scenes=scene_inputs,
                output_path=final_output_path,
                bgm_path=bgm_file,
                intro_thumbnail_path=thumbnail_path
            )

            # 7. Optional: Upload to YouTube with custom thumbnail
            youtube_id = None
            youtube_error = None
            if auto_upload_youtube and self.youtube_service.is_configured():
                if progress_callback:
                    await progress_callback("📡 [4/4] Video selesai dirender! Mengupload otomatis ke YouTube Shorts...")
                try:
                    youtube_id = await self.youtube_service.upload_video(
                        video_path=final_output_path,
                        title=script.title,
                        description=script.description,
                        tags=script.tags,
                        thumbnail_path=thumbnail_path,
                        privacy_status=settings.YOUTUBE_PRIVACY_STATUS
                    )
                    if youtube_id:
                        logger.info(f"[{job_id}] Auto-uploaded to YouTube Shorts: id={youtube_id}")
                    else:
                        youtube_error = self.youtube_service.last_error or "Gagal mengautentikasi atau mengunggah ke YouTube."
                        logger.warning(f"[{job_id}] YouTube upload failed: {youtube_error}")
                except Exception as ye:
                    youtube_error = str(ye)
                    logger.warning(f"YouTube upload error: {ye}")
            elif not auto_upload_youtube:
                youtube_error = None
            elif not self.youtube_service.is_configured():
                youtube_error = "Kredensial YouTube belum dikonfigurasi di server (perlu client_secrets.json atau token)."
            
            if progress_callback:
                await progress_callback("🚀 [4/4] Mengirim file video .mp4 ke Telegram...")

            # 8. Persist to Database
            tags_str = " ".join(script.tags)
            video_db_id = await self.repo.save_video(
                user_id=user_id,
                topic=script.topic,
                title=script.title,
                description=script.description,
                tags=tags_str,
                duration=round(total_duration, 2),
                video_path=str(final_output_path),
                youtube_id=youtube_id
            )

            await self.repo.log_generation(trigger_type, script.topic, "success")

            return FullVideoResult(
                video_id=video_db_id,
                topic=script.topic,
                title=script.title,
                description=script.description,
                tags=script.tags,
                duration=round(total_duration, 2),
                video_path=str(final_output_path),
                youtube_id=youtube_id,
                youtube_error=youtube_error,
                thumbnail_path=str(thumbnail_path) if thumbnail_path and thumbnail_path.exists() else None,
                voice_persona=voice_result.persona_name,
                voice_name=voice_result.voice_name
            )

        except Exception as e:
            logger.error(f"[{job_id}] Video generation failed: {e}", exc_info=True)
            await self.repo.log_generation(trigger_type, topic or "Auto", "failed", str(e))
            raise e
        finally:
            # Guarantee temporary scene visual and audio files are wiped to prevent disk exhaustion
            if job_temp_dir.exists():
                try:
                    shutil.rmtree(job_temp_dir, ignore_errors=True)
                    logger.debug(f"[{job_id}] Purged temp directory: {job_temp_dir}")
                except Exception as ce:
                    logger.warning(f"[{job_id}] Failed to purge temp dir {job_temp_dir}: {ce}")
