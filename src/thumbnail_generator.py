import os
import re
import random
import hashlib
import requests
import logging
import textwrap
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter

logger = logging.getLogger("ThumbnailGenerator")

ACCENT_COLORS = {
    "electric_vehicle":        "#00D4FF",
    "artificial_intelligence": "#9B5DE5",
    "robotics":                "#00F5A0",
    "battery_tech":            "#FF6B35",
    "future_tech":             "#F72585",
    "default":                 "#00D4FF",
}

# Multiple query variations per topic — picked randomly for visual diversity
TOPIC_QUERIES = {
    "electric_vehicle": [
        "electric car charging station night",
        "tesla electric vehicle highway",
        "electric car futuristic city",
        "ev sports car road",
        "electric vehicle technology interior",
    ],
    "artificial_intelligence": [
        "artificial intelligence neural network",
        "machine learning data visualization",
        "futuristic computer interface",
        "ai robot technology lab",
        "digital brain technology",
    ],
    "robotics": [
        "industrial robot arm factory",
        "humanoid robot technology",
        "autonomous vehicle sensor",
        "factory automation machinery",
        "robotic engineering lab",
    ],
    "battery_tech": [
        "electric battery cell close up",
        "lithium battery energy storage",
        "solar energy charging technology",
        "energy storage facility",
        "battery factory production",
    ],
    "future_tech": [
        "smart city night aerial",
        "futuristic transportation concept",
        "space technology innovation",
        "hyperloop concept design",
        "autonomous drone fleet",
    ],
    "default": [
        "electric vehicle road sunset",
        "ev charging modern city",
        "electric car technology",
    ],
}

FONT_BOLD   = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
for p in [FONT_BOLD, FONT_REGULAR]:
    if not os.path.exists(p):
        FONT_BOLD = FONT_REGULAR = None
        break


class ThumbnailGenerator:
    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self._used_photo_ids: set = set()  # prevent same image across videos

    def create(self, title: str, topic: str = "default", stat: str = "",
               category: str = "default", output_path: str = "thumbnail.jpg",
               is_short: bool = False) -> str:
        W, H = (1080, 1920) if is_short else (1280, 720)
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        topic_key = topic.lower().replace(" ", "_")
        accent    = ACCENT_COLORS.get(topic_key, ACCENT_COLORS["default"])

        # ── 1. Background: real Pexels photo, unique per video ───────────────
        bg = self._fetch_unique_pexels(topic_key, title, W, H)
        if bg is None:
            bg = self._gradient_fallback(W, H, accent)

        # ── 2. Dark overlay for text zone ────────────────────────────────────
        bg = self._text_overlay(bg, W, H)

        # ── 3. Draw all elements ─────────────────────────────────────────────
        draw = ImageDraw.Draw(bg)
        self._draw_category_badge(draw, topic_key, accent, W, H)
        self._draw_title_safe(draw, title, accent, W, H)
        self._draw_brand_bar(draw, accent, W, H)

        bg.save(output_path, "JPEG", quality=93)
        logger.info(f"[Thumbnail] ✅ {output_path}")
        return output_path

    # ── Background helpers ────────────────────────────────────────────────────

    def _fetch_unique_pexels(self, topic_key: str, title: str, W: int, H: int):
        if not self.pexels_key:
            return None

        queries = TOPIC_QUERIES.get(topic_key, TOPIC_QUERIES["default"])
        # Use title hash to deterministically pick a different query each time
        h = int(hashlib.md5(title.encode()).hexdigest(), 16)
        query = queries[h % len(queries)]
        # Random page (1-5) for visual diversity
        page  = (h % 5) + 1
        orient = "portrait" if H > W else "landscape"

        try:
            url = (f"https://api.pexels.com/v1/search"
                   f"?query={requests.utils.quote(query)}"
                   f"&per_page=10&page={page}&orientation={orient}")
            r = requests.get(url, headers={"Authorization": self.pexels_key}, timeout=12)
            photos = r.json().get("photos", [])
            if not photos:
                return None

            # Skip already-used photos
            for photo in photos:
                pid = photo["id"]
                if pid not in self._used_photo_ids:
                    self._used_photo_ids.add(pid)
                    img_url = photo["src"]["large2x"] if H <= W else photo["src"]["large"]
                    img_data = requests.get(img_url, timeout=20).content
                    img = Image.open(BytesIO(img_data)).convert("RGB")
                    return self._center_crop(img, W, H)

            # All used — just pick first anyway
            img_url = photos[0]["src"]["large2x"]
            img_data = requests.get(img_url, timeout=20).content
            return self._center_crop(Image.open(BytesIO(img_data)).convert("RGB"), W, H)

        except Exception as e:
            logger.warning(f"[Thumbnail] Pexels failed: {e}")
            return None

    def _center_crop(self, img: Image.Image, W: int, H: int) -> Image.Image:
        iw, ih = img.size
        if iw / ih > W / H:
            nw = int(ih * W / H)
            img = img.crop(((iw - nw) // 2, 0, (iw + nw) // 2, ih))
        else:
            nh = int(iw * H / W)
            img = img.crop((0, (ih - nh) // 2, iw, (ih + nh) // 2))
        return img.resize((W, H), Image.LANCZOS)

    def _gradient_fallback(self, W: int, H: int, accent: str) -> Image.Image:
        img  = Image.new("RGB", (W, H), (8, 8, 20))
        draw = ImageDraw.Draw(img)
        ar   = int(accent[1:3], 16)
        ag   = int(accent[3:5], 16)
        ab   = int(accent[5:7], 16)
        for y in range(H):
            t = y / H
            draw.line([(0, y), (W, y)],
                      fill=(min(int(8 + ar*t*0.25), 255),
                            min(int(8 + ag*t*0.25), 255),
                            min(int(20 + ab*t*0.35), 255)))
        return img

    def _text_overlay(self, img: Image.Image, W: int, H: int) -> Image.Image:
        """Dark vignette on bottom 55% so text is always readable."""
        ov   = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(ov)
        zone = int(H * 0.42)
        for y in range(zone, H):
            a = int(215 * (y - zone) / (H - zone))
            draw.line([(0, y), (W, y)], fill=(0, 0, 12, a))
        result = Image.alpha_composite(img.convert("RGBA"), ov)
        return result.convert("RGB")

    # ── Drawing helpers ────────────────────────────────────────────────────

    def _get_font(self, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
        path = FONT_BOLD if bold else FONT_REGULAR
        try:
            if path and os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass
        return ImageFont.load_default()

    def _draw_title_safe(self, draw: ImageDraw.Draw, title: str,
                          accent: str, W: int, H: int):
        """Draw title with guaranteed no overflow — shrinks font until it fits."""
        clean = re.sub(r"[^\w\s\-:,.!?%$+]", "", title).upper().strip()

        PADDING   = int(W * 0.06)          # 6% side padding
        max_w     = W - 2 * PADDING
        font_size = int(W * 0.075)         # start size
        wrap_w    = 18

        # Shrink font & wrap until all lines fit within max_w
        while font_size > 28:
            font  = self._get_font(font_size)
            lines = textwrap.wrap(clean, width=wrap_w)[:4]
            fits  = all(
                draw.textlength(line, font=font) <= max_w
                for line in lines
            )
            if fits:
                break
            font_size -= 4
            wrap_w    += 2

        font     = self._get_font(font_size)
        lines    = textwrap.wrap(clean, width=wrap_w)[:4]
        line_h   = font_size + int(font_size * 0.25)
        total_h  = len(lines) * line_h
        y_start  = H - total_h - int(H * 0.14)   # safe bottom margin

        ar = int(accent[1:3], 16)
        ag = int(accent[3:5], 16)
        ab = int(accent[5:7], 16)

        for i, line in enumerate(lines):
            y  = y_start + i * line_h
            tw = draw.textlength(line, font=font)
            x  = (W - tw) / 2

            # Drop shadow
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 180))
            # Subtle glow
            for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
                draw.text((x + ox, y + oy), line, font=font,
                          fill=(ar // 3, ag // 3, ab // 3))
            # Main white text
            draw.text((x, y), line, font=font, fill=(255, 255, 255))

        # Accent underline under last line
        y_ul = y_start + total_h + 6
        uw   = min(int(tw * 0.9), max_w)
        draw.rectangle([(W - uw) // 2, y_ul, (W + uw) // 2, y_ul + 5], fill=accent)

    def _draw_category_badge(self, draw: ImageDraw.Draw, topic_key: str,
                              accent: str, W: int, H: int):
        """Small colored badge top-right, e.g. 'BATTERY TECH'."""
        label_map = {
            "electric_vehicle": "EV MARKET",
            "artificial_intelligence": "AI × EV",
            "robotics": "ROBOTICS",
            "battery_tech": "BATTERY TECH",
            "future_tech": "FUTURE TECH",
            "default": "EV DATA",
        }
        label    = label_map.get(topic_key, "EV DATA")
        font     = self._get_font(int(W * 0.030), bold=True)
        tw       = draw.textlength(label, font=font)
        pad      = 14
        bx2      = W - 24
        bx1      = bx2 - tw - pad * 2
        by1, by2 = 20, 56

        ar = int(accent[1:3], 16)
        ag = int(accent[3:5], 16)
        ab = int(accent[5:7], 16)

        # Semi-transparent pill background
        pill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pd   = ImageDraw.Draw(pill)
        pd.rounded_rectangle([bx1, by1, bx2, by2], radius=8,
                              fill=(ar, ag, ab, 200))
        draw._image.paste(Image.alpha_composite(draw._image.convert("RGBA"), pill).convert("RGB"))
        draw = ImageDraw.Draw(draw._image)

        draw.text((bx1 + pad, by1 + 8), label, font=font, fill="white")
        return draw

    def _draw_brand_bar(self, draw: ImageDraw.Draw, accent: str, W: int, H: int):
        """Bottom brand strip: ⚡ EVCARIX + tagline."""
        font_brand = self._get_font(int(W * 0.038), bold=True)
        font_tag   = self._get_font(int(W * 0.026), bold=False)

        # Dark pill
        bw = int(W * 0.38)
        bx1 = (W - bw) // 2
        bx2 = bx1 + bw
        by1 = H - int(H * 0.115)
        by2 = H - int(H * 0.025)

        draw.rectangle([bx1 - 2, by1 - 2, bx2 + 2, by2 + 2],
                       fill=(0, 0, 0))
        draw.rectangle([bx1, by1, bx2, by2], fill=(15, 15, 30))

        # Accent top border
        draw.rectangle([bx1, by1, bx2, by1 + 3], fill=accent)

        cx = W // 2
        draw.text((cx, by1 + 14), "EVCARIX", font=font_brand,
                  fill=accent, anchor="mt")
        draw.text((cx, by1 + 14 + int(W * 0.042)), "EV DATA & INSIGHTS",
                  font=font_tag, fill=(200, 200, 200), anchor="mt")
