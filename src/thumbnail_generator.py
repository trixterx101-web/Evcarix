"""
Evcarix Thumbnail Generator
Generates a professional 1280x720 YouTube thumbnail for long-form videos.
Usage:
    from src.thumbnail_generator import ThumbnailGenerator
    gen = ThumbnailGenerator()
    path = gen.create(title="50% Range Lost in Winter?", stat="-50%", category="range")
"""

import os
import math
import random
import textwrap
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    raise ImportError("pip install Pillow")

# ── Constants ──────────────────────────────────────────────────────────────────
W, H       = 1280, 720
ASSETS_DIR = Path("assets")
OUT_DIR    = Path("output")

# Category color palettes  — gradient start / end / accent
PALETTES = {
    "battery":        ("#0D1B2A", "#1A3A5C", "#00D4FF"),
    "range":          ("#0A1628", "#1C3D6E", "#00FF88"),
    "charging":       ("#1A0A00", "#4A1800", "#FF6B00"),
    "ownership":      ("#0D1A0D", "#1A3D1A", "#7FFF00"),
    "comparison":     ("#1A0A2E", "#3D1A6E", "#BF00FF"),
    "market":         ("#1A1200", "#4A3600", "#FFD700"),
    "infrastructure": ("#001A1A", "#004D4D", "#00FFFF"),
    "education":      ("#0D0D1A", "#1A1A4D", "#4488FF"),
    "tools":          ("#1A000D", "#4D0026", "#FF0066"),
    "default":        ("#0D0D0D", "#1A1A2E", "#FFFFFF"),
}

# Evcarix brand
BRAND_NAME   = "EVCARIX"
BRAND_MOTTO  = "No Hype. Just Numbers."
BRAND_COLOR  = "#FFFFFF"
ACCENT_ALPHA = 200   # 0-255


class ThumbnailGenerator:

    def __init__(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self._font_cache = {}

    def create(
        self,
        title: str,
        stat: str = "",
        category: str = "default",
        output_path: str = "",
        bg_image_path: str = None,
        is_short: bool = False,
        is_comparison: bool = False
    ) -> str:
        """
        v9.0 High-Impact Thumbnail Engine (Matching USER Design Style)
        """
        width, height = (1080, 1920) if is_short else (1280, 720)
        
        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(OUT_DIR / f"thumbnail_{ts}.jpg")
        elif output_path.lower().endswith('.png'):
            output_path = output_path.rsplit('.', 1)[0] + '.jpg'

        # ── Step 1: AI Visual Core (FLUX via Pollinations) ──
        try:
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            
            # Tasarım talimatlarını içeren gelişmiş prompt
            style_instruction = (
                "Professional automotive thumbnail. High contrast, cinematic lighting, ultra-realistic. "
                "Center-weighted composition. Sharp focus on the vehicle or technical components. "
                "Clean background, futuristic tech vibe. NO TEXT on the image itself."
            )
            if is_comparison:
                style_instruction = "Side-by-side comparison of two different electric vehicles or technologies. Symmetrical composition, high contrast, clean divide."

            designer_prompt = (
                f"Design a high-impact AI image generation prompt for a YouTube thumbnail about: '{title}'. "
                f"{style_instruction} Focus on {category} theme. Output ONLY the prompt string."
            )
            
            chat = client.chat.completions.create(
                messages=[{"role": "user", "content": designer_prompt}],
                model="llama-3.3-70b-versatile",
            )
            ai_prompt = chat.choices[0].message.content.strip()
            
            import urllib.parse
            import requests
            encoded_prompt = urllib.parse.quote(ai_prompt)
            image_url = f"https://pollinations.ai/p/{encoded_prompt}?width={width}&height={height}&model=flux&seed={random.randint(1,99999)}"
            
            r = requests.get(image_url, timeout=30)
            if r.status_code == 200:
                with open(output_path, "wb") as f: f.write(r.content)
                
                # ── Step 2: Graphic Design Overlays (Adding the 'User Look') ──
                img = Image.open(output_path).convert("RGB")
                draw = ImageDraw.Draw(img)

                if is_comparison:
                    self._draw_split_line(img)
                
                # Siyah gölge katmanı (Metin okunurluğu için)
                self._draw_vignette(img)
                
                # Ana Başlık (Impact Tarzı)
                self._draw_mega_title(img, title, is_comparison)
                
                # İstatistik Rozeti (Örn: -45% RANGE?!)
                if stat:
                    self._draw_high_impact_badge(img, stat)
                
                # Grafik/Veri Katmanı
                if random.random() > 0.5:
                    self._draw_mini_graph(img)
                
                # Marka
                self._draw_brand_tag(img)

                img.save(output_path, "JPEG", quality=90, optimize=True)
                return output_path
        except Exception as e:
            print(f"[Thumbnail] AI failed: {e}. Using Composite Engine.")
            return self._create_composite_fallback(title, stat, category, output_path, is_short)

    def _draw_vignette(self, img: Image.Image):
        """Adds dark gradients to edges to make text pop."""
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = img.size
        # Bottom-up shadow
        for y in range(h // 2, h):
            alpha = int(180 * ((y - h//2) / (h//2)))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        # Top-down shadow
        for y in range(h // 3):
            alpha = int(120 * (1 - (y / (h//3))))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _draw_split_line(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        w, h = img.size
        # Vertical split line with glow
        draw.line([(w//2, 0), (w//2, h)], fill="#FFD700", width=4)

    def _draw_mega_title(self, img: Image.Image, title: str, is_comparison: bool):
        draw = ImageDraw.Draw(img)
        w, h = img.size
        title = title.upper()
        
        # Max impact font
        font_size = 110 if len(title) < 20 else 85
        font = self._font(font_size, bold=True)
        
        lines = textwrap.wrap(title, width=15 if is_comparison else 20)
        y_text = 60
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            
            # Siyah kutu arkası (Highlight)
            draw.rectangle([50, y_text - 5, 70 + tw, y_text + th + 15], fill=(0, 0, 0, 200))
            # Beyaz metin
            draw.text((60, y_text), line, font=font, fill="#FFFFFF")
            y_text += th + 30

    def _draw_high_impact_badge(self, img: Image.Image, stat: str):
        """Red or Yellow badge like '-45% RANGE LOST!'"""
        draw = ImageDraw.Draw(img)
        w, h = img.size
        font = self._font(75, bold=True)
        
        bbox = draw.textbbox((0, 0), stat, font=font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        
        # Badge rect
        bx, by = 60, h - 200
        padding = 30
        
        # Glow shadow
        draw.rectangle([bx-10, by-10, bx+tw+padding*2+10, by+th+padding*2+10], fill=(0, 0, 0, 100))
        # Main badge (Yellow for data, Red for warning)
        color = "#FFD700" if "-" not in stat else "#FF3131"
        draw.rectangle([bx, by, bx+tw+padding*2, by+th+padding*2], fill=color)
        
        # Text in black
        draw.text((bx+padding, by+padding//2), stat, font=font, fill="#000000")

    def _draw_mini_graph(self, img: Image.Image):
        """Simple trend line graph in bottom right."""
        w, h = img.size
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        gx, gy = w - 350, h - 250
        gw, gh = 300, 150
        
        # Grid lines
        draw.line([(gx, gy+gh), (gx+gw, gy+gh)], fill=(255, 255, 255, 100), width=2) # X axis
        draw.line([(gx, gy), (gx, gy+gh)], fill=(255, 255, 255, 100), width=2) # Y axis
        
        # Random trend line (Red/Green)
        points = []
        for i in range(5):
            points.append((gx + (i * gw // 4), gy + random.randint(10, gh - 10)))
        
        draw.line(points, fill="#FF3131", width=5, joint="curve")
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _draw_brand_tag(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        w, h = img.size
        font = self._font(24, bold=True)
        draw.text((w - 180, h - 50), "EVCARIX DATA", font=font, fill="#FFFFFF")

    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        key = (size, bold)
        if key in self._font_cache: return self._font_cache[key]
        
        candidates = [
            "C:/Windows/Fonts/impact.ttf",
            "C:/Windows/Fonts/ariblk.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
        
        font = None
        for path in candidates:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except: continue
        
        if not font: font = ImageFont.load_default()
        self._font_cache[key] = font
        return font

    def _create_composite_fallback(self, title, stat, category, output_path, is_short):
        # Legacy composite logic if AI fails
        w, h = (1080, 1920) if is_short else (1280, 720)
        img = Image.new("RGB", (w, h), "#0D1B2A")
        self._draw_mega_title(img, title, False)
        if stat: self._draw_high_impact_badge(img, stat)
        img.save(output_path, "JPEG", quality=85)
        return output_path


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    gen = ThumbnailGenerator()
    tests = [
        ("50% Range Lost in Winter? Real Data From 70 EVs", "-50%",  "range"),
        ("Fast Charging KILLS Battery? 500,000km Proof",    "500K",  "battery"),
        ("800V vs 400V: The Real Difference Nobody Shows",  "800V",  "charging"),
        ("EV vs Diesel: 5-Year True Cost Breakdown",        "5YR",   "ownership"),
        ("LFP Batteries: 1 Million KM Reality Check",       "1M KM", "battery"),
    ]
    for title, stat, cat in tests:
        path = gen.create(title=title, stat=stat, category=cat)
        print(f"  → {path}")
