import os
import io
import random
import urllib.parse
import logging
from pathlib import Path
from typing import Optional, List, Set, Any
import aiohttp
from PIL import Image, ImageDraw, ImageFont

from src.config import settings

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self, pexels_api_key: Optional[str] = None):
        self.pexels_api_key = pexels_api_key or settings.PEXELS_API_KEY

    async def fetch_scene_visual(
        self,
        scene_number: int,
        prompt: str,
        keywords: List[str],
        output_dir: Path,
        width: int = 720,
        height: int = 1280,
        used_media_ids: Optional[Set[Any]] = None
    ) -> Path:
        """
        Fetches high-res vertical imagery with a 4-tier resilience & anti-duplication pipeline:
        Tier 1: Pollinations.ai (AI Generation with unique random seed)
        Tier 2: Pexels API (Random multi-page candidate selection + ID deduplication)
        Tier 3: Wikimedia Commons (Random selection from matching real photos)
        Tier 4: Offline Anime Aesthetic Canvas Fallback
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        target_path = output_dir / f"scene_{scene_number}.jpg"

        # 1. Tier 1: Pollinations.ai AI Anime Generation (Unique Seed)
        success = await self._fetch_from_pollinations(prompt, keywords, target_path, width, height)
        if success and target_path.exists() and target_path.stat().st_size > 15000:
            logger.info(f"Successfully generated Studio Ghibli AI visual for scene {scene_number}")
            return target_path

        # 2. Tier 2: Pexels API with clean keywords, random choice, and deduplication
        if self.pexels_api_key and keywords:
            clean_keywords = [
                k.replace("anime", "").replace("illustration", "").replace("artwork", "").strip()
                for k in keywords if len(k.strip()) > 2
            ]
            clean_keywords = [k for k in clean_keywords if k] or keywords
            success = await self._fetch_from_pexels(clean_keywords, target_path, width, height, used_media_ids=used_media_ids)
            if success and target_path.exists() and target_path.stat().st_size > 15000:
                logger.info(f"Successfully fetched unique HD photo from Pexels for scene {scene_number}")
                return target_path

        # 3. Tier 3: Wikimedia Commons with randomized selection
        if keywords:
            clean_wiki = [k.replace("anime", "").strip() for k in keywords if len(k.strip()) > 2]
            success = await self._fetch_from_wikimedia(clean_wiki or keywords, target_path, width, height)
            if success and target_path.exists() and target_path.stat().st_size > 15000:
                return target_path

        # 4. Tier 4: Anime Aesthetic Canvas Fallback (offline)
        logger.warning(f"Using anime aesthetic canvas fallback for scene {scene_number}")
        self._generate_fallback_canvas(scene_number, keywords, target_path, width, height)
        return target_path

    def _smart_crop_and_save(self, image_bytes: bytes, target_path: Path, width: int, height: int) -> bool:
        """Crops image to exact 9:16 aspect ratio without distortion and saves."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                pil_img = pil_img.convert("RGB")
                target_ratio = width / height
                img_w, img_h = pil_img.size
                img_ratio = img_w / img_h

                if img_ratio > target_ratio:
                    new_w = int(img_h * target_ratio)
                    offset_x = (img_w - new_w) // 2
                    pil_img = pil_img.crop((offset_x, 0, offset_x + new_w, img_h))
                else:
                    new_h = int(img_w / target_ratio)
                    offset_y = (img_h - new_h) // 2
                    pil_img = pil_img.crop((0, offset_y, img_w, offset_y + new_h))

                resized = pil_img.resize((width, height), Image.Resampling.LANCZOS)
                resized.save(target_path, "JPEG", quality=92)
                return True
        except Exception as e:
            logger.warning(f"Failed to crop and save image: {e}")
            return False

    async def _fetch_from_pollinations(
        self, prompt: str, keywords: List[str], target_path: Path, width: int, height: int
    ) -> bool:
        """Generates authentic 2D Studio Ghibli anime artwork using Pollinations AI."""
        try:
            aspect_desc = "16:9 widescreen cinematic anime scenery" if width > height else "9:16 vertical anime scenery"
            ghibli_tag = f"masterpiece Studio Ghibli anime aesthetic, Hayao Miyazaki style, lush watercolor illustration, beautiful atmospheric lighting, {aspect_desc}"
            if prompt and len(prompt) > 20:
                full_prompt = f"{prompt}, {ghibli_tag}"
            elif keywords:
                full_prompt = f"Anime scenery of {' '.join(keywords[:2])}, {ghibli_tag}"
            else:
                full_prompt = f"Enchanting anime landscape, {ghibli_tag}"

            seed = random.randint(1000, 99999999)
            encoded_prompt = urllib.parse.quote(full_prompt[:260])
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={seed}"

            headers = {"User-Agent": "Mozilla/5.0"}
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        return self._smart_crop_and_save(content, target_path, width, height)
            return False
        except Exception as e:
            logger.warning(f"Pollinations anime generation failed: {e}")
            return False

    async def _fetch_from_wikimedia(
        self, keywords: List[str], target_path: Path, width: int, height: int
    ) -> bool:
        """Fetches a real HD photo from Wikimedia Commons matching scene keywords with random selection."""
        try:
            query = " ".join(keywords[:2])
            encoded_query = urllib.parse.quote(query)
            api_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                f"&gsrsearch={encoded_query}&gsrnamespace=6&prop=imageinfo&iiprop=url&format=json&gsrlimit=6"
            )

            headers = {"User-Agent": "AIVideoStudioBot/1.0 (portfolio@example.com)"}
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(api_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        pages = list(data.get("query", {}).get("pages", {}).values())
                        if pages:
                            random.shuffle(pages)
                            for page in pages:
                                info = page.get("imageinfo", [])
                                if info and "url" in info[0]:
                                    img_url = info[0]["url"]
                                    if img_url.lower().endswith((".jpg", ".jpeg", ".png")):
                                        async with session.get(img_url, headers=headers) as img_resp:
                                            if img_resp.status == 200:
                                                content = await img_resp.read()
                                                if len(content) > 20000:
                                                    logger.info(f"Successfully fetched Wikimedia photo: {page.get('title')}")
                                                    return self._smart_crop_and_save(content, target_path, width, height)
            return False
        except Exception as e:
            logger.warning(f"Wikimedia fetch failed: {e}")
            return False

    async def _fetch_from_picsum(
        self, scene_number: int, target_path: Path, width: int, height: int
    ) -> bool:
        """Fetches a guaranteed high-res real photograph from Picsum with unique seed."""
        try:
            random_seed = random.randint(1000, 999999)
            url = f"https://picsum.photos/seed/{random_seed}/{width}/{height}"
            headers = {"User-Agent": "Mozilla/5.0"}
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(target_path, "wb") as f:
                            f.write(content)
                        logger.info(f"Successfully fetched Picsum HD photo for scene {scene_number}")
                        return True
            return False
        except Exception as e:
            logger.warning(f"Picsum fetch failed: {e}")
            return False

    async def _fetch_from_pexels(
        self,
        keywords: List[str],
        target_path: Path,
        width: int,
        height: int,
        used_media_ids: Optional[Set[Any]] = None
    ) -> bool:
        """Fetches vertical HD photo from Pexels API with random selection and deduplication."""
        try:
            query = " ".join(keywords[:2]) if keywords else "mysterious landscape"
            page = random.randint(1, 3)
            orientation = "landscape" if width > height else "portrait"
            url = f"https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&orientation={orientation}&per_page=15&page={page}"
            headers = {
                "Authorization": self.pexels_api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        photos = data.get("photos", [])
                        if photos:
                            # Filter out already used photo IDs in this video
                            candidates = [p for p in photos if not used_media_ids or p.get("id") not in used_media_ids]
                            if not candidates:
                                candidates = photos
                            chosen = random.choice(candidates)
                            if used_media_ids is not None and chosen.get("id"):
                                used_media_ids.add(chosen.get("id"))
                            
                            img_url = chosen.get("src", {}).get("large2x") or chosen.get("src", {}).get("original")
                            if img_url:
                                async with session.get(img_url) as img_resp:
                                    if img_resp.status == 200:
                                        content = await img_resp.read()
                                        return self._smart_crop_and_save(content, target_path, width, height)
            return False
        except Exception as e:
            logger.warning(f"Pexels fetch failed: {e}")
            return False

    def _generate_fallback_canvas(
        self, scene_number: int, keywords: List[str], target_path: Path, width: int, height: int
    ) -> None:
        """Creates an enchanting Studio Ghibli anime aesthetic pastel gradient backdrop."""
        color_themes = [
            ((24, 20, 56), (75, 45, 110)),    # Ghibli Twilight Sky
            ((15, 45, 30), (38, 120, 75)),    # Ghibli Lush Meadow Green
            ((95, 38, 25), (195, 95, 55)),    # Ghibli Warm Sunset Glow
            ((35, 28, 65), (115, 65, 135)),   # Ghibli Dreamy Violet
            ((20, 55, 80), (70, 140, 175)),   # Ghibli Nostalgic Sky Blue
        ]
        top_color, bottom_color = color_themes[scene_number % len(color_themes)]

        img = Image.new("RGB", (width, height), top_color)
        draw = ImageDraw.Draw(img)

        for y in range(height):
            ratio = y / height
            r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
            g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
            b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        center_x, center_y = width // 2, height // 3
        draw.ellipse([center_x - 180, center_y - 180, center_x + 180, center_y + 180], outline=(255, 255, 255, 45), width=3)
        draw.text((width // 2, height // 3), "✨ GHIBLI ANIME ✨", fill=(255, 240, 200), anchor="mm")
        label = " • ".join(keywords).upper() if keywords else f"SCENE {scene_number}"
        draw.text((width // 2, height // 2), label, fill=(230, 230, 245), anchor="mm")

        img.save(target_path, "JPEG", quality=90)
