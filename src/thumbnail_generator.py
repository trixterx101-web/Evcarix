import os
import re
import requests
import logging
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

logger = logging.getLogger("ThumbnailGenerator")

ACCENT_COLORS = {
    "electric_vehicle":        "#00D4FF",
    "artificial_intelligence": "#8B00FF",
    "robotics":                "#00FF88",
    "battery_tech":            "#FF6B00",
    "future_tech":             "#FF00FF",
    "default":                 "#00D4FF",
}

TOPIC_QUERIES = {
    "electric_vehicle":        "electric car highway",
    "artificial_intelligence": "artificial intelligence technology",
    "robotics":                "industrial robot factory",
    "battery_tech":            "battery electric charging",
    "future_tech":             "futuristic city technology",
    "default":                 "electric vehicle road",
}

FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = None


class ThumbnailGenerator:
    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY")

    def create(self, title: str, topic: str = "default", stat: str = "",
               category: str = "default", output_path: str = "thumbnail.jpg",
               is_short: bool = False) -> str:
        """Create 1280x720 thumbnail with real background image + title overlay."""
        W, H = (1080, 1920) if is_short else (1280, 720)
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

        topic_key = topic.lower().replace(" ", "_")
        accent    = ACCENT_COLORS.get(topic_key, ACCENT_COLORS["default"])
        query     = TOPIC_QUERIES.get(topic_key, TOPIC_QUERIES["default"])

        # 1. Try to fetch a real background image
        bg = self._fetch_pexels_image(query, W, H)
        if bg is None:
            bg = self._gradient_bg(W, H, accent)

        # 2. Darken + blur bottom half for text readability
        bg = self._add_text_bg(bg, W, H)

        # 3. Draw text
        draw = ImageDraw.Draw(bg)
        self._draw_title(draw, title, accent, W, H)
        self._draw_branding(draw, accent, W, H)

        bg.save(output_path, "JPEG", quality=92)
        logger.info(f"[Thumbnail] ✅ Saved: {output_path}")
        return output_path

    # ── Background ─────────────────────────────────────────────────────────

    def _fetch_pexels_image(self, query: str, W: int, H: int):
        if not self.pexels_key:
            return None
        try:
            url = (f"https://api.pexels.com/v1/search?query={query}"
                   f"&per_page=5&orientation={'portrait' if H > W else 'landscape'}")
            r = requests.get(url, headers={"Authorization": self.pexels_key}, timeout=10)
            photos = r.json().get("photos", [])
            if not photos:
                return None
            import random
            photo = random.choice(photos[:3])
            img_url = photo["src"]["large2x"] if H <= W else photo["src"]["portrait"]
            img_data = requests.get(img_url, timeout=20).content
            from io import BytesIO
            img = Image.open(BytesIO(img_data)).convert("RGB")
            # Center-crop to target ratio
            img = self._center_crop(img, W, H)
            return img
        except Exception as e:
            logger.warning(f"[Thumbnail] Pexels fetch failed: {e}")
            return None

    def _center_crop(self, img: Image.Image, W: int, H: int) -> Image.Image:
        iw, ih = img.size
        target_ratio = W / H
        current_ratio = iw / ih
        if current_ratio > target_ratio:
            new_w = int(ih * target_ratio)
            left = (iw - new_w) // 2
            img = img.crop((left, 0, left + new_w, ih))
        else:
            new_h = int(iw / target_ratio)
            top = (ih - new_h) // 2
            img = img.crop((0, top, iw, top + new_h))
        return img.resize((W, H), Image.LANCZOS)

    def _gradient_bg(self, W: int, H: int, accent: str) -> Image.Image:
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)
        ar, ag, ab = int(accent[1:3],16), int(accent[3:5],16), int(accent[5:7],16)
        for y in range(H):
            t = y / H
            r = int(10 + ar * t * 0.3)
            g = int(10 + ag * t * 0.3)
            b = int(20 + ab * t * 0.4)
            draw.line([(0, y), (W, y)], fill=(min(r,255), min(g,255), min(b,255)))
        return img

    def _add_text_bg(self, img: Image.Image, W: int, H: int) -> Image.Image:
        """Add dark gradient overlay on bottom 60% for text readability."""
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        zone_start = int(H * 0.35)
        for y in range(zone_start, H):
            alpha = int(200 * (y - zone_start) / (H - zone_start))
            draw.line([(0, y), (W, y)], fill=(0, 0, 15, alpha))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay)
        return img.convert("RGB")

    # ── Text ───────────────────────────────────────────────────────────────

    def _get_font(self, size: int):
        try:
            if FONT_PATH and os.path.exists(FONT_PATH):
                return ImageFont.truetype(FONT_PATH, size)
        except:
            pass
        return ImageFont.load_default()

    def _draw_title(self, draw: ImageDraw.Draw, title: str, accent: str,
                    W: int, H: int):
        # Clean & wrap
        clean = re.sub(r"[^\w\s\-:,.!?%$]", "", title).upper()
        font_size = int(W * 0.072)
        font = self._get_font(font_size)
        wrap_w = 22 if W >= 1280 else 18
        lines = textwrap.wrap(clean, width=wrap_w)[:4]

        line_h   = font_size + 14
        total_h  = len(lines) * line_h
        y_start  = H - total_h - 120

        ar, ag, ab = int(accent[1:3],16), int(accent[3:5],16), int(accent[5:7],16)

        for i, line in enumerate(lines):
            y = y_start + i * line_h
            # Glow
            for ox, oy in [(-2,-2),(2,-2),(-2,2),(2,2)]:
                draw.text((W//2 + ox, y + oy), line, font=font,
                          fill=(ar//2, ag//2, ab//2), anchor="mt")
            # Main
            draw.text((W//2, y), line, font=font, fill="white", anchor="mt")

        # Accent underline
        y_line = y_start + total_h + 8
        draw.rectangle([W//2 - 120, y_line, W//2 + 120, y_line + 4],
                       fill=accent)

    def _draw_branding(self, draw: ImageDraw.Draw, accent: str, W: int, H: int):
        """Evcarix logo bar top-left."""
        font = self._get_font(int(W * 0.042))
        # Background pill
        draw.rectangle([20, 20, 220, 68], fill=(0, 0, 0, 180))
        draw.text((30, 26), "⚡ EVCARIX", font=font, fill=accent)
