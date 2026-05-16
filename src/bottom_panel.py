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

def _wrap_text(text: str, max_chars: int = 32) -> list[str]:
    """Wrap text into lines of max_chars, return max 3 lines."""
    clean = re.sub(r"[^A-Z0-9 .,!?%\-]", "", text.upper()).strip()
    lines = textwrap.wrap(clean, width=max_chars)
    return lines[:3]

def _ffmpeg_safe(text: str) -> str:
    """Escape special chars for FFmpeg drawtext."""
    return text.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")

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
    fg_r = min(255, ar + 30)
    fg_g = min(255, ag + 30)
    fg_b = min(255, ab + 30)

    acc_ff = "#%02x%02x%02x" % _hex_to_rgb(acc_color)
    bg_ff  = "#%02x%02x%02x" % _hex_to_rgb(bg_color)
    fg_ff  = "#%02x%02x%02x" % (fg_r, fg_g, fg_b)

    # ── Subtitle: extract first ~10 words from script, wrap neatly ───────────
    # Strip the "Welcome to EV-care-icks." opener, take the meaningful part
    clean_text = re.sub(r"(?i)welcome to ev[-\s]?care[-\s]?icks\.?\s*", "", subtitle_text)
    # Take first 10 words only — panel is small
    first_words = " ".join(clean_text.split()[:10])
    lines = _wrap_text(first_words, max_chars=28)

    # Font sizes based on panel height — smaller for long video side panel
    font_size  = 38 if W >= 1000 else 32
    line_gap   = font_size + 10

    # Vertical center for text block
    text_block_h = len(lines) * line_gap
    y_start = (H // 2) - (text_block_h // 2) - 20
    y_brand = H - 48
    y_bar   = H - 10

    dt_filters = []

    # Subtitle lines — timed fade-in per line
    words_per_sec = max(len(subtitle_text.split()) / max(duration, 1), 0.3)
    word_idx = 0
    for i, line in enumerate(lines):
        t_in  = round(word_idx / words_per_sec, 1)
        t_out = round(duration, 1)
        word_idx += len(line.split())
        y_pos = y_start + i * line_gap
        safe  = _ffmpeg_safe(line)
        dt_filters.append(
            f"drawtext=text='{safe}'"
            f":fontsize={font_size}:fontcolor=white@0.95"
            f":x=(w-tw)/2:y={y_pos}"
            f":shadowcolor=black@0.85:shadowx=2:shadowy=2"
            f":enable='between(t,{t_in},{t_out})'"
        )

    # Brand watermark — always visible
    dt_filters.append(
        f"drawtext=text='Evcarix'"
        f":fontsize=22:fontcolor={acc_ff}@0.9"
        f":x=20:y={y_brand}"
        f":shadowcolor=black@0.6:shadowx=1:shadowy=1"
    )

    # Progress bar
    dt_filters.append(
        f"drawbox=x=0:y={y_bar}:w='iw*min(t\\/{round(duration,2)},1)':h=6"
        f":color={acc_ff}:t=fill"
    )

    all_filters = ",".join(dt_filters)

    filter_graph = (
        f"[0:v]format=yuv420p[base];"
        f"[1:v]format=yuv420p[acc];"
        f"[base][acc]blend=all_mode=multiply:all_opacity=0.25[bg];"
        f"[bg]{all_filters}[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={bg_ff}:size={W}x{H}:rate=24",
        "-f", "lavfi", "-i", f"color=c={fg_ff}:size={W}x{H}:rate=24",
        "-filter_complex", filter_graph,
        "-map", "[v]",
        "-t", str(round(duration, 2)),
        "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an",
        "-threads", "2",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(output_path):
            logger.info(f"[BottomPanel] ✅ {output_path}")
            return output_path
        logger.error(f"[BottomPanel] FFmpeg error: {result.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        logger.error("[BottomPanel] Timeout 300s")
    except Exception as e:
        logger.error(f"[BottomPanel] Failed: {e}")

    return None
