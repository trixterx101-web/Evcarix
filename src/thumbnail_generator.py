import os
import re
import random
import hashlib
import logging
import textwrap
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("ThumbnailGenerator")

BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

def _fnt(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    try:
        path = BOLD if bold else REGULAR
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    return ImageFont.load_default()

# ── Topic config ──────────────────────────────────────────────────────────────
TOPIC_CONFIG = {
    "electric_vehicle": {
        "style":         "A",
        "keyword_color": (220, 30, 30),
        "bg_dark":       (8, 5, 5),
        "accent":        (0, 212, 255),
        "badge":         "⚡ R.I.P.",
        "lines_a":       ["GAS CARS", "ARE DEAD"],
        "sub_a":         "EV Tech Proved It",
        "badge_b":       "SHOCKING",
        "the_b":         "THE",
        "stats": [
            ("+300%", "EV SALES GROWTH",      (0, 212, 255)),
            ("$0",    "GAS CAR FUTURE VALUE",  (255, 180, 0)),
            ("500mi", "NEW EV RANGE RECORD",   (0, 255, 140)),
        ],
    },
    "battery_tech": {
        "style":         "B",
        "keyword_color": (255, 107, 0),
        "bg_dark":       (15, 6, 0),
        "accent":        (255, 107, 0),
        "badge":         "🔋 DATA",
        "lines_a":       ["BATTERY", "BREAKS"],
        "sub_a":         "Solid State Changes Everything",
        "badge_b":       "SHOCKING",
        "the_b":         "THE",
        "stats": [
            ("1M KM",  "LFP LIFESPAN",         (255, 107, 0)),
            ("10 MIN", "FUTURE CHARGE TIME",    (0, 212, 255)),
            ("-45%",   "WINTER RANGE LOSS",     (0, 255, 140)),
        ],
    },
    "artificial_intelligence": {
        "style":         "B",
        "keyword_color": (139, 0, 255),
        "bg_dark":       (8, 0, 18),
        "accent":        (139, 0, 255),
        "badge":         "🤖 AI",
        "lines_a":       ["AI TAKES", "THE WHEEL"],
        "sub_a":         "Self-Driving 2026",
        "badge_b":       "SHOCKING",
        "the_b":         "THE",
        "stats": [
            ("10x",   "SPEED VS HUMAN",         (139, 0, 255)),
            ("2030",  "AGI PREDICTION",          (0, 212, 255)),
            ("$1T",   "AI MARKET SIZE",          (255, 180, 0)),
        ],
    },
    "robotics": {
        "style":         "A",
        "keyword_color": (0, 255, 136),
        "bg_dark":       (0, 10, 6),
        "accent":        (0, 255, 136),
        "badge":         "🦾 ROBOTS",
        "lines_a":       ["ROBOTS", "TAKE OVER"],
        "sub_a":         "Factory Automation 2026",
        "badge_b":       "SHOCKING",
        "the_b":         "THE",
        "stats": [
            ("40%",   "JOBS AUTOMATED",          (0, 255, 136)),
            ("$1.5T", "ROBOTICS MARKET",         (0, 212, 255)),
            ("24/7",  "ROBOT UPTIME",            (255, 180, 0)),
        ],
    },
    "future_tech": {
        "style":         "B",
        "keyword_color": (0, 212, 255),
        "bg_dark":       (4, 8, 28),
        "accent":        (0, 212, 255),
        "badge":         "⚡ SHOCKING",
        "lines_a":       ["THE FUTURE", "IS NOW"],
        "sub_a":         "Tech That Will Shock You",
        "badge_b":       "SHOCKING",
        "the_b":         "THE",
        "stats": [
            ("+300%", "EV SALES GROWTH",         (0, 212, 255)),
            ("$0",    "GAS CAR FUTURE VALUE",    (255, 180, 0)),
            ("500mi", "NEW EV RANGE RECORD",     (0, 255, 140)),
        ],
    },
    "default": {
        "style":         "B",
        "keyword_color": (0, 212, 255),
        "bg_dark":       (4, 8, 28),
        "accent":        (0, 212, 255),
        "badge":         "⚡ SHOCKING",
        "lines_a":       ["EV DATA", "REVEALED"],
        "sub_a":         "Facts That Will Shock You",
        "badge_b":       "SHOCKING",
        "the_b":         "THE",
        "stats": [
            ("+300%", "EV SALES GROWTH",         (0, 212, 255)),
            ("$0",    "GAS CAR FUTURE VALUE",    (255, 180, 0)),
            ("500mi", "NEW EV RANGE RECORD",     (0, 255, 140)),
        ],
    },
}


def _title_to_main_lines(title: str) -> tuple[str, str, str]:
    """Split title into (line1, line2, subtitle) for style B."""
    clean = re.sub(r"[^\w\s\-:]", "", title).upper().strip()
    words = clean.split()
    if len(words) <= 2:
        return words[0] if words else "EV", words[1] if len(words) > 1 else "DATA", ""
    # First 1-2 words → line1, next 1-2 → line2, rest → subtitle
    mid   = max(1, len(words) // 3)
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:mid*2])
    sub   = " ".join(words[mid*2:])
    return line1, line2, sub


def _title_to_a_lines(title: str, defaults: list) -> tuple[str, str, str]:
    """Split title into (big_word, line2, sub) for style A."""
    clean = re.sub(r"[^\w\s]", "", title).upper().strip()
    words = clean.split()
    if not words:
        return defaults[0], defaults[1], title
    if len(words) == 1:
        return words[0], "", ""
    line1 = words[0]
    line2 = " ".join(words[1:3])
    sub   = " ".join(words[3:7])
    return line1, line2, sub


# ── Style A ───────────────────────────────────────────────────────────────────
def _render_style_a(W: int, H: int, title: str, cfg: dict) -> Image.Image:
    kc  = cfg["keyword_color"]
    img = Image.new("RGB", (W, H), cfg["bg_dark"])
    draw = ImageDraw.Draw(img)

    # Diagonal grid
    for i in range(-H, W + H, 60):
        draw.line([(i, 0), (i + H, H)], fill=(255, 255, 255), width=1)

    # Redraw bg to overlay the grid faintly
    overlay = Image.new("RGB", (W, H), cfg["bg_dark"])
    img     = Image.blend(img, overlay, 0.82)
    draw    = ImageDraw.Draw(img)

    # Left accent bar
    draw.rectangle([0, 0, 18, H], fill=kc)

    # Top-left badge
    badge = cfg["badge"]
    bf    = _fnt(26)
    bw    = int(draw.textlength(badge, font=bf))
    draw.rectangle([22, 16, bw + 58, 54], fill=kc)
    draw.text((30, 20), badge, font=bf, fill=(0, 0, 0))

    # Top-right: "EV TECH ▶"
    rt  = "EV TECH ▶"
    rf  = _fnt(24)
    rtw = int(draw.textlength(rt, font=rf))
    draw.rectangle([W - rtw - 36, 16, W - 14, 54], fill=(0, 180, 220))
    draw.text((W - rtw - 20, 20), rt, font=rf, fill=(0, 0, 10))

    # Big lines from title
    defaults = cfg.get("lines_a", ["EV", "DATA"])
    line1, line2, sub = _title_to_a_lines(title, defaults)

    # Line1 — huge colored
    f1   = _fnt(int(H * 0.27))
    x_l  = 30
    y1   = int(H * 0.10)
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((x_l + ox, y1 + oy), line1, font=f1,
                  fill=(kc[0]//2, kc[1]//2, kc[2]//2))
    draw.text((x_l, y1), line1, font=f1, fill=kc)

    # Line2 — white large
    f2 = _fnt(int(H * 0.15))
    y2 = y1 + int(H * 0.30)
    draw.text((x_l, y2), line2, font=f2, fill=(255, 255, 255))

    # Sub — smaller muted
    if sub:
        f3 = _fnt(int(H * 0.068), bold=False)
        y3 = y2 + int(H * 0.19)
        draw.text((x_l, y3), sub[:42], font=f3, fill=(185, 185, 185))

    # Diagonal accent slashes top-right
    for i in range(7):
        draw.line([(W - 200 + i * 7, 0), (W, H // 2 - i * 18)],
                  fill=kc, width=3)

    # Bottom brand bar
    by = H - 52
    draw.rectangle([0, by, W, H], fill=(0, 0, 0))
    draw.rectangle([0, by, W, by + 3], fill=kc)
    draw.text((28, by + 12), "⚡ EVCARIX", font=_fnt(28), fill=kc)
    tag = "EV DATA & INSIGHTS"
    tw  = int(draw.textlength(tag, font=_fnt(20, False)))
    draw.text((W - tw - 20, by + 16), tag, font=_fnt(20, False), fill=(130, 145, 158))

    return img


# ── Style B ───────────────────────────────────────────────────────────────────
def _render_style_b(W: int, H: int, title: str, cfg: dict) -> Image.Image:
    ac  = cfg["accent"]
    ar, ag, ab = ac

    img  = Image.new("RGB", (W, H), cfg["bg_dark"])
    draw = ImageDraw.Draw(img)

    # Grid
    for x in range(0, W, 68):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255), width=1)
    for y in range(0, H, 68):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255), width=1)
    overlay = Image.new("RGB", (W, H), cfg["bg_dark"])
    img     = Image.blend(img, overlay, 0.88)
    draw    = ImageDraw.Draw(img)

    # Radial glow left-center
    for step in range(280, 0, -8):
        a   = int(55 * (1 - step / 280))
        col = (min(cfg["bg_dark"][0] + ar * a // 55, 255),
               min(cfg["bg_dark"][1] + ag * a // 55, 255),
               min(cfg["bg_dark"][2] + ab * a // 55, 255))
        draw.ellipse([160 - step, H//2 - step, 160 + step, H//2 + step], fill=col)

    # Top badge "⚡ SHOCKING | GAS CAR OWNERS MUST SEE THIS"
    sbf = _fnt(22)
    badge_label = f"⚡ {cfg['badge_b']}"
    sbw = int(draw.textlength(badge_label, font=sbf))
    draw.rectangle([14, 14, sbw + 44, 48], fill=(255, 90, 0))
    draw.text((22, 17), badge_label, font=sbf, fill=(255, 255, 255))
    draw.text((sbw + 54, 17), "GAS CAR OWNERS MUST SEE THIS",
              font=_fnt(19, False), fill=(210, 210, 210))

    # "THE" label
    the_label = cfg.get("the_b", "THE")
    draw.text((38, 68), the_label, font=_fnt(50), fill=(150, 195, 230))

    # Main title — split into 2 big lines
    line1, line2, sub = _title_to_main_lines(title)
    mf = _fnt(int(H * 0.21))
    y_m = 118
    for line in [line1, line2]:
        if not line:
            continue
        lw = int(draw.textlength(line, font=mf))
        for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
            draw.text((36 + ox, y_m + oy), line, font=mf,
                      fill=(ar//3, ag//3, ab//3))
        draw.text((36, y_m), line, font=mf, fill=ac)
        y_m += int(H * 0.235)

    # Sub / year line
    if sub:
        draw.text((42, y_m), sub[:30], font=_fnt(int(H * 0.075)), fill=(150, 205, 225))
        y_m += int(H * 0.09)

    # Tagline
    draw.text((42, y_m + 8), "⚡ THAT WILL SHOCK YOU",
              font=_fnt(26, False), fill=(255, 200, 0))

    # Vertical divider
    vx = W - 348
    draw.line([(vx, 20), (vx, H - 58)], fill=ac, width=2)

    # Right stat cards
    cx = vx + 18
    cy = 28
    cw = W - cx - 18
    for val, lbl, col in cfg.get("stats", []):
        cr, cg, cb = col
        draw.rectangle([cx, cy, cx + cw, cy + 92],
                       fill=(max(0,cr//9), max(0,cg//9), max(0,cb//9+8)))
        draw.rectangle([cx, cy, cx + 6, cy + 92], fill=col)
        draw.text((cx + 16, cy + 6),  val, font=_fnt(44), fill=col)
        draw.text((cx + 16, cy + 58), lbl, font=_fnt(19, False), fill=(170, 185, 198))
        cy += 105

    # Bottom brand bar
    by = H - 52
    draw.rectangle([0, by, W, H], fill=(0, 0, 12))
    draw.rectangle([0, by, W, by + 3], fill=ac)
    draw.text((20, by + 12), "⚡ EVCARIX", font=_fnt(28), fill=ac)
    tag = "EV DATA & INSIGHTS"
    tw  = int(draw.textlength(tag, font=_fnt(20, False)))
    draw.text((W - tw - 20, by + 16), tag, font=_fnt(20, False), fill=(125, 145, 165))

    return img


# ── Public API ────────────────────────────────────────────────────────────────
class ThumbnailGenerator:
    def __init__(self):
        # Keep pexels_key for possible future use, not needed for graphic style
        self.pexels_key = os.getenv("PEXELS_API_KEY")

    def create(self, title: str, topic: str = "default", stat: str = "",
               category: str = "default", output_path: str = "thumbnail.jpg",
               is_short: bool = False) -> str:
        W, H = (1080, 1920) if is_short else (1280, 720)

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        topic_key = topic.lower().replace(" ", "_")
        cfg       = TOPIC_CONFIG.get(topic_key, TOPIC_CONFIG["default"])

        # Short video: no graphic thumbnail needed — skip
        if is_short:
            try:
                img = Image.new("RGB", (W, H), cfg["bg_dark"])
                img.save(output_path, "JPEG", quality=80)
            except Exception:
                pass
            return output_path

        # Alternate styles per video using title hash
        h     = int(hashlib.md5(title.encode()).hexdigest(), 16)
        style = "A" if h % 2 == 0 else "B"

        try:
            if style == "A":
                img = _render_style_a(W, H, title, cfg)
            else:
                img = _render_style_b(W, H, title, cfg)

            img.save(output_path, "JPEG", quality=95)
            logger.info(f"[Thumbnail] ✅ Style-{style} → {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Thumbnail] ❌ create() error: {e}")
            # Minimal fallback
            try:
                fallback = Image.new("RGB", (W, H), (4, 8, 28))
                d = ImageDraw.Draw(fallback)
                d.text((40, H//2 - 40), title[:40].upper(),
                       font=_fnt(52), fill=(0, 212, 255))
                d.text((40, H - 60), "EVCARIX",
                       font=_fnt(30), fill=(0, 212, 255))
                fallback.save(output_path, "JPEG", quality=85)
                return output_path
            except Exception:
                return output_path
