import os
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

logger = logging.getLogger("ThumbnailGenerator")

# Evcarix Brand Colors
ACCENT_COLORS = {
    "electric_vehicle": "#00D4FF",
    "artificial_intelligence": "#8B00FF",
    "robotics": "#00FF88",
    "battery_tech": "#FF6B00",
    "future_tech": "#FF00FF",
    "default": "#00D4FF"
}

class ThumbnailGenerator:
    def __init__(self):
        # GitHub Actions Ubuntu font path - LiberationSans is standard
        self.font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if not os.path.exists(self.font_path):
            # Fallback to local assets if exists
            self.font_path = "assets/fonts/LiberationSans-Bold.ttf"
            if not os.path.exists(self.font_path):
                self.font_path = None # PIL will use default

    def create(self, title: str, topic: str, output_path: str, is_short: bool = True) -> str:
        """
        Main method called by Editor.
        Creates 1280x720 thumbnail (long) or 1080x1920 (shorts).
        """
        try:
            if is_short:
                return self.create_shorts(title, topic, output_path)
            else:
                return self.create_horizontal(title, topic, output_path)
        except Exception as e:
            logger.error(f"[ThumbnailGenerator] Create error: {e}")
            # Generate a solid color emergency thumb
            img = Image.new("RGB", (1080, 1920) if is_short else (1280, 720), "#0A0A0F")
            img.save(output_path)
            return output_path

    def _get_base_canvas(self, width: int, height: int):
        # Dark Gradient Background #0A0A0F -> #001833
        base = Image.new("RGB", (width, height), "#0A0A0F")
        draw = ImageDraw.Draw(base)
        for y in range(height):
            # Simple linear gradient simulation
            r = int(10 - (10 * y / height))
            g = int(10 + (14 * y / height))
            b = int(15 + (36 * y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        return base

    def create_shorts(self, title: str, topic: str, output_path: str) -> str:
        width, height = 1080, 1920
        img = self._get_base_canvas(width, height)
        self._draw_elements(img, title, topic, width, height)
        img.save(output_path, "JPEG", quality=90)
        return output_path

    def create_horizontal(self, title: str, topic: str, output_path: str) -> str:
        width, height = 1280, 720
        img = self._get_base_canvas(width, height)
        self._draw_elements(img, title, topic, width, height)
        img.save(output_path, "JPEG", quality=90)
        return output_path

    def _draw_elements(self, img, title, topic, w, h):
        draw = ImageDraw.Draw(img)
        # Match topic to color
        clean_topic = topic.lower().replace(" ", "_")
        accent = ACCENT_COLORS.get(clean_topic, ACCENT_COLORS["default"])
        
        # 1. Left Edge Accent Stripe (6px)
        draw.rectangle([0, 0, 6, h], fill=accent)
        
        # 2. Text Logic
        font_size = int(w * 0.11)
        try:
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Split title into lines (max 2 words per line)
        words = title.upper().split()
        lines = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
        
        y_cursor = h // 3
        for line in lines[:5]:
            # Glow effect: Draw blurred text behind
            glow_offset = 2
            for ox in [-glow_offset, glow_offset]:
                for oy in [-glow_offset, glow_offset]:
                    draw.text((w//2 + ox, y_cursor + oy), line, font=font, fill=accent, anchor="mm")
            
            # Main white text
            draw.text((w//2, y_cursor), line, font=font, fill="white", anchor="mm")
            y_cursor += font_size + 30

        # 3. Bottom Branding Bar
        brand_font_size = int(w * 0.06)
        try:
            brand_font = ImageFont.truetype(self.font_path, brand_font_size) if self.font_path else ImageFont.load_default()
        except:
            brand_font = ImageFont.load_default()
            
        draw.text((w//2, h - 150), "⚡ EVCARIX", font=brand_font, fill=accent, anchor="mm")
        draw.text((w//2, h - 80), "THE WORLD'S LEAD EV DATA AUTHORITY", font=brand_font, fill="white", anchor="mm")
