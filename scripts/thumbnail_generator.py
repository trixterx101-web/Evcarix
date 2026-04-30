#!/usr/bin/env python3
"""
thumbnail_generator.py
======================
Evcarix YouTube Shorts thumbnail generator (9:16 format)
Usage:
    python thumbnail_generator.py --title "EV Range Lost 40%?" --subtitle "Real Winter Test" --accent red --output thumb.png
    python thumbnail_generator.py --json '{"title":"FAST CHARGING","subtitle":"Damages Battery?!","accent":"cyan","stat":"-30%"}'
    python thumbnail_generator.py --claude "winter ev range loss topic"   # AI generates layout
"""

import argparse
import json
import math
import os
import random
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Font paths (fallback chain) ─────────────────────────────────────────────
FONT_BOLD   = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_MEDIUM = "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf"
FONT_REGULAR= "/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf"
FONT_SERIF  = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"

# ── Canvas size (9:16 Shorts) ────────────────────────────────────────────────
W, H = 1080, 1920

# ── Accent palettes ──────────────────────────────────────────────────────────
PALETTES = {
    "red":    {"accent": (255, 45, 45),  "glow": (180, 0, 0),    "secondary": (255, 200, 0)},
    "cyan":   {"accent": (0, 240, 255),  "glow": (0, 160, 200),  "secondary": (255, 255, 255)},
    "yellow": {"accent": (255, 220, 0),  "glow": (180, 140, 0),  "secondary": (255, 80, 0)},
    "green":  {"accent": (0, 255, 120),  "glow": (0, 160, 80),   "secondary": (200, 255, 0)},
    "orange": {"accent": (255, 120, 0),  "glow": (180, 60, 0),   "secondary": (255, 220, 0)},
}

def load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def draw_glow_text(draw, text, x, y, font, color, glow_color, glow_radius=18, anchor="mm"):
    """Draw text with glow effect using multiple blurred shadow layers."""
    for r in [glow_radius, glow_radius // 2, glow_radius // 4]:
        alpha = max(80, 200 - r * 4)
        blur_color = glow_color + (alpha,)
        for dx in range(-r, r + 1, max(1, r // 3)):
            for dy in range(-r, r + 1, max(1, r // 3)):
                draw.text((x + dx, y + dy), text, font=font, fill=glow_color, anchor=anchor)
    draw.text((x, y), text, font=font, fill=color, anchor=anchor)

def draw_outlined_text(draw, text, x, y, font, fill, outline, thickness=6, anchor="mm"):
    for ox in range(-thickness, thickness + 1, 2):
        for oy in range(-thickness, thickness + 1, 2):
            draw.text((x + ox, y + oy), text, font=font, fill=outline, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]

def draw_lightning_bolt(draw, cx, cy, size, color):
    """Draw a simple lightning bolt shape."""
    pts = [
        (cx + size * 0.2,  cy - size * 0.5),
        (cx - size * 0.05, cy + size * 0.05),
        (cx + size * 0.12, cy + size * 0.05),
        (cx - size * 0.2,  cy + size * 0.5),
        (cx + size * 0.05, cy - size * 0.05),
        (cx - size * 0.12, cy - size * 0.05),
    ]
    draw.polygon(pts, fill=color)

def draw_battery_bar(draw, x, y, w, h, pct, color_full, color_low):
    """Draw a horizontal battery bar."""
    radius = h // 3
    # Outline
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, outline=(200, 200, 200), width=4)
    # Terminal
    tw, th = 14, h // 2
    draw.rectangle([x + w + 4, y + (h - th) // 2, x + w + 4 + tw, y + (h + th) // 2], fill=(180, 180, 180))
    # Fill
    fill_w = int((w - 12) * pct / 100)
    fill_color = color_full if pct > 30 else color_low
    if fill_w > 0:
        draw.rounded_rectangle([x + 6, y + 6, x + 6 + fill_w, y + h - 6], radius=radius // 2, fill=fill_color)

def build_background(palette):
    """Generate a dark dramatic background with gradient + noise."""
    img = Image.new("RGB", (W, H), (5, 5, 10))
    draw = ImageDraw.Draw(img)

    # Dark radial gradient (center brighter)
    for r in range(min(W, H), 0, -20):
        t = r / min(W, H)
        brightness = int(8 + (1 - t) * 30)
        glow_r = int(brightness + palette["glow"][0] * 0.08 * (1 - t))
        glow_g = int(brightness + palette["glow"][1] * 0.08 * (1 - t))
        glow_b = int(brightness + palette["glow"][2] * 0.08 * (1 - t))
        draw.ellipse([W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r],
                     fill=(glow_r, glow_g, glow_b))

    # Speed lines from center-bottom
    cx, cy = W // 2, H * 2 // 3
    for i in range(60):
        angle = random.uniform(-math.pi / 3, math.pi / 3) + math.pi / 2
        length = random.randint(200, 900)
        alpha = random.randint(15, 50)
        ex = int(cx + math.cos(angle) * length)
        ey = int(cy + math.sin(angle) * length)
        draw.line([(cx, cy), (ex, ey)],
                  fill=(palette["accent"][0], palette["accent"][1], palette["accent"][2]),
                  width=random.randint(1, 3))

    return img.filter(ImageFilter.GaussianBlur(1))

def generate_thumbnail(
    title: str,
    subtitle: str = "",
    stat: str = "",           # e.g. "-45%", "800V"
    accent: str = "red",
    output_path: str = "thumbnail.png",
    show_battery: bool = False,
    battery_pct: int = 30,
    show_bolt: bool = False,
    channel_tag: str = "EVCARIX",
):
    random.seed(hash(title) % 9999)
    pal = PALETTES.get(accent, PALETTES["red"])

    img = build_background(pal)
    draw = ImageDraw.Draw(img)

    # ── Decorative corner lines ──────────────────────────────────────────────
    line_color = tuple(min(255, c + 60) for c in pal["accent"])
    for i in range(3):
        d = i * 18
        draw.line([(d, d), (260 + d, d)], fill=line_color, width=2)
        draw.line([(d, d), (d, 260 + d)], fill=line_color, width=2)
        draw.line([(W - d, H - d), (W - 260 - d, H - d)], fill=line_color, width=2)
        draw.line([(W - d, H - d), (W - d, H - 260 - d)], fill=line_color, width=2)

    # ── Channel tag (top-left) ───────────────────────────────────────────────
    font_tag = load_font(FONT_MEDIUM, 38)
    tag_x, tag_y = 54, 60
    draw.rectangle([tag_x - 8, tag_y - 8, tag_x + 240, tag_y + 48], fill=(0, 0, 0, 180))
    draw.rectangle([tag_x - 8, tag_y - 8, tag_x - 2, tag_y + 48], fill=pal["accent"])
    draw.text((tag_x + 8, tag_y + 20), channel_tag, font=font_tag, fill=(220, 220, 220), anchor="lm")

    # ── STAT / big number (center, massive) ─────────────────────────────────
    stat_y = H // 2 - 80
    if stat:
        font_stat = load_font(FONT_BOLD, 320)
        draw_outlined_text(draw, stat, W // 2, stat_y, font_stat,
                           fill=pal["accent"], outline=(0, 0, 0), thickness=14, anchor="mm")

    # ── Battery bar (optional) ───────────────────────────────────────────────
    if show_battery:
        bw, bh = 680, 90
        bx = (W - bw) // 2
        by = stat_y + 200 if stat else H // 2
        draw_battery_bar(draw, bx, by, bw, bh, battery_pct,
                         color_full=pal["accent"], color_low=(255, 50, 50))
        font_pct = load_font(FONT_BOLD, 52)
        draw.text((W // 2, by + bh + 36), f"{battery_pct}% Remaining",
                  font=font_pct, fill=(200, 200, 200), anchor="mm")

    # ── Lightning bolt (optional) ────────────────────────────────────────────
    if show_bolt:
        bolt_y = stat_y - 200 if stat else H // 2 - 250
        draw_lightning_bolt(draw, W // 2, bolt_y, 200, pal["accent"])

    # ── Main TITLE ───────────────────────────────────────────────────────────
    title_lines = wrap_text(title.upper(), 14)
    font_title = load_font(FONT_BOLD, 140 if len(title_lines) <= 2 else 110)
    title_start_y = (H * 3 // 4) if stat else (H // 2 - 100)
    line_h = 150 if len(title_lines) <= 2 else 120
    for i, line in enumerate(title_lines):
        ty = title_start_y + i * line_h
        # Alternating color for punch
        col = pal["accent"] if i % 2 == 0 else (255, 255, 255)
        draw_outlined_text(draw, line, W // 2, ty, font_title,
                           fill=col, outline=(0, 0, 0), thickness=10, anchor="mm")

    # ── Subtitle ─────────────────────────────────────────────────────────────
    if subtitle:
        sub_y = title_start_y + len(title_lines) * line_h + 40
        font_sub = load_font(FONT_MEDIUM, 68)
        sub_lines = wrap_text(subtitle, 20)
        for j, sl in enumerate(sub_lines):
            draw_outlined_text(draw, sl, W // 2, sub_y + j * 78,
                               font_sub, fill=(230, 230, 230), outline=(0, 0, 0), thickness=6, anchor="mm")

    # ── Bottom accent bar ────────────────────────────────────────────────────
    bar_h = 22
    draw.rectangle([0, H - bar_h, W, H], fill=pal["accent"])

    # ── Save ─────────────────────────────────────────────────────────────────
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), "PNG", quality=95)
    print(f"✅ Thumbnail saved → {out}  ({W}x{H})")
    return str(out)

# ── Groq AI layout generator ───────────────────────────────────────────────
def ai_generate(topic: str, api_key: str = None) -> dict:
    """Call Groq API to generate thumbnail parameters from a topic."""
    try:
        from groq import Groq
    except ImportError:
        print("ERROR: groq package not found. Run: pip install groq")
        return {
            "title": topic.upper()[:20],
            "subtitle": "Watch to find out",
            "stat": "",
            "accent": "red",
            "show_battery": False,
            "battery_pct": 50,
            "show_bolt": False,
        }

    if not api_key:
        print("ERROR: GROQ_API_KEY not set")
        return {
            "title": topic.upper()[:20],
            "subtitle": "Watch to find out",
            "stat": "",
            "accent": "red",
            "show_battery": False,
            "battery_pct": 50,
            "show_bolt": False,
        }

    prompt = f"""You are a YouTube thumbnail designer for an EV (electric vehicle) channel called Evcarix.
Given a topic, output ONLY a JSON object (no markdown, no explanation) with these fields:
- title: short punchy ALL-CAPS title (max 4 words, e.g. "RANGE LOST?!", "FAST CHARGING LIE")
- subtitle: supporting text (max 6 words, lowercase, e.g. "Real winter test results")
- stat: optional big number/percentage to show (e.g. "-45%", "800V", "2X") or empty string
- accent: color theme, one of: red, cyan, yellow, green, orange
- show_battery: true/false (show battery bar graphic)
- battery_pct: 0-100 (if show_battery is true, how full)
- show_bolt: true/false (show lightning bolt, good for charging topics)

Topic: {topic}

Respond ONLY with the JSON object."""

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw = response.choices[0].message.content
        # Strip markdown fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"⚠️  AI generation failed: {e}", file=sys.stderr)
        return {
            "title": topic.upper()[:20],
            "subtitle": "Watch to find out",
            "stat": "",
            "accent": "red",
            "show_battery": False,
            "battery_pct": 50,
            "show_bolt": False,
        }

# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Generate EV YouTube Shorts thumbnail")
    parser.add_argument("--title",    default="", help="Main title text")
    parser.add_argument("--subtitle", default="", help="Subtitle / supporting text")
    parser.add_argument("--stat",     default="", help="Big stat/number overlay (e.g. -45%%)")
    parser.add_argument("--accent",   default="red", choices=list(PALETTES.keys()), help="Color accent")
    parser.add_argument("--battery",  action="store_true", help="Show battery bar")
    parser.add_argument("--battery-pct", type=int, default=30, help="Battery percentage (0-100)")
    parser.add_argument("--bolt",     action="store_true", help="Show lightning bolt icon")
    parser.add_argument("--channel",  default="EVCARIX", help="Channel tag shown on thumbnail")
    parser.add_argument("--output",   default="thumbnail.png", help="Output file path")
    parser.add_argument("--json",     default="", help="JSON string with all params")
    parser.add_argument("--groq",     default="", help="Topic — let Groq AI design the thumbnail")
    parser.add_argument("--api-key",  default=os.environ.get("GROQ_API_KEY", ""), help="Groq API key")
    args = parser.parse_args()

    # ── Mode 1: AI-designed from topic
    if args.groq:
        print(f"🤖 Asking Groq to design thumbnail for: {args.groq}")
        params = ai_generate(args.groq, args.api_key)
        print(f"📐 AI params: {json.dumps(params, ensure_ascii=False)}")
        generate_thumbnail(
            title=params.get("title", args.groq),
            subtitle=params.get("subtitle", ""),
            stat=params.get("stat", ""),
            accent=params.get("accent", "red"),
            output_path=args.output,
            show_battery=params.get("show_battery", False),
            battery_pct=params.get("battery_pct", 30),
            show_bolt=params.get("show_bolt", False),
            channel_tag=args.channel,
        )
        return

    # ── Mode 2: JSON params
    if args.json:
        params = json.loads(args.json)
        generate_thumbnail(
            title=params.get("title", ""),
            subtitle=params.get("subtitle", ""),
            stat=params.get("stat", ""),
            accent=params.get("accent", "red"),
            output_path=args.output,
            show_battery=params.get("show_battery", False),
            battery_pct=params.get("battery_pct", 30),
            show_bolt=params.get("show_bolt", False),
            channel_tag=params.get("channel", args.channel),
        )
        return

    # ── Mode 3: Direct CLI args
    if not args.title:
        parser.print_help()
        sys.exit(1)

    generate_thumbnail(
        title=args.title,
        subtitle=args.subtitle,
        stat=args.stat,
        accent=args.accent,
        output_path=args.output,
        show_battery=args.battery,
        battery_pct=args.battery_pct,
        show_bolt=args.bolt,
        channel_tag=args.channel,
    )

if __name__ == "__main__":
    main()
