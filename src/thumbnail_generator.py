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


def _mix(c1, c2, t):
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


# ── Topic styles ──────────────────────────────────────────────────────────────
TOPIC_STYLES = {
    "electric_vehicle": {
        "bg": (0, 0, 0), "left_bg": (10, 0, 0), "right_bg": (0, 10, 24),
        "accent1": (255, 34, 0), "accent2": (0, 212, 255),
        "label": "EV DATA", "icon": "EV",
        "stats": [
            ("+300%", "EV SALES GROWTH",     (255, 34, 0)),
            ("$0",    "GAS CAR FUTURE VALUE", (0, 212, 255)),
            ("500MI", "NEW EV RANGE RECORD",  (255, 204, 0)),
        ],
    },
    "battery_tech": {
        "bg": (0, 0, 0), "left_bg": (10, 5, 0), "right_bg": (0, 10, 5),
        "accent1": (255, 107, 0), "accent2": (0, 255, 136),
        "label": "BATTERY", "icon": "BAT",
        "stats": [
            ("1M KM",  "LFP LIFESPAN",       (255, 107, 0)),
            ("10 MIN", "FUTURE CHARGE TIME",  (0, 212, 255)),
            ("-45%",   "WINTER RANGE LOSS",   (0, 255, 136)),
        ],
    },
    "artificial_intelligence": {
        "bg": (0, 0, 0), "left_bg": (5, 0, 10), "right_bg": (0, 0, 10),
        "accent1": (139, 0, 255), "accent2": (0, 212, 255),
        "label": "AI TECH", "icon": "AI",
        "stats": [
            ("10x",  "SPEED VS HUMAN", (139, 0, 255)),
            ("2030", "AGI PREDICTION", (0, 212, 255)),
            ("$1T",  "AI MARKET SIZE", (255, 204, 0)),
        ],
    },
    "robotics": {
        "bg": (0, 0, 0), "left_bg": (0, 10, 0), "right_bg": (0, 5, 5),
        "accent1": (0, 255, 136), "accent2": (255, 255, 255),
        "label": "ROBOTICS", "icon": "BOT",
        "stats": [
            ("40%",   "JOBS AUTOMATED",  (0, 255, 136)),
            ("$1.5T", "ROBOTICS MARKET", (0, 212, 255)),
            ("24/7",  "ROBOT UPTIME",    (255, 204, 0)),
        ],
    },
    "future_tech": {
        "bg": (0, 0, 0), "left_bg": (5, 0, 10), "right_bg": (10, 0, 5),
        "accent1": (255, 0, 255), "accent2": (255, 204, 0),
        "label": "FUTURE", "icon": ">>",
        "stats": [
            ("+300%", "EV SALES GROWTH",     (0, 212, 255)),
            ("$0",    "GAS CAR FUTURE VALUE", (255, 180, 0)),
            ("500MI", "NEW EV RANGE RECORD",  (0, 255, 136)),
        ],
    },
    "default": {
        "bg": (0, 0, 0), "left_bg": (10, 0, 0), "right_bg": (0, 10, 24),
        "accent1": (255, 34, 0), "accent2": (0, 212, 255),
        "label": "EV TECH", "icon": "EV",
        "stats": [
            ("+300%", "EV SALES GROWTH",     (255, 34, 0)),
            ("$0",    "GAS CAR FUTURE VALUE", (0, 212, 255)),
            ("500MI", "NEW EV RANGE RECORD",  (255, 204, 0)),
        ],
    },
}

# Sabit sıra — create_all bu sırayla dosya adı numarası verir (01..10)
LAYOUTS = ["split", "versus", "shock", "data",
           "neon", "minimal", "alert", "cinematic", "grid", "bold"]


def _safe(text: str, max_len: int = 25) -> str:
    text = re.sub(r"[^\w\s%\-\+\?!.,:/]", "", text)
    return text[:max_len].strip()


def _split_title(title: str):
    words = title.upper().split()
    fillers = {"IN", "THE", "A", "AN", "AND", "OR", "OF",
               "FOR", "TO", "IS", "ARE", "WAS", "BUT", "WITH"}
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
        draw.line([(0, y), (W, y)], fill=_mix(top_c, bot_c, y / H))


def _radial_glow(img, cx, cy, radius, color, strength=0.45):
    glow = Image.new("RGB", img.size, (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(radius, 0, -4):
        t = (1 - r / radius) * strength
        col = tuple(min(255, int(color[i] * t)) for i in range(3))
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return Image.blend(img, glow, 0.7)


def _brand_bar(draw, W, H, a1, label):
    by = H - 72
    draw.rectangle([0, by, W, H], fill=(0, 0, 0))
    draw.rectangle([0, by, W, by + 3], fill=a1)
    draw.text((50, by + 18), "* EVCARIX", font=_fnt(34), fill=(255, 255, 255))
    tag = f"{label} & INSIGHTS"
    tw = int(draw.textlength(tag, font=_fnt(20, False)))
    draw.text((W - tw - 40, by + 24), tag, font=_fnt(20, False), fill=(120, 140, 155))


def _corners(draw, a1, a2, W=1280, H=720):
    s, t, m, mb = 50, 5, 15, 83
    draw.rectangle([m, m, m + s, m + t],                   fill=a1)
    draw.rectangle([m, m, m + t, m + s],                   fill=a1)
    draw.rectangle([W - m - s, m, W - m, m + t],           fill=a2)
    draw.rectangle([W - m - t, m, W - m, m + s],           fill=a2)
    draw.rectangle([m, H - mb, m + s, H - mb + t],         fill=a1)
    draw.rectangle([m, H - mb - s, m + t, H - mb],         fill=a1)
    draw.rectangle([W - m - s, H - mb, W - m, H - mb + t], fill=a2)
    draw.rectangle([W - m - t, H - mb - s, W - m, H - mb], fill=a2)


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 1 — split
# Sol: büyük renkli başlık + grev çizgisi | Sağ: "EV" dev yazı
# ─────────────────────────────────────────────────────────────────────────────
def _layout_split(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), st["bg"])
    draw = ImageDraw.Draw(img)
    for x in range(W // 2 + 80):
        draw.line([(x, 0), (x, H)], fill=_mix(st["left_bg"], st["bg"], x / (W // 2 + 80)))
    for x in range(W // 2 - 80, W):
        t = (x - (W // 2 - 80)) / (W - (W // 2 - 80))
        draw.line([(x, 0), (x, H)], fill=_mix(st["bg"], st["right_bg"], t))
    img = _radial_glow(img, 200, H // 2, 500, a1, 0.35)
    img = _radial_glow(img, W - 200, H // 2, 450, a2, 0.28)
    draw = ImageDraw.Draw(img)
    for i in range(6):
        x = W // 2 - 30 + i * 10
        draw.line([(x, 0), (x + 100, H)], fill=a1 if i < 3 else a2, width=1)
    draw.rectangle([0, 0, 14, H], fill=a1)
    lbl = f"* {st['label']}"
    bf = _fnt(24)
    bw = int(draw.textlength(lbl, font=bf))
    draw.rectangle([18, 16, bw + 54, 54], fill=a1)
    draw.text((26, 20), lbl, font=bf, fill=(0, 0, 0))
    rt = "EV TECH >"
    rf = _fnt(22)
    rtw = int(draw.textlength(rt, font=rf))
    draw.rectangle([W - rtw - 36, 16, W - 14, 54], fill=(0, 180, 220))
    draw.text((W - rtw - 20, 20), rt, font=rf, fill=(0, 0, 10))
    f1 = _fnt(int(H * 0.26))
    x_l, y1 = 30, int(H * 0.10)
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((x_l + ox, y1 + oy), lines[0], font=f1, fill=tuple(c // 2 for c in a1))
    draw.text((x_l, y1), lines[0], font=f1, fill=a1)
    f2 = _fnt(int(H * 0.14))
    y2 = y1 + int(H * 0.29)
    draw.text((x_l, y2), lines[1], font=f2, fill=(255, 255, 255))
    sy = y2 + int(H * 0.095)
    draw.rectangle([x_l - 10, sy - 6, x_l + int(draw.textlength(lines[1], font=f2)) + 10, sy + 6], fill=a1)
    if lines[2]:
        draw.text((x_l, y2 + int(H * 0.175)), lines[2][:40], font=_fnt(int(H * 0.065), False), fill=(185, 185, 185))
    ev_f = _fnt(int(H * 0.38))
    ev_x = W - 30 - int(draw.textlength("EV", font=ev_f))
    ev_y = int(H * 0.08)
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((ev_x + ox, ev_y + oy), "EV", font=ev_f, fill=tuple(c // 3 for c in a2))
    draw.text((ev_x, ev_y), "EV", font=ev_f, fill=a2)
    pf = _fnt(int(H * 0.07))
    pw = int(draw.textlength("DATA INSIDE", font=pf))
    draw.text((W - 30 - pw, ev_y + int(H * 0.42)), "DATA INSIDE", font=pf, fill=(255, 255, 255))
    lf = _fnt(90)
    lw = int(draw.textlength("*", font=lf))
    draw.text((W // 2 - lw // 2, H // 2 - 55), "*", font=lf, fill=(255, 220, 0))
    _brand_bar(draw, W, H, a1, st["label"])
    _corners(draw, a1, a2)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 2 — versus
# Üst kırmızı banner + sol metin + sağ stat kartları
# ─────────────────────────────────────────────────────────────────────────────
def _layout_versus(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (0, 5, 16))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        draw.line([(0, y), (W, y)], fill=_mix((0, 5, 16), (5, 0, 16), y / H))
    img = _radial_glow(img, 300, H // 2, 500, a1, 0.35)
    img = _radial_glow(img, W - 200, H // 2, 400, a2, 0.28)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 78], fill=(0, 0, 0))
    draw.rectangle([0, 75, W, 78], fill=a1)
    sf = _fnt(22)
    shock_label = "! SHOCKING"
    sw = int(draw.textlength(shock_label, font=sf))
    draw.rectangle([14, 14, sw + 50, 62], fill=(255, 90, 0))
    draw.text((22, 18), shock_label, font=sf, fill=(255, 255, 255))
    draw.text((sw + 60, 18), "GAS CAR OWNERS MUST SEE THIS", font=_fnt(20, False), fill=(200, 200, 200))
    draw.text((38, 92), "THE", font=_fnt(38), fill=(140, 185, 220))
    mf = _fnt(int((H - 78) * 0.32))
    y_m = 140
    for line in [lines[0], lines[1]]:
        if not line:
            continue
        for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
            draw.text((38 + ox, y_m + oy), line, font=mf, fill=tuple(c // 3 for c in a1))
        draw.text((38, y_m), line, font=mf, fill=a1)
        y_m += int((H - 78) * 0.33)
    if lines[2]:
        draw.text((42, y_m + 8), f"!! {lines[2]}", font=_fnt(28), fill=a2)
    vx = W - 348
    for y in range(82, H - 74):
        draw.point((vx, y), fill=a1)
    cx, cy, cw = vx + 18, 90, W - vx - 36
    for val, lbl_text, col in st.get("stats", []):
        cr, cg, cb = col
        draw.rectangle([cx, cy, cx + cw, cy + 90],
                       fill=(max(0, cr // 8), max(0, cg // 8), max(0, cb // 8 + 6)))
        draw.rectangle([cx, cy, cx + 6, cy + 90], fill=col)
        draw.text((cx + 14, cy + 6),  val,      font=_fnt(46),        fill=col)
        draw.text((cx + 14, cy + 58), lbl_text, font=_fnt(18, False), fill=(165, 180, 195))
        cy += 104
    _brand_bar(draw, W, H, a1, st["label"])
    _corners(draw, a1, a2)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 3 — shock
# Tam merkez tipografi, radyal patlama efekti
# ─────────────────────────────────────────────────────────────────────────────
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
    ico_f = _fnt(88)
    iw = int(draw.textlength(st["icon"], font=ico_f))
    draw.text((W // 2 - iw // 2, int(H * 0.06)), st["icon"], font=ico_f, fill=(255, 220, 0))
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
        draw.text((W // 2 - lw3 // 2, y2 + int(H * 0.20)), lines[2], font=f3, fill=a2)
    _brand_bar(draw, W, H, a1, st["label"])
    _corners(draw, a1, a2)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 4 — data
# Sol metin + alt 3 istatistik kutusu
# ─────────────────────────────────────────────────────────────────────────────
def _layout_data(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    _gradient(draw, W, H, st["left_bg"], st["right_bg"])
    img = _radial_glow(img, 100, H // 2, 450, a1, 0.32)
    img = _radial_glow(img, W - 100, H // 2, 400, a2, 0.26)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 8, H], fill=a1)
    lbl = f"{st['icon']} {st['label']}"
    bf = _fnt(24)
    bw = int(draw.textlength(lbl, font=bf))
    draw.rectangle([30, 28, bw + 68, 66], fill=a1)
    draw.text((38, 32), lbl, font=bf, fill=(0, 0, 0))
    draw.text((W - 90, 20), st["icon"], font=_fnt(60), fill=a1)
    f1 = _fnt(int(H * 0.24))
    y1 = 84
    for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
        draw.text((36 + ox, y1 + oy), lines[0], font=f1, fill=tuple(c // 3 for c in a1))
    draw.text((36, y1), lines[0], font=f1, fill=a1)
    f2 = _fnt(int(H * 0.18))
    y2 = y1 + int(H * 0.255)
    draw.text((36, y2), lines[1], font=f2, fill=(255, 255, 255))
    if lines[2]:
        f3 = _fnt(int(H * 0.1))
        y3 = y2 + int(H * 0.195)
        draw.rectangle([36, y3 - 4, 36 + 6, y3 + int(H * 0.105)], fill=a2)
        draw.text((50, y3), lines[2], font=f3, fill=a2)
    bx, by_s = 36, H - 148
    bw_s = (W - 72 - 40) // 3
    for i, (val, lbl_text, col) in enumerate(st.get("stats", [])):
        x = bx + i * (bw_s + 20)
        cr, cg, cb = col
        draw.rectangle([x, by_s, x + bw_s, by_s + 68],
                       fill=(max(0, cr // 7), max(0, cg // 7), max(0, cb // 7 + 5)))
        draw.rectangle([x, by_s, x + bw_s, by_s + 4], fill=col)
        draw.text((x + 12, by_s + 10), val,           font=_fnt(36),        fill=col)
        draw.text((x + 12, by_s + 48), lbl_text[:14], font=_fnt(14, False), fill=(150, 165, 178))
    _brand_bar(draw, W, H, a1, st["label"])
    _corners(draw, a1, a2)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 5 — neon
# Cyberpunk: koyu mor, neon yatay çizgiler, merkez parlak metin
# ─────────────────────────────────────────────────────────────────────────────
def _layout_neon(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (4, 0, 20))
    draw = ImageDraw.Draw(img)
    for i, y in enumerate(range(0, H, 36)):
        intensity = 8 if i % 3 == 0 else 4
        draw.line([(0, y), (W, y)], fill=(intensity, 0, intensity * 2))
    img = _radial_glow(img, W // 2, H // 2, 600, a1, 0.5)
    img = _radial_glow(img, W // 2, H // 2, 350, a2, 0.3)
    draw = ImageDraw.Draw(img)
    # Neon çerçeve
    for offset in range(0, 20, 5):
        c = max(0, 255 - offset * 10)
        col = tuple(min(255, int(a1[i] * c / 255)) for i in range(3))
        draw.rectangle([offset, offset, W - offset, H - 75 - offset], outline=col, width=1)
    # Üst etiket
    draw.rectangle([0, 0, W, 50], fill=(0, 0, 0))
    lbl_txt = f"[ {st['label']} REPORT ]"
    lf = _fnt(26)
    lw = int(draw.textlength(lbl_txt, font=lf))
    draw.text((W // 2 - lw // 2, 12), lbl_txt, font=lf, fill=a2)
    # Ana metin merkez
    f1 = _fnt(int(H * 0.22))
    y1 = int(H * 0.16)
    tw1 = int(draw.textlength(lines[0], font=f1))
    for ox, oy in [(-5, 0), (5, 0), (0, -5), (0, 5)]:
        draw.text((W // 2 - tw1 // 2 + ox, y1 + oy), lines[0], font=f1,
                  fill=tuple(min(255, c * 2) for c in a1))
    draw.text((W // 2 - tw1 // 2, y1), lines[0], font=f1, fill=(255, 255, 255))
    draw.rectangle([W // 2 - tw1 // 2 - 10, y1 + int(H * 0.225),
                    W // 2 + tw1 // 2 + 10, y1 + int(H * 0.235)], fill=a1)
    f2 = _fnt(int(H * 0.14))
    y2 = y1 + int(H * 0.26)
    tw2 = int(draw.textlength(lines[1], font=f2))
    draw.text((W // 2 - tw2 // 2, y2), lines[1], font=f2, fill=a1)
    if lines[2]:
        f3 = _fnt(int(H * 0.085), False)
        tw3 = int(draw.textlength(lines[2], font=f3))
        draw.text((W // 2 - tw3 // 2, y2 + int(H * 0.185)), lines[2], font=f3, fill=a2)
    # Sol/sağ neon dikey çizgiler
    for offset in range(3):
        draw.line([(8 + offset * 4, 50), (8 + offset * 4, H - 75)], fill=a1, width=2)
        draw.line([(W - 8 - offset * 4, 50), (W - 8 - offset * 4, H - 75)], fill=a2, width=2)
    _brand_bar(draw, W, H, a1, st["label"])
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 6 — minimal
# Temiz, büyük tipografi, sol dikey çizgi, sağ dev sayı
# ─────────────────────────────────────────────────────────────────────────────
def _layout_minimal(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (8, 8, 12))
    draw = ImageDraw.Draw(img)
    for x in range(W):
        draw.line([(x, 0), (x, H)], fill=_mix((8, 8, 12), st["right_bg"], x / W * 0.15))
    draw.rectangle([0, 0, 16, H], fill=a1)
    draw.rectangle([0, 0, W, 6], fill=a1)
    draw.text((30, 20), f"EVCARIX  //  {st['label']}", font=_fnt(20, False), fill=(100, 110, 125))
    f1 = _fnt(int(H * 0.30))
    y1 = int(H * 0.12)
    draw.text((30, y1), lines[0], font=f1, fill=(240, 240, 240))
    line_y = y1 + int(H * 0.315)
    draw.rectangle([30, line_y, 30 + int(draw.textlength(lines[0], font=f1)), line_y + 8], fill=a1)
    f2 = _fnt(int(H * 0.16))
    y2 = line_y + 18
    draw.text((30, y2), lines[1], font=f2, fill=a2)
    if lines[2]:
        draw.text((30, y2 + int(H * 0.195)), lines[2], font=_fnt(int(H * 0.08), False), fill=(160, 165, 175))
    big_f = _fnt(int(H * 0.50))
    big_txt = st["stats"][0][0] if st.get("stats") else st["icon"]
    bw_px = int(draw.textlength(big_txt, font=big_f))
    bx = W - bw_px - 60
    by = int(H * 0.12)
    draw.text((bx + 3, by + 3), big_txt, font=big_f, fill=tuple(c // 6 for c in a1))
    draw.text((bx, by), big_txt, font=big_f, fill=a1)
    if st.get("stats"):
        sf = _fnt(18, False)
        desc = st["stats"][0][1]
        sw_px = int(draw.textlength(desc, font=sf))
        draw.text((W - sw_px - 60, by + int(H * 0.52)), desc, font=sf, fill=(130, 140, 150))
    draw.rectangle([0, H - 72, W, H - 72 + 3], fill=a1)
    draw.text((30, H - 58), "* EVCARIX", font=_fnt(30), fill=(255, 255, 255))
    draw.text((W - 200, H - 52), st["label"], font=_fnt(22, False), fill=(80, 90, 100))
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 7 — alert
# Haber/uyarı: üst kırmızı "ALERT" banner, sağ stat, sola metin
# ─────────────────────────────────────────────────────────────────────────────
def _layout_alert(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    dark1 = tuple(min(20, c // 4) for c in a1)
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    _gradient(draw, W, H, dark1, (0, 0, 0))
    img = _radial_glow(img, W // 4, H // 2, 600, a1, 0.45)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 22, H], fill=a1)
    draw.rectangle([22, 0, W, 68], fill=a1)
    af = _fnt(38)
    draw.text((36, 14), ">> ALERT:", font=af, fill=(0, 0, 0))
    sub_x = 36 + int(draw.textlength(">> ALERT:", font=af)) + 20
    draw.text((sub_x, 20), st["label"], font=_fnt(28, False), fill=(0, 0, 0))
    draw.rectangle([W - 180, 0, W, 68], fill=(0, 0, 0))
    draw.text((W - 165, 16), st["icon"], font=_fnt(36), fill=a1)
    f1 = _fnt(int(H * 0.25))
    y1 = 84
    draw.text((36, y1), lines[0], font=f1, fill=(255, 255, 255))
    draw.rectangle([36, y1 + int(H * 0.265),
                    36 + int(draw.textlength(lines[0], font=f1)), y1 + int(H * 0.275)], fill=a2)
    f2 = _fnt(int(H * 0.155))
    y2 = y1 + int(H * 0.29)
    draw.text((36, y2), lines[1], font=f2, fill=a2)
    if lines[2]:
        draw.text((36, y2 + int(H * 0.185)), lines[2],
                  font=_fnt(int(H * 0.085), False), fill=(200, 200, 200))
    rx, ry = W - 320, 80
    for val, lbl_text, col in st.get("stats", []):
        cr, cg, cb = col
        draw.rectangle([rx, ry, rx + 300, ry + 88],
                       fill=(max(0, cr // 9), max(0, cg // 9), max(0, cb // 9 + 4)))
        draw.rectangle([rx, ry, rx + 8, ry + 88], fill=col)
        draw.text((rx + 18, ry + 8),  val,      font=_fnt(42),        fill=col)
        draw.text((rx + 18, ry + 56), lbl_text, font=_fnt(16, False), fill=(160, 175, 185))
        ry += 100
    _brand_bar(draw, W, H, a1, st["label"])
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 8 — cinematic
# Film afişi: letterbox bantlar, radyal ışık, büyük merkez başlık
# ─────────────────────────────────────────────────────────────────────────────
def _layout_cinematic(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (2, 2, 6))
    draw = ImageDraw.Draw(img)
    img = _radial_glow(img, W // 2, H // 2, 700, a1, 0.38)
    img = _radial_glow(img, W // 2, H // 2, 400, a2, 0.18)
    draw = ImageDraw.Draw(img)
    bar_h = int(H * 0.13)
    draw.rectangle([0, 0, W, bar_h], fill=(0, 0, 0))
    draw.rectangle([0, H - bar_h, W, H], fill=(0, 0, 0))
    draw.text((40, H - bar_h + 14), "* EVCARIX", font=_fnt(26), fill=(200, 200, 200))
    tag = f"{st['label']} & INSIGHTS"
    tw = int(draw.textlength(tag, font=_fnt(18, False)))
    draw.text((W - tw - 40, H - bar_h + 18), tag, font=_fnt(18, False), fill=(90, 100, 110))
    lbl_txt = f"[ {st['label']} ]"
    lf = _fnt(22)
    lw = int(draw.textlength(lbl_txt, font=lf))
    draw.text((W // 2 - lw // 2, bar_h // 2 - 12), lbl_txt, font=lf, fill=a2)
    mid_y = H // 2
    draw.rectangle([60, mid_y - 3, W - 60, mid_y + 3], fill=a1)
    f1 = _fnt(int(H * 0.20))
    tw1 = int(draw.textlength(lines[0], font=f1))
    y1 = mid_y - int(H * 0.285)
    for ox, oy in [(-4, 0), (4, 0)]:
        draw.text((W // 2 - tw1 // 2 + ox, y1 + oy), lines[0], font=f1,
                  fill=tuple(c // 3 for c in a1))
    draw.text((W // 2 - tw1 // 2, y1), lines[0], font=f1, fill=(240, 240, 240))
    f2 = _fnt(int(H * 0.155))
    tw2 = int(draw.textlength(lines[1], font=f2))
    draw.text((W // 2 - tw2 // 2, y1 + int(H * 0.225)), lines[1], font=f2, fill=a1)
    if lines[2]:
        f3 = _fnt(int(H * 0.09), False)
        tw3 = int(draw.textlength(lines[2], font=f3))
        draw.text((W // 2 - tw3 // 2, mid_y + int(H * 0.06)), lines[2], font=f3, fill=a2)
    for offset in [60, 68, 76]:
        draw.line([(offset, bar_h), (offset, H - bar_h)], fill=a1, width=1)
        draw.line([(W - offset, bar_h), (W - offset, H - bar_h)], fill=a2, width=1)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 9 — grid
# Infografik ızgara: sol metin + sağ 3 büyük stat kartı
# ─────────────────────────────────────────────────────────────────────────────
def _layout_grid(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for x in range(0, W, 60):
        draw.line([(x, 0), (x, H)], fill=(12, 12, 18), width=1)
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=(12, 12, 18), width=1)
    _gradient(draw, W, H, st["left_bg"], (0, 0, 0))
    img = _radial_glow(img, 200, H // 2, 550, a1, 0.35)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 20, H], fill=a1)
    draw.rectangle([0, 0, W // 2 + 20, 6], fill=a1)
    ef = _fnt(22)
    ew = int(draw.textlength(st["label"], font=ef))
    draw.rectangle([30, 18, ew + 58, 54], fill=a1)
    draw.text((38, 22), st["label"], font=ef, fill=(0, 0, 0))
    f1 = _fnt(int(H * 0.22))
    y1 = 70
    for ox, oy in [(-2, 0), (2, 0)]:
        draw.text((30 + ox, y1 + oy), lines[0], font=f1, fill=tuple(c // 3 for c in a1))
    draw.text((30, y1), lines[0], font=f1, fill=a1)
    f2 = _fnt(int(H * 0.145))
    y2 = y1 + int(H * 0.245)
    draw.text((30, y2), lines[1], font=f2, fill=(230, 230, 230))
    lw2 = int(draw.textlength(lines[1], font=f2))
    draw.rectangle([30, y2 + int(H * 0.158), 30 + lw2, y2 + int(H * 0.168)], fill=a2)
    if lines[2]:
        draw.text((30, y2 + int(H * 0.182)), lines[2],
                  font=_fnt(int(H * 0.078), False), fill=(155, 165, 175))
    gx = W // 2 + 30
    gy = 20
    gw = W - gx - 30
    for i, (val, lbl_text, col) in enumerate(st.get("stats", [])):
        card_h = (H - 100) // 3 - 8
        cy_card = gy + i * (card_h + 10)
        cr, cg, cb = col
        draw.rectangle([gx, cy_card, gx + gw, cy_card + card_h],
                       fill=(max(0, cr // 9), max(0, cg // 9), max(0, cb // 9 + 6)))
        draw.rectangle([gx, cy_card, gx + 10, cy_card + card_h], fill=col)
        vf = _fnt(int(card_h * 0.65))
        draw.text((gx + 22, cy_card + 4), val, font=vf, fill=col)
        draw.text((gx + 22, cy_card + card_h - 26), lbl_text,
                  font=_fnt(16, False), fill=(155, 170, 185))
    _brand_bar(draw, W, H, a1, st["label"])
    _corners(draw, a1, a2)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT 10 — bold
# Maksimum etki: diyagonal renkli bant, dev tipografi, güçlü kontrast
# ─────────────────────────────────────────────────────────────────────────────
def _layout_bold(W, H, lines, st):
    a1, a2 = st["accent1"], st["accent2"]
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    tri_pts = [(W // 2, 0), (W, 0), (W, H), (W // 2 + 80, H)]
    draw.polygon(tri_pts, fill=tuple(c // 5 for c in a1))
    for i in range(12):
        x_start = W // 2 - 40 + i * 30
        draw.line([(x_start, 0), (x_start + 200, H)], fill=tuple(c // 3 for c in a1), width=2)
    img = _radial_glow(img, W // 4, H // 2, 580, a1, 0.42)
    img = _radial_glow(img, W - 100, H // 4, 400, a2, 0.30)
    draw = ImageDraw.Draw(img)
    for i, w in enumerate([20, 6, 3]):
        x = [0, 28, 40][i]
        draw.rectangle([x, 0, x + w, H], fill=a1 if i == 0 else tuple(c // 2 for c in a1))
    draw.rectangle([0, 0, W, 58], fill=(0, 0, 0))
    draw.rectangle([0, 55, W, 58], fill=a1)
    draw.text((54, 15), f"EVCARIX  |  {st['label']} SERIES", font=_fnt(24), fill=(200, 200, 200))
    f1 = _fnt(int(H * 0.285))
    y1 = 70
    draw.text((50, y1 + 4), lines[0], font=f1, fill=tuple(c // 5 for c in a1))
    draw.text((50, y1), lines[0], font=f1, fill=(255, 255, 255))
    f2 = _fnt(int(H * 0.175))
    y2 = y1 + int(H * 0.315)
    draw.text((50, y2), lines[1], font=f2, fill=a1)
    lw2 = int(draw.textlength(lines[1], font=f2))
    draw.rectangle([50, y2 + int(H * 0.186), 50 + lw2, y2 + int(H * 0.198)], fill=a2)
    if lines[2]:
        draw.text((50, y2 + int(H * 0.215)), lines[2],
                  font=_fnt(int(H * 0.09), False), fill=(170, 180, 190))
    big_f = _fnt(int(H * 0.42))
    big_val = st["stats"][0][0] if st.get("stats") else st["icon"]
    bw_px = int(draw.textlength(big_val, font=big_f))
    bx = W - bw_px - 50
    by = int(H * 0.08)
    draw.text((bx + 5, by + 5), big_val, font=big_f, fill=tuple(c // 6 for c in a2))
    draw.text((bx, by), big_val, font=big_f, fill=a2)
    if st.get("stats"):
        desc = st["stats"][0][1]
        sf = _fnt(20, False)
        sw_px = int(draw.textlength(desc, font=sf))
        draw.text((W - sw_px - 50, by + int(H * 0.46)), desc, font=sf, fill=(120, 130, 140))
    _brand_bar(draw, W, H, a1, st["label"])
    _corners(draw, a1, a2)
    return img


# ── Layout dispatch tablosu ───────────────────────────────────────────────────
_LAYOUT_FN = {
    "split":     _layout_split,
    "versus":    _layout_versus,
    "shock":     _layout_shock,
    "data":      _layout_data,
    "neon":      _layout_neon,
    "minimal":   _layout_minimal,
    "alert":     _layout_alert,
    "cinematic": _layout_cinematic,
    "grid":      _layout_grid,
    "bold":      _layout_bold,
}


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
        """Geriye dönük uyumluluk: tek thumbnail oluşturur."""
        if is_short:
            logger.info("[Thumbnail] Short video - thumbnail atlanıyor.")
            return ""

        W, H = 1280, 720
        topic_key = topic.lower().replace(" ", "_")
        st = TOPIC_STYLES.get(topic_key, TOPIC_STYLES["default"])
        h = int(hashlib.md5(title.encode()).hexdigest(), 16)
        layout = LAYOUTS[h % len(LAYOUTS)]
        lines = _split_title(title)

        try:
            img = _LAYOUT_FN[layout](W, H, lines, st)
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

    def create_all(
        self,
        title: str,
        topic: str = "default",
        is_short: bool = False,
        out_dir: str = "",
    ) -> list:
        """
        10 farklı layout'ta thumbnail üretir.
        Dosya adları: {baslik}_{01..10}_{layout}.jpg  (sıra korunur)
        Kısa videoda boş liste döner.
        """
        if is_short:
            logger.info("[Thumbnail] Short video - thumbnail atlanıyor.")
            return []

        W, H = 1280, 720
        topic_key = topic.lower().replace(" ", "_")
        st = TOPIC_STYLES.get(topic_key, TOPIC_STYLES["default"])
        lines = _split_title(title)
        safe_t = re.sub(r"[^\w]", "_", title[:30])
        base_dir = out_dir or OUTPUT_DIR
        os.makedirs(base_dir, exist_ok=True)

        paths = []
        for idx, layout_name in enumerate(LAYOUTS):
            fn = _LAYOUT_FN[layout_name]
            try:
                img = fn(W, H, lines, st)
                path = os.path.join(base_dir, f"{safe_t}_{idx+1:02d}_{layout_name}.jpg")
                img.save(path, "JPEG", quality=95)
                size = os.path.getsize(path) // 1024
                logger.info(f"[Thumbnail] [{idx+1:2d}/10] {layout_name:12s} {size:4d}KB -> {path}")
                paths.append(path)
            except Exception as e:
                logger.error(f"[Thumbnail] ERROR {layout_name}: {e}")

        logger.info(f"[Thumbnail] Toplam {len(paths)}/10 thumbnail uretildi.")
        return paths

    def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Tek thumbnail YouTube'a yükle."""
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
            logger.info(f"[Thumbnail] YouTube'a yuklendi: {video_id}")
            return True
        except Exception as e:
            logger.error(f"[Thumbnail] Upload failed: {e}")
            return False

    def upload_all(self, video_id: str, thumbnail_paths: list) -> int:
        """
        Tüm thumbnail'leri sırayla yükle.
        YouTube yalnızca en son yüklenenin görünür olduğunu not et;
        dışarıdan istenen index'i upload_one ile seçebilirsin.
        Başarıyla yüklenen sayısını döner.
        """
        success = 0
        for idx, path in enumerate(thumbnail_paths):
            if not path or not os.path.exists(path):
                logger.warning(f"[Thumbnail] Dosya bulunamiyor: {path}")
                continue
            logger.info(f"[Thumbnail] Yukleniyor [{idx+1}/{len(thumbnail_paths)}]: {path}")
            if self.upload_thumbnail(video_id, path):
                success += 1
        logger.info(f"[Thumbnail] {success}/{len(thumbnail_paths)} thumbnail yuklendi.")
        return success

    def upload_one(self, video_id: str, thumbnail_paths: list, index: int = 0) -> bool:
        """
        Listeden belirli bir thumbnail'i yükle.
        index: 0-9 arası (modüler, liste dışına taşmaz).
        """
        if not thumbnail_paths:
            logger.warning("[Thumbnail] Thumbnail listesi bos.")
            return False
        return self.upload_thumbnail(video_id, thumbnail_paths[index % len(thumbnail_paths)])


def generate_and_upload(video_id: str, title: str, topic: str,
                        is_short: bool = False) -> bool:
    """
    Uzun video → 10 thumbnail üret + sırayla yükle.
    Kısa video → hiçbir şey yapma, False döner.
    """
    if is_short:
        logger.info("[Thumbnail] Short video - atlaniyor.")
        return False
    gen = ThumbnailGenerator()
    paths = gen.create_all(title=title, topic=topic, is_short=False)
    if not paths:
        return False
    uploaded = gen.upload_all(video_id, paths)
    return uploaded > 0
