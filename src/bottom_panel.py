import os
import re
import random
import subprocess
import tempfile
import logging

logger = logging.getLogger("BottomPanel")

THEME = {
    "electric_vehicle":        ("#000d1a", "#00D4FF"),
    "artificial_intelligence": ("#0d001a", "#8B00FF"),
    "robotics":                ("#001a00", "#00FF88"),
    "battery_tech":            ("#1a0800", "#FF6B00"),
    "future_tech":             ("#0a0010", "#FF00FF"),
    "default":                 ("#000d1a", "#00D4FF"),
}

STATS = {
    "electric_vehicle": [
        {"icon": "⚡", "value": "+300%", "label": "EV Sales Growth 2026"},
        {"icon": "🔋", "value": "500 MI", "label": "New Range Record"},
        {"icon": "🌍", "value": "$0",     "label": "Gas Car Future Value"},
    ],
    "battery_tech": [
        {"icon": "🔋", "value": "1M KM",  "label": "LFP Lifespan Claim"},
        {"icon": "⚡", "value": "10 MIN", "label": "Future Charge Time"},
        {"icon": "📉", "value": "-45%",   "label": "Winter Range Loss"},
    ],
    "artificial_intelligence": [
        {"icon": "🤖", "value": "GPT-5",  "label": "Latest AI Model"},
        {"icon": "⚡", "value": "10x",    "label": "Speed vs Human"},
        {"icon": "🌍", "value": "2030",   "label": "AGI Prediction"},
    ],
    "robotics": [
        {"icon": "🦾", "value": "40%",    "label": "Jobs Automated"},
        {"icon": "⚡", "value": "24/7",   "label": "Robot Uptime"},
        {"icon": "🌍", "value": "$1.5T",  "label": "Robotics Market"},
    ],
    "future_tech": [
        {"icon": "🚀", "value": "2030",   "label": "Flying Cars ETA"},
        {"icon": "⚡", "value": "1 TW",   "label": "Solar Capacity"},
        {"icon": "🌍", "value": "8B",     "label": "People Connected"},
    ],
    "default": [
        {"icon": "⚡", "value": "+300%",  "label": "EV Growth 2026"},
        {"icon": "🔋", "value": "500 MI", "label": "Range Record"},
        {"icon": "🌍", "value": "2030",   "label": "Full EV Target"},
    ],
}

STAT_COLORS = ["#00D4FF", "#FF6B00", "#00FF88"]


def _safe_text(text: str, max_words: int = 10) -> str:
    clean = re.sub(r"(?i)welcome to ev[-\s]?care[-\s]?icks\.?\s*", "", text)
    clean = re.sub(r"[^a-zA-Z0-9 .,!?%\-]", " ", clean)
    words = clean.split()[:max_words]
    return " ".join(words).upper()


def _build_html(topic: str, subtitle_text: str, W: int, H: int) -> str:
    bg_color, acc_color = THEME.get(topic, THEME["default"])
    stats = STATS.get(topic, STATS["default"])
    speaking = _safe_text(subtitle_text, max_words=10)

    stat_cards_html = ""
    for i, stat in enumerate(stats):
        color = STAT_COLORS[i % len(STAT_COLORS)]
        stat_cards_html += f"""
        <div class="stat-card" style="border-left-color:{color}">
          <div class="stat-icon">{stat['icon']}</div>
          <div class="stat-info">
            <div class="stat-value" style="color:{color};text-shadow:0 0 12px {color}88">{stat['value']}</div>
            <div class="stat-label">{stat['label']}</div>
          </div>
        </div>"""

    left_w  = int(W * 0.54)
    right_w = W - left_w
    body_h  = H - 44

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;background:{bg_color};font-family:Arial,sans-serif;overflow:hidden}}
.wrap{{width:{W}px;height:{H}px;position:relative;overflow:hidden;
  background:linear-gradient(160deg,{bg_color} 0%,#001020 60%,#000820 100%)}}
.top-line{{position:absolute;top:0;left:0;right:0;height:4px;
  background:linear-gradient(90deg,{acc_color},{acc_color}88,{acc_color})}}
.left{{position:absolute;left:0;top:4px;width:{left_w}px;height:{body_h}px;
  display:flex;flex-direction:column;justify-content:center;
  padding:14px 22px 14px 22px;
  border-right:1px solid {acc_color}33}}
.now-label{{font-size:11px;font-weight:700;color:{acc_color}99;
  letter-spacing:4px;text-transform:uppercase;margin-bottom:10px}}
.speaking-text{{font-size:26px;font-weight:900;color:#fff;line-height:1.3;
  text-shadow:0 0 20px {acc_color}44}}
.right{{position:absolute;right:0;top:4px;width:{right_w}px;height:{body_h}px;
  display:flex;flex-direction:column;justify-content:center;
  padding:10px 16px;gap:8px}}
.stat-card{{background:rgba(0,20,40,0.85);border-left:4px solid {acc_color};
  padding:9px 12px;display:flex;align-items:center;gap:10px}}
.stat-icon{{font-size:20px}}
.stat-info{{flex:1}}
.stat-value{{font-size:22px;font-weight:900;line-height:1}}
.stat-label{{font-size:10px;font-weight:700;color:rgba(255,255,255,0.5);
  letter-spacing:2px;text-transform:uppercase;margin-top:2px}}
.bottom{{position:absolute;bottom:0;left:0;right:0;height:40px;
  background:rgba(0,0,0,0.92);border-top:2px solid {acc_color}33;
  display:flex;align-items:center;padding:0 18px;gap:14px}}
.brand{{font-size:15px;font-weight:900;color:{acc_color};letter-spacing:5px;white-space:nowrap}}
.progress-wrap{{flex:1;height:5px;background:rgba(255,255,255,0.1);
  border-radius:3px;overflow:hidden}}
.progress-fill{{width:50%;height:100%;
  background:linear-gradient(90deg,{acc_color},{acc_color}88);border-radius:3px}}
.ev-tag{{font-size:10px;font-weight:700;color:rgba(255,255,255,0.35);
  letter-spacing:2px;white-space:nowrap}}
.vdivider{{position:absolute;left:{left_w}px;top:8px;bottom:48px;width:1px;
  background:linear-gradient(180deg,transparent,{acc_color}44 30%,{acc_color}22 70%,transparent)}}
</style></head><body>
<div class="wrap">
  <div class="top-line"></div>
  <div class="vdivider"></div>
  <div class="left">
    <div class="now-label">NOW SPEAKING</div>
    <div class="speaking-text">{speaking}</div>
  </div>
  <div class="right">{stat_cards_html}</div>
  <div class="bottom">
    <div class="brand">EVCARIX</div>
    <div class="progress-wrap"><div class="progress-fill"></div></div>
    <div class="ev-tag">EV DATA AND INSIGHTS</div>
  </div>
</div></body></html>"""


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

    try:
        html = _build_html(topic, subtitle_text, W, H)

        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(html)
            tmp_html = f.name

        jpg_path = output_path.replace(".mp4", "_panel.jpg")
        cmd_img  = [
            "wkhtmltoimage",
            "--width",  str(W),
            "--height", str(H),
            "--quality", "92",
            "--zoom", "1",
            "--disable-smart-width",
            tmp_html, jpg_path
        ]
        r_img = subprocess.run(cmd_img, capture_output=True, text=True, timeout=30)
        try:
            os.unlink(tmp_html)
        except:
            pass

        if r_img.returncode != 0 or not os.path.exists(jpg_path):
            logger.error(f"[BottomPanel] wkhtmltoimage failed: {r_img.stderr[-200:]}")
            return _fallback_panel(topic, duration, output_path, W, H)

        safe_dur = round(max(duration, 1.0), 2)
        cmd_vid  = [
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
        r_vid = subprocess.run(cmd_vid, capture_output=True, text=True, timeout=120)

        try:
            os.remove(jpg_path)
        except:
            pass

        if r_vid.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            logger.info(f"[BottomPanel] {output_path} ({size//1024}KB)")
            return output_path

        logger.error(f"[BottomPanel] MP4 failed: {r_vid.stderr[-200:]}")

    except Exception as e:
        logger.error(f"[BottomPanel] Exception: {e}")

    return _fallback_panel(topic, duration, output_path, W, H)


def _fallback_panel(topic: str, duration: float, output_path: str, W: int, H: int) -> str | None:
    bg_map = {
        "electric_vehicle": "0x001833",
        "battery_tech":     "0x1a0800",
        "artificial_intelligence": "0x0d001a",
        "robotics":         "0x001a00",
        "future_tech":      "0x0a0010",
    }
    bg  = bg_map.get(topic, "0x001020")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg}:size={W}x{H}:rate=24",
        "-t", str(round(max(duration, 1.0), 2)),
        "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-an",
        output_path
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    if r.returncode == 0 and os.path.exists(output_path):
        logger.info(f"[BottomPanel] Fallback ok: {output_path}")
        return output_path
    return None
