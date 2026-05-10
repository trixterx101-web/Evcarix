"""
Evcarix Thumbnail Generator v10.0
Generates a professional 1280x720 YouTube thumbnail for long-form videos.

Design philosophy (matching reference images):
  - Real EV/car photo from Pexels as background (NO empty background)
  - Dark cinematic vignette overlay for text readability
  - Large IMPACT-style bold title text (white / highlighted)
  - Stat badge (red/yellow) — e.g. "50% RANGE LOST"
  - Optional mini data graph
  - EVCARIX brand tag bottom-right

Usage:
    from src.thumbnail_generator import ThumbnailGenerator
    gen = ThumbnailGenerator()
    path = gen.create(title="50% Range Lost in Winter?", stat="-50%", category="range")
"""

import os
import re
import io
import math
import random
import textwrap
import logging
import requests
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
except ImportError:
    raise ImportError("pip install Pillow")

logger = logging.getLogger("ThumbnailGen")

# ── Constants ──────────────────────────────────────────────────────────────────
W_LONG,  H_LONG  = 1280, 720
W_SHORT, H_SHORT = 1080, 1920
ASSETS_DIR = Path("assets")
OUT_DIR    = Path("output")

# Category → Pexels search keywords for background photo
CATEGORY_PEXELS_QUERY = {
    "battery":        ["electric car battery pack technology", "EV battery cells", "lithium battery"],
    "range":          ["electric car driving highway", "EV range winter", "Tesla driving road"],
    "charging":       ["electric car charging station", "EV supercharger night", "charging plug EV"],
    "ownership":      ["electric car owner happy", "EV long trip", "Tesla parking"],
    "comparison":     ["two electric cars side by side", "EV comparison road", "BMW vs Tesla"],
    "market":         ["electric vehicle traffic city", "EV market cars street", "multiple electric cars"],
    "infrastructure": ["charging network stations", "EV infrastructure road", "charging hub airport"],
    "education":      ["electric car technology", "EV motor cutaway", "car technology dashboard"],
    "tools":          ["car dashboard data", "EV software digital", "automotive technology screen"],
    "default":        ["electric vehicle cinematic", "EV car road", "Tesla Model exterior"],
}

# Category color accent (for badge & highlights)
CATEGORY_ACCENT = {
    "battery":        "#00D4FF",
    "range":          "#FF3131",
    "charging":       "#FF6B00",
    "ownership":      "#7FFF00",
    "comparison":     "#BF00FF",
    "market":         "#FFD700",
    "infrastructure": "#00FFFF",
    "education":      "#4488FF",
    "tools":          "#FF0066",
    "default":        "#FFD700",
}

BRAND_NAME  = "EVCARIX"
BRAND_MOTTO = "No Hype. Just Numbers."


class ThumbnailGenerator:

    def __init__(self):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self._font_cache = {}
        self._pexels_key = os.getenv("PEXELS_API_KEY", "")

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────────
    def create(
        self,
        title: str,
        stat: str = "",
        category: str = "default",
        output_path: str = "",
        bg_image_path: str = None,
        is_short: bool = False,
        is_comparison: bool = False,
    ) -> str:
        """
        v10.0 — Real photo background + professional text overlay.
        Only generates thumbnails for long-form videos (is_short=False).
        For Shorts, returns None immediately (Shorts don't need thumbnails).
        """
        if is_short:
            # Shorts'ta thumbnail üretme — YouTube otomatik oluşturur
            return None

        width, height = W_LONG, H_LONG

        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(OUT_DIR / f"thumbnail_{ts}.jpg")
        # PNG → JPG dönüşümü
        if output_path.lower().endswith(".png"):
            output_path = output_path.rsplit(".", 1)[0] + ".jpg"

        # 1. Arka plan görseli al
        bg = self._get_background(category, width, height, bg_image_path)

        # 2. Sinematik karartma katmanı
        bg = self._apply_vignette(bg)

        # 3. Karşılaştırma çizgisi
        if is_comparison:
            self._draw_split_line(bg)

        # 4. Ana başlık
        self._draw_title(bg, title, is_comparison)

        # 5. Stat rozeti
        if stat:
            self._draw_stat_badge(bg, stat, category)

        # 6. Mini data grafiği (%60 olasılıkla)
        if random.random() > 0.4:
            self._draw_mini_graph(bg, category)

        # 7. Marka etiketi
        self._draw_brand_tag(bg)

        # 8. Kaydet
        bg.save(output_path, "JPEG", quality=93, optimize=True)
        logger.info(f"[Thumbnail] ✅ Kaydedildi: {output_path}")
        return output_path

    # ─────────────────────────────────────────────────────────────────────────
    # BACKGROUND: Pexels → Local file → Gradient fallback
    # ─────────────────────────────────────────────────────────────────────────
    def _get_background(self, category: str, width: int, height: int,
                         bg_image_path: str = None) -> Image.Image:
        """
        Priority:
          1. Explicitly provided local file
          2. Pexels API (real EV/car photo)
          3. Premium dark gradient fallback
        """
        # 1. Yerel dosya verilmişse kullan
        if bg_image_path and os.path.exists(bg_image_path):
            try:
                img = Image.open(bg_image_path).convert("RGB")
                return self._fill_crop(img, width, height)
            except Exception as e:
                logger.warning(f"[Thumbnail] Yerel BG açılamadı: {e}")

        # 2. Pexels'tan gerçek EV fotoğrafı çek
        if self._pexels_key:
            queries = CATEGORY_PEXELS_QUERY.get(category, CATEGORY_PEXELS_QUERY["default"])
            random.shuffle(queries)
            for q in queries:
                img = self._fetch_pexels_photo(q, width, height)
                if img:
                    logger.info(f"[Thumbnail] ✅ Pexels arka plan: '{q}'")
                    return img

        # 3. Premium gradient fallback
        logger.warning("[Thumbnail] ⚠️ Pexels başarısız, gradient arka plan kullanılıyor.")
        return self._make_gradient_bg(width, height, category)

    def _fetch_pexels_photo(self, query: str, width: int, height: int) -> Image.Image | None:
        """Pexels Photos API'den yatay/yüksek çözünürlüklü fotoğraf çek."""
        try:
            url = (
                f"https://api.pexels.com/v1/search"
                f"?query={requests.utils.quote(query)}"
                f"&per_page=15&orientation=landscape"
            )
            r = requests.get(url, headers={"Authorization": self._pexels_key}, timeout=15)
            if r.status_code != 200:
                return None

            photos = r.json().get("photos", [])
            if not photos:
                return None

            # Yüksek kalite fotoğraf seç — büyük boyutu tercih et
            random.shuffle(photos)
            for photo in photos[:8]:
                src = photo.get("src", {})
                img_url = src.get("large2x") or src.get("large") or src.get("original")
                if not img_url:
                    continue
                ir = requests.get(img_url, timeout=20)
                if ir.status_code == 200:
                    img = Image.open(io.BytesIO(ir.content)).convert("RGB")
                    return self._fill_crop(img, width, height)
        except Exception as e:
            logger.warning(f"[Thumbnail] Pexels photo hatası: {e}")
        return None

    def _fill_crop(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Cover-style: resmi hedef boyuta kırp (en-boy oranını bozmadan)."""
        iw, ih = img.size
        scale = max(width / iw, height / ih)
        new_w, new_h = int(iw * scale), int(ih * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        x = (new_w - width) // 2
        y = (new_h - height) // 2
        return img.crop((x, y, x + width, y + height))

    def _make_gradient_bg(self, width: int, height: int, category: str) -> Image.Image:
        """Koyu sinematik gradient arka plan (Pexels başarısız olduğunda)."""
        # Kategori rengi
        accent_hex = CATEGORY_ACCENT.get(category, "#FFD700")
        ax = int(accent_hex[1:3], 16)
        ay = int(accent_hex[3:5], 16)
        az = int(accent_hex[5:7], 16)

        img = Image.new("RGB", (width, height))
        pixels = img.load()
        for y in range(height):
            t = y / height
            r = int(8  + (ax * 0.15) * t)
            g = int(8  + (ay * 0.10) * t)
            b = int(20 + (az * 0.20) * t)
            for x in range(width):
                # Kenarlarda vignette efekti
                vx = 1.0 - 0.3 * abs(x / width - 0.5) * 2
                pixels[x, y] = (
                    max(0, min(255, int(r * vx))),
                    max(0, min(255, int(g * vx))),
                    max(0, min(255, int(b * vx))),
                )
        return img

    # ─────────────────────────────────────────────────────────────────────────
    # OVERLAYS
    # ─────────────────────────────────────────────────────────────────────────
    def _apply_vignette(self, img: Image.Image) -> Image.Image:
        """
        Sinematik vignette: alt %40 ve üst %20'ye koyu gradient uygular.
        Metin okunurluğunu dramatik biçimde artırır.
        """
        w, h = img.size
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Alt gradient (ana metin alanı)
        fade_start = int(h * 0.45)
        for y in range(fade_start, h):
            alpha = int(210 * ((y - fade_start) / (h - fade_start)) ** 0.8)
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        # Üst gradient (başlık alanı)
        for y in range(int(h * 0.30)):
            alpha = int(160 * (1 - y / (h * 0.30)) ** 1.2)
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        # Sol kenar gradient (derinlik)
        for x in range(int(w * 0.15)):
            alpha = int(80 * (1 - x / (w * 0.15)))
            draw.line([(x, 0), (x, h)], fill=(0, 0, 0, alpha))

        result = Image.alpha_composite(img.convert("RGBA"), overlay)
        return result.convert("RGB")

    def _draw_split_line(self, img: Image.Image):
        draw = ImageDraw.Draw(img)
        w, h = img.size
        # Altın dikey bölme çizgisi
        for offset in [-2, 0, 2]:
            draw.line([(w // 2 + offset, 0), (w // 2 + offset, h)],
                      fill=(255, 215, 0, 180), width=2)
        draw.line([(w // 2, 0), (w // 2, h)], fill="#FFD700", width=4)

    def _draw_title(self, img: Image.Image, title: str, is_comparison: bool):
        """
        Büyük, vurgulu başlık — referans görsellere benzer Impact stili.
        Üst sol/sağ konumda, koyu kutu arka planlı.
        """
        draw = ImageDraw.Draw(img)
        w, h = img.size
        title_upper = title.upper()

        # Karakter sayısına göre font boyutu
        if len(title_upper) <= 18:
            font_size = 105
        elif len(title_upper) <= 30:
            font_size = 85
        else:
            font_size = 68

        font = self._font(font_size, bold=True)
        max_chars = 16 if is_comparison else 22
        lines = textwrap.wrap(title_upper, width=max_chars)[:3]  # Max 3 satır

        y = 45
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            # Koyu vurgulu arka plan kutusu (highlight efekti)
            pad_x, pad_y = 18, 10
            # İlk satır sarı, diğerleri beyaz
            box_color = (255, 215, 0, 230) if i == 0 else (0, 0, 0, 200)
            text_color = "#000000" if i == 0 else "#FFFFFF"

            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            ov_draw.rectangle(
                [50 - pad_x, y - pad_y, 50 + tw + pad_x, y + th + pad_y],
                fill=box_color
            )
            img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
            draw = ImageDraw.Draw(img)  # Yeniden al

            # Metin
            draw.text((50, y), line, font=font, fill=text_color)
            y += th + pad_y * 2 + 8

    def _draw_stat_badge(self, img: Image.Image, stat: str, category: str):
        """
        Büyük, dikkat çekici stat rozeti — sol alt köşe.
        Örnek: '-45%', '50% RANGE LOST!', '800V'
        """
        draw = ImageDraw.Draw(img)
        w, h = img.size

        # Rozetin içine yazacak metin
        stat_upper = stat.upper()

        font_size = 90 if len(stat_upper) <= 6 else 68
        font = self._font(font_size, bold=True)

        bbox = draw.textbbox((0, 0), stat_upper, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        bx = 50
        by = h - th - 100
        pad = 22

        # Glow shadow (derinlik)
        shadow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh_draw = ImageDraw.Draw(shadow_layer)
        sh_draw.rectangle(
            [bx - 8, by - 8, bx + tw + pad * 2 + 8, by + th + pad * 2 + 8],
            fill=(0, 0, 0, 120)
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), shadow_layer).convert("RGB"))
        draw = ImageDraw.Draw(img)

        # Ana rozet rengi — negatif değerler kırmızı, pozitifler sarı/yeşil
        accent = CATEGORY_ACCENT.get(category, "#FFD700")
        if any(c in stat_upper for c in ["-", "LOST", "DROPS", "FAIL", "DEAD"]):
            badge_color = "#FF1A1A"
            text_color  = "#FFFFFF"
        elif any(c in stat_upper for c in ["+", "GAIN", "SAVE", "BEST", "WIN"]):
            badge_color = "#00CC44"
            text_color  = "#000000"
        else:
            badge_color = "#FFD700"
            text_color  = "#000000"

        draw.rectangle(
            [bx, by, bx + tw + pad * 2, by + th + pad * 2],
            fill=badge_color
        )

        # Metin (kalın kenarlı efekt için gölge)
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            shadow_c = "#000000" if text_color == "#FFFFFF" else "#888888"
            draw.text((bx + pad + dx, by + pad // 2 + dy), stat_upper, font=font, fill=shadow_c)
        draw.text((bx + pad, by + pad // 2), stat_upper, font=font, fill=text_color)

    def _draw_mini_graph(self, img: Image.Image, category: str):
        """Sağ alt köşede küçük veri grafiği — veri kanalı estetiği."""
        w, h = img.size
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        gx, gy = w - 320, h - 200
        gw, gh = 280, 120

        # Arkaplan panel
        draw.rectangle([gx - 10, gy - 15, gx + gw + 10, gy + gh + 15],
                       fill=(0, 0, 0, 160))

        # Eksen çizgileri
        draw.line([(gx, gy + gh), (gx + gw, gy + gh)], fill=(255, 255, 255, 80), width=1)
        draw.line([(gx, gy), (gx, gy + gh)],          fill=(255, 255, 255, 80), width=1)

        # Rastgele ama anlamlı görünen veri noktaları (azalan trend — EV range loss vb.)
        accent_hex = CATEGORY_ACCENT.get(category, "#FFD700")
        num_points = 7
        # Trend: sağa doğru düşen veya yükselen (yarı yarıya)
        going_down = random.random() > 0.5
        base = gh * 0.2 if going_down else gh * 0.8
        points = []
        for i in range(num_points):
            noise = random.randint(-15, 15)
            if going_down:
                yval = base + (gh * 0.6 * i / (num_points - 1)) + noise
            else:
                yval = base - (gh * 0.6 * i / (num_points - 1)) + noise
            yval = max(5, min(gh - 5, yval))
            points.append((gx + int(i * gw / (num_points - 1)), int(gy + yval)))

        # Gölge çizgi
        for dx, dy in [(0, 2)]:
            shadow_pts = [(p[0] + dx, p[1] + dy) for p in points]
            draw.line(shadow_pts, fill=(0, 0, 0, 120), width=5)
        # Renkli veri çizgisi
        draw.line(points, fill=accent_hex, width=4)

        # Son noktaya daire işareti
        lx, ly = points[-1]
        draw.ellipse([lx - 6, ly - 6, lx + 6, ly + 6], fill=accent_hex, outline="white", width=2)

        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _draw_brand_tag(self, img: Image.Image):
        """Sağ alt köşe: EVCARIX marka watermark."""
        draw = ImageDraw.Draw(img)
        w, h = img.size

        font_b = self._font(22, bold=True)
        font_s = self._font(14, bold=False)

        # Yarı saydam arka plan panel
        panel_w = 200
        panel_h = 46
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        ov_draw.rectangle(
            [w - panel_w - 10, h - panel_h - 10, w - 5, h - 5],
            fill=(0, 0, 0, 160)
        )
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
        draw = ImageDraw.Draw(img)

        draw.text((w - panel_w, h - panel_h + 2),  BRAND_NAME,  font=font_b, fill="#FFFFFF")
        draw.text((w - panel_w, h - panel_h + 26), BRAND_MOTTO, font=font_s, fill="#FFD700")

    # ─────────────────────────────────────────────────────────────────────────
    # FONT LOADER
    # ─────────────────────────────────────────────────────────────────────────
    def _font(self, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        key = (size, bold)
        if key in self._font_cache:
            return self._font_cache[key]

        # Impact en yüksek öncelik (YouTube thumbnail standarı)
        bold_candidates = [
            "C:/Windows/Fonts/impact.ttf",          # Windows Impact
            "C:/Windows/Fonts/ariblk.ttf",           # Arial Black
            "C:/Windows/Fonts/arialbd.ttf",           # Arial Bold
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            # Ubuntu GitHub Actions
            "/usr/share/fonts/truetype/fonts-liberation/LiberationSans-Bold.ttf",
            # fonts-dejavu-core (GitHub Actions APT paketi)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        regular_candidates = [
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]

        candidates = bold_candidates if bold else regular_candidates
        font = None
        for path in candidates:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except Exception:
                    continue

        if not font:
            font = ImageFont.load_default()
            logger.warning(f"[Thumbnail] Font bulunamadı, varsayılan kullanılıyor (size={size})")

        self._font_cache[key] = font
        return font


# ── Standalone test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gen = ThumbnailGenerator()
    tests = [
        ("50% Range Lost in Winter? Real Data From 70 EVs", "-50%",   "range"),
        ("Fast Charging KILLS Battery? 500,000km Proof",    "500K",   "battery"),
        ("800V vs 400V: The Real Difference Nobody Shows",  "800V",   "charging"),
        ("EV vs Diesel: 5-Year True Cost Breakdown",        "5YR",    "ownership"),
        ("LFP Batteries: 1 Million KM Reality Check",       "1M KM",  "battery"),
    ]
    for title, stat, cat in tests:
        path = gen.create(title=title, stat=stat, category=cat)
        print(f"  → {path}")
