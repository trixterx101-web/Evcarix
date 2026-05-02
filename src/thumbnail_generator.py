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

    # ── Public API ─────────────────────────────────────────────────────────────
    def create(
        self,
        title: str,
        stat: str = "",
        category: str = "default",
        output_path: str = "",
    ) -> str:
        """
        Generate thumbnail and return saved file path.
        Args:
            title:    Main headline shown on thumbnail (max ~50 chars)
            stat:     Big eye-catching number/stat, e.g. "-45%", "800V", "1M KM"
            category: Evcarix category id for color palette
            output_path: Override save path (optional)
        """
        img = Image.new("RGB", (W, H), "#000000")

        self._draw_gradient_background(img, category)
        self._draw_grid_overlay(img)
        self._draw_glow_accent(img, category)
        self._draw_left_bar(img, category)
        self._draw_stat_block(img, stat, category)
        self._draw_title(img, title)
        self._draw_data_bar(img)
        self._draw_brand(img)
        self._draw_corner_badge(img, category)

        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(OUT_DIR / f"thumbnail_{ts}.jpg")

        img.save(output_path, "JPEG", quality=97, optimize=True)
        print(f"[Thumbnail] ✅ Saved → {output_path}")
        return output_path

    # ── Background ─────────────────────────────────────────────────────────────
    def _draw_gradient_background(self, img: Image.Image, category: str):
        palette = PALETTES.get(category, PALETTES["default"])
        c1 = self._hex(palette[0])
        c2 = self._hex(palette[1])
        draw = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

    def _draw_grid_overlay(self, img: Image.Image):
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)
        color   = (255, 255, 255, 12)
        # vertical lines
        for x in range(0, W, 80):
            draw.line([(x, 0), (x, H)], fill=color, width=1)
        # horizontal lines
        for y in range(0, H, 80):
            draw.line([(0, y), (W, y)], fill=color, width=1)
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _draw_glow_accent(self, img: Image.Image, category: str):
        palette = PALETTES.get(category, PALETTES["default"])
        accent  = self._hex(palette[2])
        glow    = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(glow)
        # large soft ellipse top-right
        draw.ellipse(
            [W - 500, -200, W + 200, 400],
            fill=(accent[0], accent[1], accent[2], 35)
        )
        # smaller sharp ellipse bottom-left
        draw.ellipse(
            [-100, H - 300, 400, H + 100],
            fill=(accent[0], accent[1], accent[2], 25)
        )
        blurred = glow.filter(ImageFilter.GaussianBlur(radius=80))
        img.paste(
            Image.alpha_composite(img.convert("RGBA"), blurred).convert("RGB")
        )

    # ── Design elements ────────────────────────────────────────────────────────
    def _draw_left_bar(self, img: Image.Image, category: str):
        palette = PALETTES.get(category, PALETTES["default"])
        accent  = self._hex(palette[2])
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)
        # vertical accent bar on left edge
        draw.rectangle([0, 0, 8, H], fill=(accent[0], accent[1], accent[2], 255))
        # subtle left panel background
        draw.rectangle(
            [0, 0, 30, H],
            fill=(accent[0], accent[1], accent[2], 30)
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _draw_stat_block(self, img: Image.Image, stat: str, category: str):
        if not stat:
            return
        palette = PALETTES.get(category, PALETTES["default"])
        accent  = self._hex(palette[2])
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        # stat background pill — right side
        bx1, by1, bx2, by2 = W - 420, 60, W - 40, 260
        draw.rounded_rectangle(
            [bx1, by1, bx2, by2],
            radius=20,
            fill=(accent[0], accent[1], accent[2], 35),
            outline=(accent[0], accent[1], accent[2], 180),
            width=3,
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

        draw2 = ImageDraw.Draw(img)
        # stat number
        stat_font = self._font(160 if len(stat) <= 4 else 110)
        bx_center = (bx1 + bx2) // 2
        by_center = (by1 + by2) // 2 - 10
        draw2.text(
            (bx_center, by_center),
            stat,
            font=stat_font,
            fill=self._hex_str(palette[2]),
            anchor="mm",
            stroke_width=3,
            stroke_fill="#000000",
        )

    def _draw_title(self, img: Image.Image, title: str):
        draw = ImageDraw.Draw(img)
        lines = textwrap.wrap(title.upper(), width=22)
        lines = lines[:3]  # max 3 lines

        y_start = 320
        line_gap = 10

        # measure total block height
        sizes = []
        for line in lines:
            sz = 72 if len(line) <= 18 else 58 if len(line) <= 22 else 48
            sizes.append(sz)

        total_h = sum(sizes) + line_gap * (len(lines) - 1)
        y = y_start - total_h // 2 + 80   # vertically center in lower half

        for i, line in enumerate(lines):
            font = self._font(sizes[i], bold=True)
            # shadow
            draw.text((62, y + 4), line, font=font, fill=(0, 0, 0, 180), anchor="lm")
            # main text
            draw.text(
                (60, y),
                line,
                font=font,
                fill="#FFFFFF",
                anchor="lm",
                stroke_width=2,
                stroke_fill="#000000",
            )
            y += sizes[i] + line_gap

    def _draw_data_bar(self, img: Image.Image):
        """Horizontal data/progress bar — visual credibility element."""
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        bar_y = H - 90
        # background track
        draw.rectangle([60, bar_y, W - 60, bar_y + 6],
                       fill=(255, 255, 255, 25))
        # filled portion — random 60-90% for visual effect
        fill_w = int((W - 120) * random.uniform(0.60, 0.90))
        draw.rectangle([60, bar_y, 60 + fill_w, bar_y + 6],
                       fill=(255, 255, 255, 140))
        # glowing dot at progress end
        dot_x = 60 + fill_w
        draw.ellipse([dot_x - 7, bar_y - 5, dot_x + 7, bar_y + 11],
                     fill=(255, 255, 255, 230))

        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _draw_brand(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        # brand name — bottom left
        draw.text(
            (60, H - 55),
            BRAND_NAME,
            font=self._font(28, bold=True),
            fill="#FFFFFF",
            anchor="lm",
        )
        # motto — next to brand
        draw.text(
            (200, H - 55),
            f"— {BRAND_MOTTO}",
            font=self._font(20),
            fill=(255, 255, 255, 160),
            anchor="lm",
        )
        # top-left small label
        draw.text(
            (60, 38),
            "EV DATA",
            font=self._font(18, bold=True),
            fill=(255, 255, 255, 180),
            anchor="lm",
        )

    def _draw_corner_badge(self, img: Image.Image, category: str):
        """Small category badge top-right corner."""
        label_map = {
            "battery":        "BATTERY",
            "range":          "RANGE TEST",
            "charging":       "CHARGING",
            "ownership":      "COST",
            "comparison":     "COMPARE",
            "market":         "MARKET",
            "infrastructure": "INFRA",
            "education":      "EXPLAINED",
            "tools":          "DATA TOOL",
        }
        label = label_map.get(category, "EV DATA")

        palette = PALETTES.get(category, PALETTES["default"])
        accent  = self._hex(palette[2])

        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)
        font    = self._font(20, bold=True)

        bbox    = draw.textbbox((0, 0), label, font=font)
        text_w  = bbox[2] - bbox[0]
        pad     = 14
        rx1     = W - text_w - pad * 2 - 50
        ry1     = 30
        rx2     = W - 50
        ry2     = 70

        draw.rounded_rectangle(
            [rx1, ry1, rx2, ry2],
            radius=8,
            fill=(accent[0], accent[1], accent[2], 200),
        )
        draw.text(
            ((rx1 + rx2) // 2, (ry1 + ry2) // 2),
            label,
            font=font,
            fill="#000000",
            anchor="mm",
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    # ── Font helper ────────────────────────────────────────────────────────────
    def _font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        key = (size, bold)
        if key in self._font_cache:
            return self._font_cache[key]

        # Try system fonts in order of preference
        candidates = []
        if bold:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "C:/Windows/Fonts/arialbd.ttf",
            ]
        else:
            candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "C:/Windows/Fonts/arial.ttf",
            ]

        font = None
        for path in candidates:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except Exception:
                    continue

        if font is None:
            font = ImageFont.load_default()

        self._font_cache[key] = font
        return font

    # ── Color helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _hex(h: str) -> tuple:
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _hex_str(h: str) -> str:
        return h if h.startswith("#") else f"#{h}"


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
