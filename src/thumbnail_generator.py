import os
import re
import json
import logging
import hashlib
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

logger = logging.getLogger("ThumbnailGenerator")

OUTPUT_DIR = "output/thumbnails"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _fnt(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(BOLD if bold else REGULAR, size)
    except Exception:
        return ImageFont.load_default()


def _hex(h: str) -> tuple:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _mix(c1, c2, t):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


# ── Topic styles ──────────────────────────────────────────────────────────────
TOPIC_STYLES = {
    "electric_vehicle": {
        "bg":       (0, 0, 0),
        "left_bg":  (10, 0, 0),
        "right_bg": (0, 10, 24),
        "accent1":  (255, 34, 0),
        "accent2":  (0, 212, 255),
        "label":    "EV DATA",
        "icon":     "EV",
        "stats": [
            ("+300%", "EV SALES GROWTH",      (255, 34, 0)),
            ("$0",    "GAS CAR FUTURE VALUE",  (0, 212, 255)),
            ("500MI", "NEW EV RANGE RECORD",   (255, 204, 0)),
        ],
    },
    "battery_tech": {
        "bg":       (0, 0, 0),
        "left_bg":  (10, 5, 0),
        "right_bg": (0, 10, 5),
        "accent1":  (255, 107, 0),
        "accent2":  (0, 255, 136),
        "label":    "BATTERY",
        "icon":     "[B]",
        "stats": [
            ("1M KM",  "LFP LIFESPAN",        (255, 107, 0)),
            ("10 MIN", "FUTURE CHARGE TIME",   (0, 212, 255)),
            ("-45%",   "WINTER RANGE LOSS",    (0, 255, 136)),
        ],
    },
    "artificial_intelligence": {
        "bg":       (0, 0, 0),
        "left_bg":  (5, 0, 10),
        "right_bg": (0, 0, 10),
        "accent1":  (139, 0, 255),
        "accent2":  (0, 212, 255),
        "label":    "AI TECH",
        "icon":     "AI",
        "stats": [
            ("10x",  "SPEED VS HUMAN",  (139, 0, 255)),
            ("2030", "AGI PREDICTION",  (0, 212, 255)),
            ("$1T",  "AI MARKET SIZE",  (255, 204, 0)),
        ],
    },
    "robotics": {
        "bg":       (0, 0, 0),
        "left_bg":  (0, 10, 0),
        "right_bg": (0, 5, 5),
        "accent1":  (0, 255, 136),
        "accent2":  (255, 255, 255),
        "label":    "ROBOTICS",
        "icon":     "[R]",
        "stats": [
            ("40%",   "JOBS AUTOMATED",  (0, 255, 136)),
            ("$1.5T", "ROBOTICS MARKET", (0, 212, 255)),
            ("24/7",  "ROBOT UPTIME",    (255, 204, 0)),
        ],
    },
    "future_tech": {
        "bg":       (0, 0, 0),
        "left_bg":  (5, 0, 10),
        "right_bg": (10, 0, 5),
        "accent1":  (255, 0, 255),
        "accent2":  (255, 204, 0),
        "label":    "FUTURE",
        "icon":     ">>",
        "stats": [
            ("+300%", "EV SALES GROWTH",      (0, 212, 255)),
            ("$0",    "GAS CAR FUTURE VALUE",  (255, 180, 0)),
            ("500MI", "NEW EV RANGE RECORD",   (0, 255, 136)),
        ],
    },
    "default": {
        "bg":       (0, 0, 0),
        "left_bg":  (10, 0, 0),
        "right_bg": (0, 10, 24),
        "accent1":  (255, 34, 0),
        "accent2":  (0, 212, 255),
        "label":    "EV TECH",
        "icon":     "EV",
        "stats": [
            ("+300%", "EV SALES GROWTH",      (255, 34, 0)),
            ("$0",    "GAS CAR FUTURE VALUE",  (0, 212, 255)),
            ("500MI", "NEW EV RANGE RECORD",   (255, 204, 0)),
        ],
    },
}

LAYOUTS = ["split", "versus", "shock", "data"]


def _safe(text: str, max_len: int = 25) -> str:
    text = re.sub(r"[^\w\s%\-\+\?!.,:/]", "", text)
    return text[:max_len].strip()


def _split_title(title: str):
    words = title.upper().split()
    fillers = {"IN", "THE", "A", "AN", "AND", "OR", "OF", "FOR",
               "TO", "IS", "ARE", "WAS", "BUT", "WITH"}
    if len(words) > 9:
        words = [w for w in words if w not in fillers]
    lines, chunk = [], []
    for word in words:
        chunk.append(word)
        if len(chunk) == 3:
            lines.append(" ".join(chunk))
            chunk = []
            if len(lines) == 3:
                break
    if chunk and len(lines) < 3:
        lines.append(" ".join(chunk))
    while len(lines) < 3:
        lines.append("")
    return [_safe(ln) for ln in lines[:3]]


def _gradient(draw, W, H, top_c, bot_c):
    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=_mix(top_c, bot_c, t))


def _radial_glow(img, cx, cy, radius, color, strength=0.45):
    glow = Image.new("RGB", img.size, (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(radius, 0, -4):
        t = (1 - r / radius) * strength
        col = tuple(min(255, int(color[i] * t)) for i in range(3))
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return Image.blend(img, glow, 0.7)


def _brand_bar(draw, W, H, a1, a2, label):
    by = H - 72
    draw.rectangle([0, by, W, H], fill=(0, 0, 0))
    draw.rectangle([0, by, W, by + 3], fill=a1)
    draw.text((50, by + 18), "* EVCARIX", font=_fnt(34), fill=(255, 255, 255))
    tag = f"{label} & INSIGHTS"
    tw = int(draw.textlength(tag, font=_fnt(20, False)))
    draw.text((W - tw - 40, by + 24), tag, font=_fnt(20, False), fill=(120, 140, 155))


def _corners(draw, a1, a2):
    W, H = 1280, 720
    s, t, m, mb = 50, 5, 15, 83
    draw.rectangle([m, m, m + s, m + t],          fill=a1)
    draw.rectangle([m, m, m + t, m + s],          fill=a1)
    draw.rectangle([W - m - s, m, W - m, m + t],  fill=a2)
    draw.rectangle([W - m - t, m, W - m, m + s],  fill=a2)
    draw.rectangle([m, H - mb, m + s, H - mb + t],         fill=a1)
    draw.rectangle([m, H - mb - s, m + t, H - mb],         fill=a1)
    draw.rectangle([W - m - s, H - mb, W - m, H - mb + t], fill=a2)
    draw.rectangle([W - m - t, H - mb - s, W - m, H - mb], fill=a2)


# ── LAYOUT: split ─────────────────────────────────────────────────────────────
def _layout_split(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), st["bg"])
    draw = ImageDraw.Draw(img)

    # Left / right gradient panels
    for x in range(W // 2 + 80):
        t = x / (W // 2 + 80)
        draw.line([(x, 0), (x, H)], fill=_mix(st["left_bg"], st["bg"], t))
    for x in range(W // 2 - 80, W):
        t = (x - (W // 2 - 80)) / (W - (W // 2 - 80))
        draw.line([(x, 0), (x, H)], fill=_mix(st["bg"], st["right_bg"], t))

    img = _radial_glow(img, 200, H // 2, 500, a1, 0.35)
    img = _radial_glow(img, W - 200, H // 2, 450, a2, 0.28)
    draw = ImageDraw.Draw(img)

    # Diagonal divider lines (RGB only – no alpha channel needed)
    for i in range(6):
        x = W // 2 - 30 + i * 10
        col = a1 if i < 3 else a2
        draw.line([(x, 0), (x + 100, H)], fill=col, width=1)

    # Left accent bar
    draw.rectangle([0, 0, 14, H], fill=a1)

    # Badge top-left
    lbl = f"* {st['label']}"
    bf = _fnt(24)
    bw = int(draw.textlength(lbl, font=bf))
    draw.rectangle([18, 16, bw + 54, 54], fill=a1)
    draw.text((26, 20), lbl, font=bf, fill=(0, 0, 0))

    # Badge top-right
    rt = "EV TECH >"
    rf = _fnt(22)
    rtw = int(draw.textlength(rt, font=rf))
    draw.rectangle([W - rtw - 36, 16, W - 14, 54], fill=(0, 180, 220))
    draw.text((W - rtw - 20, 20), rt, font=rf, fill=(0, 0, 10))

    # Big L1 colored
    f1 = _fnt(int(H * 0.26))
    x_l = 30
    y1 = int(H * 0.10)
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((x_l + ox, y1 + oy), lines[0], font=f1,
                  fill=tuple(c // 2 for c in a1))
    draw.text((x_l, y1), lines[0], font=f1, fill=a1)

    # L2 white
    f2 = _fnt(int(H * 0.14))
    y2 = y1 + int(H * 0.29)
    draw.text((x_l, y2), lines[1], font=f2, fill=(255, 255, 255))

    # Strike through L2
    strike_y = y2 + int(H * 0.095)
    draw.rectangle(
        [x_l - 10, strike_y - 6,
         x_l + int(draw.textlength(lines[1], font=f2)) + 10, strike_y + 6],
        fill=a1,
    )

    # Sub-line
    if lines[2]:
        f3 = _fnt(int(H * 0.065), False)
        y3 = y2 + int(H * 0.175)
        draw.text((x_l, y3), lines[2][:40], font=f3, fill=(185, 185, 185))

    # Right side: "EV" big
    ev_f = _fnt(int(H * 0.38))
    ev_x = W - 30 - int(draw.textlength("EV", font=ev_f))
    ev_y = int(H * 0.08)
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((ev_x + ox, ev_y + oy), "EV", font=ev_f,
                  fill=tuple(c // 3 for c in a2))
    draw.text((ev_x, ev_y), "EV", font=ev_f, fill=a2)

    pf = _fnt(int(H * 0.07))
    pw = int(draw.textlength("DATA INSIDE", font=pf))
    draw.text((W - 30 - pw, ev_y + int(H * 0.42)), "DATA INSIDE",
              font=pf, fill=(255, 255, 255))

    # Center star marker
    lf = _fnt(90)
    lw = int(draw.textlength("*", font=lf))
    draw.text((W // 2 - lw // 2, H // 2 - 55), "*", font=lf,
              fill=(255, 220, 0))

    _brand_bar(draw, W, H, a1, a2, st["label"])
    _corners(draw, a1, a2)
    return img


# ── LAYOUT: versus ────────────────────────────────────────────────────────────
def _layout_versus(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (0, 5, 16))
    draw = ImageDraw.Draw(img)

    for y in range(H):
        t = y / H
        draw.line([(0, y), (W, y)], fill=_mix((0, 5, 16), (5, 0, 16), t))

    img = _radial_glow(img, 300, H // 2, 500, a1, 0.35)
    img = _radial_glow(img, W - 200, H // 2, 400, a2, 0.28)
    draw = ImageDraw.Draw(img)

    # Top bar
    draw.rectangle([0, 0, W, 78], fill=(0, 0, 0))
    draw.rectangle([0, 75, W, 78], fill=a1)
    sf = _fnt(22)
    shock_label = "! SHOCKING"
    shock_w = int(draw.textlength(shock_label, font=sf))
    draw.rectangle([14, 14, shock_w + 50, 62], fill=(255, 90, 0))
    draw.text((22, 18), shock_label, font=sf, fill=(255, 255, 255))
    draw.text((shock_w + 60, 18), "GAS CAR OWNERS MUST SEE THIS",
              font=_fnt(20, False), fill=(200, 200, 200))

    # Left content
    draw.text((38, 92), "THE", font=_fnt(38), fill=(140, 185, 220))
    mf = _fnt(int((H - 78) * 0.32))
    y_m = 140
    for line in [lines[0], lines[1]]:
        if not line:
            continue
        for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
            draw.text((38 + ox, y_m + oy), line, font=mf,
                      fill=tuple(c // 3 for c in a1))
        draw.text((38, y_m), line, font=mf, fill=a1)
        y_m += int((H - 78) * 0.33)
    if lines[2]:
        draw.text((42, y_m + 8), f"!! {lines[2]}", font=_fnt(28), fill=a2)

    # Vertical divider
    vx = W - 348
    for y in range(82, H - 74):
        draw.point((vx, y), fill=a1)

    # Right: stat cards
    cx, cy, cw = vx + 18, 90, W - vx - 36
    for val, lbl_text, col in st.get("stats", []):
        cr, cg, cb = col
        draw.rectangle(
            [cx, cy, cx + cw, cy + 90],
            fill=(max(0, cr // 8), max(0, cg // 8), max(0, cb // 8 + 6)),
        )
        draw.rectangle([cx, cy, cx + 6, cy + 90], fill=col)
        draw.text((cx + 14, cy + 6),  val,      font=_fnt(46),       fill=col)
        draw.text((cx + 14, cy + 58), lbl_text, font=_fnt(18, False), fill=(165, 180, 195))
        cy += 104

    _brand_bar(draw, W, H, a1, a2, st["label"])
    _corners(draw, a1, a2)
    return img


# ── LAYOUT: shock ─────────────────────────────────────────────────────────────
def _layout_shock(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    _gradient(draw, W, H, st["left_bg"], (0, 0, 0))

    img = _radial_glow(img, W // 2, int(H * 0.45), 550, a1, 0.4)
    img = _radial_glow(img, W // 2, int(H * 0.45), 400, a2, 0.25)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 12, H], fill=a1)
    draw.rectangle([W - 12, 0, W, H], fill=a2)

    # Icon
    ico_f = _fnt(88)
    iw = int(draw.textlength(st["icon"], font=ico_f))
    draw.text((W // 2 - iw // 2, int(H * 0.06)), st["icon"],
              font=ico_f, fill=(255, 220, 0))

    # Main text lines
    f1 = _fnt(int(H * 0.28))
    lw = int(draw.textlength(lines[0], font=f1))
    y1 = int(H * 0.22)
    for ox, oy in [(-4, 0), (4, 0), (0, -4), (0, 4)]:
        draw.text((W // 2 - lw // 2 + ox, y1 + oy), lines[0], font=f1,
                  fill=tuple(c // 2 for c in a1))
    draw.text((W // 2 - lw // 2, y1), lines[0], font=f1, fill=a1)

    f2 = _fnt(int(H * 0.17))
    lw2 = int(draw.textlength(lines[1], font=f2))
    y2 = y1 + int(H * 0.30)
    draw.text((W // 2 - lw2 // 2, y2), lines[1], font=f2, fill=(255, 255, 255))

    if lines[2]:
        f3 = _fnt(int(H * 0.09))
        lw3 = int(draw.textlength(lines[2], font=f3))
        y3 = y2 + int(H * 0.20)
        draw.text((W // 2 - lw3 // 2, y3), lines[2], font=f3, fill=a2)

    _brand_bar(draw, W, H, a1, a2, st["label"])
    _corners(draw, a1, a2)
    return img


# ── LAYOUT: data ──────────────────────────────────────────────────────────────
def _layout_data(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    _gradient(draw, W, H, st["left_bg"], st["right_bg"])

    img = _radial_glow(img, 100, H // 2, 450, a1, 0.32)
    img = _radial_glow(img, W - 100, H // 2, 400, a2, 0.26)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, 8, H], fill=a1)

    # Header badge
    lbl = f"{st['icon']} {st['label']}"
    bf = _fnt(24)
    bw = int(draw.textlength(lbl, font=bf))
    draw.rectangle([30, 28, bw + 68, 66], fill=a1)
    draw.text((38, 32), lbl, font=bf, fill=(0, 0, 0))

    ico_f = _fnt(60)
    draw.text((W - 90, 20), st["icon"], font=ico_f, fill=a1)

    # Main text
    f1 = _fnt(int(H * 0.24))
    y1 = 84
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((36 + ox, y1 + oy), lines[0], font=f1,
                  fill=tuple(c // 3 for c in a1))
    draw.text((36, y1), lines[0], font=f1, fill=a1)

    f2 = _fnt(int(H * 0.18))
    y2 = y1 + int(H * 0.255)
    draw.text((36, y2), lines[1], font=f2, fill=(255, 255, 255))

    if lines[2]:
        f3 = _fnt(int(H * 0.1))
        y3 = y2 + int(H * 0.195)
        draw.rectangle([36, y3 - 4, 36 + 6, y3 + int(H * 0.105)], fill=a2)
        draw.text((50, y3), lines[2], font=f3, fill=a2)

    # Stat boxes at bottom
    bx, by_s = 36, H - 148
    bw_s = (W - 72 - 40) // 3
    for i, (val, lbl_text, col) in enumerate(st.get("stats", [])):
        x = bx + i * (bw_s + 20)
        cr, cg, cb = col
        draw.rectangle(
            [x, by_s, x + bw_s, by_s + 68],
            fill=(max(0, cr // 7), max(0, cg // 7), max(0, cb // 7 + 5)),
        )
        draw.rectangle([x, by_s, x + bw_s, by_s + 4], fill=col)
        draw.text((x + 12, by_s + 10), val,          font=_fnt(36),       fill=col)
        draw.text((x + 12, by_s + 48), lbl_text[:14], font=_fnt(14, False), fill=(150, 165, 178))

    _brand_bar(draw, W, H, a1, a2, st["label"])
    _corners(draw, a1, a2)
    return img


# ── Public class ──────────────────────────────────────────────────────────────
class ThumbnailGenerator:

    def create(
        self,
        title: str,
        topic: str = "default",
        stat: str = "",
        category: str = "default",
        output_path: str = "",
        is_short: bool = False,
    ) -> str:
        # Short video → skip graphic thumbnail
        if is_short:
            if output_path:
                os.makedirs(
                    os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
                    exist_ok=True,
                )
                Image.new("RGB", (1080, 1920), (0, 0, 0)).save(
                    output_path, "JPEG", quality=60
                )
            return output_path or ""

        W, H = 1280, 720
        topic_key = topic.lower().replace(" ", "_")
        st = TOPIC_STYLES.get(topic_key, TOPIC_STYLES["default"])

        # Pick layout deterministically per title, cycle through all 4
        h = int(hashlib.md5(title.encode()).hexdigest(), 16)
        layout = LAYOUTS[h % len(LAYOUTS)]

        lines = _split_title(title)

        try:
            if layout == "split":
                img = _layout_split(W, H, lines, st)
            elif layout == "versus":
                img = _layout_versus(W, H, lines, st)
            elif layout == "shock":
                img = _layout_shock(W, H, lines, st)
            else:
                img = _layout_data(W, H, lines, st)

            if not output_path:
                safe_t = re.sub(r"[^\w]", "_", title[:30])
                output_path = os.path.join(OUTPUT_DIR, f"thumb_{safe_t}_{layout}.jpg")
            os.makedirs(
                os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
                exist_ok=True,
            )

            img.save(output_path, "JPEG", quality=95)
            size = os.path.getsize(output_path) // 1024
            logger.info(f"[Thumbnail] OK {layout} - {size}KB -> {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Thumbnail] ERROR create(): {e}")
            return output_path or ""

    def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        try:
            token_json  = os.getenv("YOUTUBE_TOKEN_JSON")
            secret_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
            if not token_json or not secret_json:
                logger.warning("[Thumbnail] Missing YouTube credentials")
                return False
            token_data  = json.loads(token_json)
            secret_data = json.loads(secret_json)
            client_id   = secret_data["installed"]["client_id"]
            client_sec  = secret_data["installed"]["client_secret"]
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_sec,
                scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
            )
            youtube = build("youtube", "v3", credentials=creds)
            media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
            logger.info(f"[Thumbnail] Uploaded to YouTube: {video_id}")
            return True
        except Exception as e:
            logger.error(f"[Thumbnail] Upload failed: {e}")
            return False


def generate_and_upload(video_id: str, title: str, topic: str) -> bool:
    gen = ThumbnailGenerator()
    path = gen.create(title=title, topic=topic)
    if path and os.path.exists(path):
        return gen.upload_thumbnail(video_id, path)
    return False
