import os
import random
import subprocess
import logging
import re
import textwrap

logger = logging.getLogger("BottomPanel")

THEME_COLORS = {
    "electric_vehicle":        ("0x001833", "0x00D4FF"),
    "artificial_intelligence": ("0x0D001A", "0x8B00FF"),
    "robotics":                ("0x001A00", "0x00FF88"),
    "battery_tech":            ("0x1A0800", "0xFF6B00"),
    "future_tech":             ("0x0A0A1E", "0xFF00FF"),
    "default":                 ("0x001020", "0x00AAFF"),
}

def _hex_to_rgb(h: str):
    h = h.replace("0x", "").replace("#", "")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _ffmpeg_safe(text: str) -> str:
    """FFmpeg drawtext için güvenli metin."""
    text = re.sub(r"[^A-Z0-9 .,!?%\-]", "", text.upper())
    text = text[:30].strip()
    text = text.replace("'", "").replace(":", "").replace("\\", "")
    return text

def _get_subtitle_lines(subtitle_text: str) -> list:
    """Scriptten max 3 kısa satır çıkar."""
    clean = re.sub(r"(?i)welcome to ev[-\s]?care[-\s]?icks\.?\s*", "", subtitle_text)
    clean = re.sub(r"[^a-zA-Z0-9 .,!?%\-]", " ", clean)
    words = clean.split()[:15]  # Sadece ilk 15 kelime
    text  = " ".join(words).upper()
    lines = textwrap.wrap(text, width=22)
    return lines[:3]

def generate_bottom_panel(
    topic: str,
    subtitle_text: str,
    duration: float,
    output_path: str,
    panel_size: tuple = (1080, 635)
) -> str | None:
    W, H = panel_size
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    bg_color, acc_color = THEME_COLORS.get(topic, THEME_COLORS["default"])

    ar, ag, ab = _hex_to_rgb(acc_color)
    acc_ff = "#%02x%02x%02x" % (ar, ag, ab)
    bg_rgb  = _hex_to_rgb(bg_color)
    bg_ff   = "#%02x%02x%02x" % bg_rgb

    lines     = _get_subtitle_lines(subtitle_text)
    font_size = 42
    line_gap  = font_size + 12

    text_h  = len(lines) * line_gap
    y_start = max(40, (H // 2) - (text_h // 2) - 30)
    y_brand = H - 44
    y_bar   = H - 8

    # ── Basit, kısa filter_complex ────────────────────────────
    # Sadece statik metin — kelime kelime timing YOK
    # Bu FFmpeg komutunu patlatmaz
    dt_parts = []

    for i, line in enumerate(lines):
        safe = _ffmpeg_safe(line)
        if not safe:
            continue
        y = y_start + i * line_gap
        dt_parts.append(
            f"drawtext=text='{safe}'"
            f":fontsize={font_size}"
            f":fontcolor=white@0.95"
            f":x=(w-tw)/2:y={y}"
            f":shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )

    # Evcarix branding
    dt_parts.append(
        f"drawtext=text='EVCARIX'"
        f":fontsize=24"
        f":fontcolor={acc_ff}@0.9"
        f":x=18:y={y_brand}"
        f":shadowcolor=black@0.6:shadowx=1:shadowy=1"
    )

    # Progress bar — animasyonlu
    safe_dur = round(max(duration, 1.0), 2)
    dt_parts.append(
        f"drawbox=x=0:y={y_bar}"
        f":w='iw*min(t\\/{safe_dur}\\,1)'"
        f":h=7:color={acc_ff}:t=fill"
    )

    # Accent top border
    dt_parts.append(
        f"drawbox=x=0:y=0:w=iw:h=5:color={acc_ff}:t=fill"
    )

    vf = ",".join(dt_parts)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg_ff}:size={W}x{H}:rate=24",
        "-vf", vf,
        "-t", str(safe_dur),
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-an",
        "-threads", "2",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            logger.info(f"[BottomPanel] ✅ {output_path} ({size//1024}KB)")
            return output_path

        # Hata varsa stderr'i logla
        err = result.stderr[-400:] if result.stderr else "unknown"
        logger.error(f"[BottomPanel] FFmpeg failed: {err}")

        # ── Ultra basit fallback ───────────────────────────────
        fallback_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={bg_ff}:size={W}x{H}:rate=24",
            "-t", str(safe_dur),
            "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-an",
            output_path
        ]
        result2 = subprocess.run(fallback_cmd, capture_output=True, timeout=60)
        if result2.returncode == 0 and os.path.exists(output_path):
            logger.info(f"[BottomPanel] ✅ Fallback panel: {output_path}")
            return output_path

    except subprocess.TimeoutExpired:
        logger.error("[BottomPanel] Timeout 120s")
    except Exception as e:
        logger.error(f"[BottomPanel] Exception: {e}")

    return None
