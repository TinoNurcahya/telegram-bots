import os
import re
import logging
from pathlib import Path
from typing import Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from src.config import settings, BASE_DIR

logger = logging.getLogger(__name__)

class ThumbnailService:
    """Generates high-CTR 9:16 vertical YouTube Shorts thumbnails featuring Siesta."""

    def __init__(self, assets_dir: Optional[Path] = None):
        self.assets_dir = assets_dir or (BASE_DIR / settings.ASSETS_DIR)
        self.siesta_dir = self.assets_dir / "characters" / "siesta"

    def _get_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont:
        """Loads project or system font with fallback."""
        # 1. Project bundled fonts
        project_candidates = [
            settings.abs_assets_dir / "fonts" / font_name,
            settings.abs_assets_dir / "fonts" / "Montserrat-Black.ttf",
            settings.abs_assets_dir / "fonts" / "Arial-Bold.ttf",
            settings.abs_assets_dir / "fonts" / "Impact.ttf",
        ]
        for pf in project_candidates:
            if pf.exists():
                try:
                    return ImageFont.truetype(str(pf), size)
                except Exception:
                    pass

        # 2. Windows system fonts
        win_fonts = Path("C:/Windows/Fonts")
        font_path = win_fonts / font_name
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size)
            except Exception:
                pass

        # 3. Linux system fonts
        for lf in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"]:
            p = Path(lf)
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except Exception:
                    pass

        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def _clean_title_for_thumbnail(self, raw_title: str) -> List[str]:
        """Extracts 2-4 punchy, high-impact uppercase words from the title."""
        # Strip hashtags, emojis, and punctuation
        cleaned = re.sub(r"[#@][\w_]+", "", raw_title)
        cleaned = re.sub(r"[^\w\s\'-]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Remove filler words at the start if needed
        words = cleaned.split()
        if not words:
            return ["MYSTERIOUS", "CASE"]

        # Limit to 4-6 most punchy words
        short_words = words[:5]

        # Break into 2 or 3 lines
        if len(short_words) <= 2:
            return [" ".join(short_words).upper()]
        elif len(short_words) == 3:
            return [short_words[0].upper(), f"{short_words[1]} {short_words[2]}".upper()]
        elif len(short_words) == 4:
            return [f"{short_words[0]} {short_words[1]}".upper(), f"{short_words[2]} {short_words[3]}".upper()]
        else:
            return [f"{short_words[0]} {short_words[1]}".upper(), f"{short_words[2]} {short_words[3]} {short_words[4]}".upper()]

    async def generate_thumbnail(
        self,
        title: str,
        category: str,
        output_path: Path,
        emotion: str = "concentration",
        bg_image_path: Optional[str] = None,
        width: int = 720,
        height: int = 1280
    ) -> Path:
        """Composites a professional high-CTR 9:16 vertical thumbnail with Siesta."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Background Canvas
        if bg_image_path and os.path.exists(bg_image_path):
            try:
                with Image.open(bg_image_path) as raw_bg:
                    raw_bg = raw_bg.convert("RGB")
                    # Crop & resize to 9:16
                    target_ratio = width / height
                    bw, bh = raw_bg.size
                    b_ratio = bw / bh
                    if b_ratio > target_ratio:
                        new_w = int(bh * target_ratio)
                        off_x = (bw - new_w) // 2
                        raw_bg = raw_bg.crop((off_x, 0, off_x + new_w, bh))
                    else:
                        new_h = int(bw / target_ratio)
                        off_y = (bh - new_h) // 2
                        raw_bg = raw_bg.crop((0, off_y, bw, off_y + new_h))

                    bg = raw_bg.resize((width, height), Image.Resampling.LANCZOS)
                    # Apply dramatic blur and dark contrast
                    bg = bg.filter(ImageFilter.GaussianBlur(10))
                    dark_overlay = Image.new("RGBA", (width, height), (8, 10, 18, 140))
                    bg = Image.alpha_composite(bg.convert("RGBA"), dark_overlay).convert("RGB")
            except Exception as e:
                logger.warning(f"Could not load background image for thumbnail: {e}")
                bg = self._create_gradient_bg(width, height)
        else:
            bg = self._create_gradient_bg(width, height)

        # 2. Subtle Radial Mystery Glow
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow)
        g_draw.ellipse(
            [width // 2 - 260, height // 2 - 180, width // 2 + 260, height // 2 + 320],
            fill=(0, 140, 255, 45)
        )
        glow = glow.filter(ImageFilter.GaussianBlur(80))
        bg.paste(glow, (0, 0), glow)

        # 3. Load & Composite Siesta Character Sprite
        sprite_file = self.siesta_dir / f"{emotion}.png"
        if not sprite_file.exists():
            sprite_file = self.siesta_dir / "concentration.png"
        if not sprite_file.exists():
            # Fallback to any existing sprite
            available = list(self.siesta_dir.glob("*.png"))
            if available:
                sprite_file = available[0]

        if sprite_file.exists():
            try:
                sprite = Image.open(sprite_file).convert("RGBA")
                is_landscape = width > height
                target_h = int(height * (0.94 if is_landscape else 0.78))
                sw, sh = sprite.size
                target_w = int(sw * (target_h / sh))
                sprite_resized = sprite.resize((target_w, target_h), Image.Resampling.LANCZOS)

                if is_landscape:
                    pos_x = width - target_w - 15
                    pos_y = height - target_h + 10
                else:
                    pos_x = (width - target_w) // 2
                    pos_y = height - target_h + 10

                # Soft vignette gradient mask at the top of the sprite to eliminate hard edges
                mask = Image.new("L", (target_w, target_h), 255)
                m_draw = ImageDraw.Draw(mask)
                fade_h = 50 if is_landscape else 70
                for fy in range(fade_h):
                    alpha = int(255 * (fy / fade_h) ** 2)
                    m_draw.line([(0, fy), (target_w, fy)], fill=alpha)

                bg.paste(sprite_resized, (pos_x, pos_y), mask)
            except Exception as e:
                logger.warning(f"Failed to composite Siesta sprite into thumbnail: {e}")

        # 4. Dark Vignette for Maximum Text Readability
        is_landscape = width > height
        top_grad = Image.new("RGBA", (width, int(height * (0.55 if is_landscape else 0.44))), (0, 0, 0, 0))
        t_draw = ImageDraw.Draw(top_grad)
        for y in range(top_grad.height):
            alpha = int(245 * (1 - (y / top_grad.height) ** 1.3))
            t_draw.line([(0, y), (width, y)], fill=(4, 6, 12, alpha))
        bg.paste(top_grad, (0, 0), top_grad)

        # 5. Category Pill Badge with Vector Red Dot
        draw = ImageDraw.Draw(bg)
        badge_text = category.upper() if len(category) <= 22 else category[:20].upper() + "..."
        font_badge = self._get_font("arialbd.ttf", 22)
        bbox = draw.textbbox((0, 0), badge_text, font=font_badge)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        dot_radius = 6
        padding_x = 24
        padding_y = 10
        badge_w = tw + dot_radius * 2 + 16 + padding_x * 2
        badge_h = th + padding_y * 2
        bx = 64 if is_landscape else (width - badge_w) // 2
        by = 110 if is_landscape else 80

        draw.rounded_rectangle(
            [bx, by, bx + badge_w, by + badge_h],
            radius=badge_h // 2,
            fill=(18, 22, 36, 240),
            outline=(255, 65, 65),
            width=2
        )
        # Vector glowing red dot
        dot_x = bx + padding_x + dot_radius
        dot_y = by + badge_h // 2
        draw.ellipse(
            [dot_x - dot_radius, dot_y - dot_radius, dot_x + dot_radius, dot_y + dot_radius],
            fill=(255, 50, 50)
        )
        # Badge Text
        draw.text((dot_x + dot_radius + 12, by + padding_y - 1), badge_text, font=font_badge, fill=(255, 255, 255))

        # 6. High-CTR Bold Title
        title_lines = self._clean_title_for_thumbnail(title)
        font_title = self._get_font("impact.ttf", 74 if is_landscape else 66)
        cur_y = by + badge_h + 24

        for i, line in enumerate(title_lines):
            l_box = draw.textbbox((0, 0), line, font=font_title)
            lw = l_box[2] - l_box[0]
            lx = 64 if is_landscape else (width - lw) // 2
            # Alternating colors: yellow accent for punch line, white for base
            color = (255, 228, 45) if (i == len(title_lines) - 1 and len(title_lines) > 1) else (255, 255, 255)

            # 8-Direction thick black drop shadow
            for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4), (0, -4), (4, 0), (-4, 0)]:
                draw.text((lx + ox, cur_y + oy), line, font=font_title, fill=(0, 0, 0))
            draw.text((lx, cur_y), line, font=font_title, fill=color)
            cur_y += 84 if is_landscape else 76

        bg.save(str(output_path), "JPEG", quality=95)
        logger.info(f"Generated High-CTR Siesta thumbnail: {output_path}")
        return output_path

    def _create_gradient_bg(self, width: int, height: int) -> Image.Image:
        """Creates a smooth cinematic deep blue/dark gradient canvas."""
        bg = Image.new("RGB", (width, height), (12, 14, 22))
        draw = ImageDraw.Draw(bg)
        for y in range(height):
            ratio = y / height
            r = int(18 * (1 - ratio) + 8 * ratio)
            g = int(24 * (1 - ratio) + 10 * ratio)
            b = int(45 * (1 - ratio) + 18 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        return bg
