import os
import re
import subprocess
import logging
import textwrap
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("BottomPanel")

# ── Fonts (GitHub Actions'da fonts-liberation yüklü) ────────────────────────
FONT_DIR = "/usr/share/fonts/truetype/liberation"
FONT_BOLD    = os.path.join(FONT_DIR, "LiberationSans-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "LiberationSans-Regular.ttf")

def _fnt(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

# ── Theme ─────────────────────────────────────────────────────────────────────
THEME = {
    "electric_vehicle":        ((0, 13, 26),  (0, 212, 255)),
    "artificial_intelligence": ((13, 0, 26),  (139, 0, 255)),
    "robotics":                ((0, 26, 0),   (0, 255, 136)),
    "battery_tech":            ((26, 8, 0),   (255, 107, 0)),
    "future_tech":             ((10, 0, 16),  (255, 0, 255)),
    "default":                 ((0, 13, 26),  (0, 212, 255)),
}

STATS = {
    "electric_vehicle": [
        ("⚡", "+300%",  "EV SALES GROWTH",     (0, 212, 255)),
        ("🔋", "500 MI", "NEW RANGE RECORD",     (255, 107, 0)),
        ("🌍", "$0",     "GAS CAR FUTURE VALUE", (0, 255, 136)),
    ],
    "battery_tech": [
        ("🔋", "1M KM",  "LFP LIFESPAN",        (0, 212, 255)),
        ("⚡", "10 MIN", "FUTURE CHARGE TIME",   (255, 107, 0)),
        ("📉", "-45%",   "WINTER RANGE LOSS",    (0, 255, 136)),
    ],
    "artificial_intelligence": [
        ("🤖", "GPT-5",  "LATEST AI MODEL",      (139, 0, 255)),
        ("⚡", "10x",    "SPEED VS HUMAN",        (255, 107, 0)),
        ("🌍", "2030",   "AGI PREDICTION",        (0, 212, 255)),
    ],
    "robotics": [
        ("🦾", "40%",    "JOBS AUTOMATED",        (0, 255, 136)),
        ("⚡", "24/7",   "ROBOT UPTIME",          (0, 212, 255)),
        ("🌍", "$1.5T",  "ROBOTICS MARKET",       (255, 107, 0)),
    ],
    "future_tech": [
        ("🚀", "2030",   "FLYING CARS ETA",       (255, 0, 255)),
        ("⚡", "1 TW",   "SOLAR CAPACITY",        (0, 212, 255)),
        ("🌍", "8B",     "PEOPLE CONNECTED",      (0, 255, 136)),
    ],
    "default": [
        ("⚡", "+300%",  "EV GROWTH 2026",        (0, 212, 255)),
        ("🔋", "500 MI", "RANGE RECORD",          (255, 107, 0)),
        ("🌍", "2030",   "FULL EV TARGET",        (0, 255, 136)),
    ],
}

def _safe_text(text: str, max_words: int = 8) -> str:
    clean = re.sub(r"(?i)welcome to ev[-\s]?care[-\s]?icks\.?\s*", "", text)
    clean = re.sub(r"[^a-zA-Z0-9 .,!?%\-]", " ", clean)
    return " ".join(clean.split()[:max_words]).upper()

def _draw_panel(topic: str, subtitle_text: str, W: int, H: int) -> Image.Image:
    bg_rgb, acc_rgb = THEME.get(topic, THEME["default"])
    stats = STATS.get(topic, STATS["default"])

    img  = Image.new("RGB", (W, H), bg_rgb)
    draw = ImageDraw.Draw(img)

    # Background gradient — subtle
    for y in range(H):
        t = y / H
        r = min(255, int(bg_rgb[0] + 10 * t))
        g = min(255, int(bg_rgb[1] + 15 * t))
        b = min(255, int(bg_rgb[2] + 20 * t))
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Top accent line
    draw.rectangle([0, 0, W, 4], fill=acc_rgb)

    # Layout: left 55% text, right 45% stat cards
    left_w  = int(W * 0.54)
    right_x = left_w + 12
    brand_h = 44
    body_h  = H - brand_h

    # Vertical divider
    for y in range(8, body_h - 8):
        alpha = 0.25 + 0.15 * abs((y - body_h // 2) / (body_h // 2))
        c = tuple(int(c * alpha) for c in acc_rgb)
        draw.point((left_w, y), fill=c)

    # ── LEFT: "NOW SPEAKING" label + subtitle ────────────────────────────────
    label_fnt = _fnt(20, bold=True)
    draw.text((22, 14), "NOW SPEAKING", font=label_fnt,
              fill=tuple(int(c * 0.6) for c in acc_rgb))

    speaking = _safe_text(subtitle_text, max_words=9)
    lines = textwrap.wrap(speaking, width=20)[:3]

    text_fnt  = _fnt(int(left_w * 0.075), bold=True)
    line_gap  = int(left_w * 0.088)
    total_th  = len(lines) * line_gap
    y_text    = (body_h - total_th) // 2 + 10

    for i, line in enumerate(lines):
        y = y_text + i * line_gap
        # Shadow
        draw.text((24, y + 2), line, font=text_fnt, fill=(0, 0, 0))
        # Main
        draw.text((22, y), line, font=text_fnt, fill=(255, 255, 255))

    # ── RIGHT: 3 stat cards ──────────────────────────────────────────────────
    card_h   = (body_h - 20) // 3 - 6
    card_w   = W - right_x - 14
    cy       = 10

    for icon, value, label, color in stats:
        # Card background
        card_bg = tuple(min(255, int(c * 0.15 + bg_rgb[i] * 0.85))
                        for i, c in enumerate(color))
        draw.rounded_rectangle(
            [right_x, cy, right_x + card_w, cy + card_h],
            radius=8, fill=card_bg
        )
        # Left accent bar
        draw.rounded_rectangle(
            [right_x, cy, right_x + 5, cy + card_h],
            radius=3, fill=color
        )
        # Value
        val_fnt = _fnt(int(card_h * 0.44), bold=True)
        draw.text((right_x + 16, cy + 6), value, font=val_fnt, fill=color)
        # Label
        lbl_fnt = _fnt(int(card_h * 0.22), bold=False)
        lbl_color = (160, 185, 200)
        draw.text((right_x + 16, cy + card_h - int(card_h * 0.32)),
                  label, font=lbl_fnt, fill=lbl_color)
        cy += card_h + 8

    # ── BOTTOM: Brand bar ────────────────────────────────────────────────────
    bar_y = H - brand_h
    draw.rectangle([0, bar_y, W, H], fill=(0, 0, 8))
    draw.rectangle([0, bar_y, W, bar_y + 2], fill=acc_rgb)

    brand_fnt = _fnt(24, bold=True)
    draw.text((20, bar_y + 10), "EVCARIX", font=brand_fnt, fill=acc_rgb)

    tag_fnt = _fnt(16, bold=False)
    tag_text = "EV DATA & INSIGHTS"
    tw = draw.textlength(tag_text, font=tag_fnt)
    draw.text((W - tw - 18, bar_y + 14), tag_text,
              font=tag_fnt, fill=(130, 160, 180))

    return img


def generate_bottom_panel(
    topic: str,
    subtitle_text: str,
    duration: float,
    output_path: str,
    panel_size: tuple = (1080, 480)
) -> str | None:
    W, H = panel_size
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    jpg_path = output_path.replace(".mp4", "_panel.jpg")

    try:
        # Draw panel with Pillow (no wkhtmltoimage needed)
        panel_img = _draw_panel(topic, subtitle_text, W, H)
        panel_img.save(jpg_path, "JPEG", quality=92)
        logger.info(f"[BottomPanel] Panel image: {jpg_path}")
    except Exception as e:
        logger.error(f"[BottomPanel] Draw failed: {e}")
        return _fallback_panel(topic, duration, output_path, W, H)

    # Convert static image → video
    safe_dur = round(max(duration, 1.0), 2)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", jpg_path,
        "-t", str(safe_dur),
        "-vf", f"scale={W}:{H},setsar=1",
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an",
        "-threads", "2",
        output_path
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        try:
            os.remove(jpg_path)
        except:
            pass
        if r.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path) // 1024
            logger.info(f"[BottomPanel] ✅ {output_path} ({size}KB)")
            return output_path
        logger.error(f"[BottomPanel] FFmpeg: {r.stderr[-200:]}")
    except Exception as e:
        logger.error(f"[BottomPanel] FFmpeg exception: {e}")

    return _fallback_panel(topic, duration, output_path, W, H)


def _fallback_panel(topic: str, duration: float, output_path: str,
                    W: int, H: int) -> str | None:
    bg_map = {
        "electric_vehicle": "0x001833", "battery_tech": "0x1a0800",
        "artificial_intelligence": "0x0d001a", "robotics": "0x001a00",
        "future_tech": "0x0a0010",
    }
    bg  = bg_map.get(topic, "0x001020")
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={bg}:size={W}x{H}:rate=24",
        "-t", str(round(max(duration, 1.0), 2)),
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an", output_path
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    if r.returncode == 0 and os.path.exists(output_path):
        logger.info(f"[BottomPanel] Fallback ok: {output_path}")
        return output_path
    return None
