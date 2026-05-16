import os
import random
import subprocess
import logging
import re

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
    h = h.replace("0x","").replace("#","")
    return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)

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
    fg_r = min(255, ar + 40)
    fg_g = min(255, ag + 40)
    fg_b = min(255, ab + 40)

    acc_ff = "#%02x%02x%02x" % _hex_to_rgb(acc_color)
    bg_ff  = "#%02x%02x%02x" % _hex_to_rgb(bg_color)
    fg_ff  = "#%02x%02x%02x" % (fg_r, fg_g, fg_b)

    # Subtitle: wrap into max 2 lines
    words = re.sub(r"[^A-Z0-9 .,!?%\-]", "", subtitle_text.upper()).split()
    line1_words, line2_words = [], []
    for w in words:
        if sum(len(x)+1 for x in line1_words) + len(w) <= 36:
            line1_words.append(w)
        elif sum(len(x)+1 for x in line2_words) + len(w) <= 36:
            line2_words.append(w)
    line1 = " ".join(line1_words)
    line2 = " ".join(line2_words)

    y_center = int(H * 0.42)
    y_line1  = y_center - (28 if line2 else 0)
    y_line2  = y_center + 38
    y_brand  = H - 55
    y_bar    = H - 12

    dt_filters = []
    if line1:
        dt_filters.append(
            f"drawtext=text='{line1}':fontsize=46:fontcolor=white"
            f":x=(w-tw)/2:y={y_line1}"
            f":shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )
    if line2:
        dt_filters.append(
            f"drawtext=text='{line2}':fontsize=46:fontcolor=white"
            f":x=(w-tw)/2:y={y_line2}"
            f":shadowcolor=black@0.8:shadowx=2:shadowy=2"
        )
    dt_filters.append(
        f"drawtext=text='EVCARIX':fontsize=26:fontcolor={acc_ff}@0.8:x=28:y={y_brand}"
    )
    dt_filters.append(
        f"drawbox=x=0:y={y_bar}:w='iw*min(t\\/{duration},1)':h=8:color={acc_ff}:t=fill"
    )

    all_filters = ",".join(dt_filters)

    filter_graph = (
        f"[0:v]format=yuv420p[base];"
        f"[1:v]format=yuv420p[accent];"
        f"[base][accent]blend=all_mode=multiply:all_opacity=0.3[blended];"
        f"[blended]{all_filters}[v]"
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
            logger.info(f"[BottomPanel] Generated: {output_path}")
            return output_path
        logger.error(f"[BottomPanel] FFmpeg error: {result.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        logger.error("[BottomPanel] Timeout after 300s")
    except Exception as e:
        logger.error(f"[BottomPanel] Failed: {e}")

    return None
