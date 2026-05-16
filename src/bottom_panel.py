import os
import random
import subprocess
import logging
import re
from pathlib import Path

logger = logging.getLogger("BottomPanel")

EFFECTS = {
    "tunnel": "geq=r='128+127*sin(hypot(X-W/2+{cx},Y-H/2+{cy})/{f1}-T*{s1})':g='128+127*sin(hypot(X-W/2,Y-H/2)/{f2}-T*{s2})':b='200+55*cos(T*{s3})'",
    "plasma": "geq=r='128+{r}*sin(2*PI*(X/W+T/{s1}))':g='128+{g}*cos(2*PI*(Y/H+T/{s2}))':b='200+55*sin(2*PI*(X/W+Y/H+T/{s3}))'",
    "wave":   "geq=r='128+{r}*sin(X/{f1}+T*{s1})*cos(Y/{f2}+T*{s2})':g='128+{g}*cos(X/{f2}-T*{s2})':b='200+55*sin((X+Y)/{f3}+T*{s3})'",
    "spiral": "geq=r='128+{r}*sin(10*atan2(Y-H/2+0.001,X-W/2+0.001)+hypot(X-W/2,Y-H/2+0.001)/{f1}-T*{s1})':g='128+{g}*cos(8*atan2(Y-H/2+0.001,X-W/2+0.001)-T*{s2})':b='200+55*sin(T*{s3})'",
    "grid":   "geq=r='200*lt(mod(X+T*{s1}*30,{grid}),3)':g='255*lt(mod(Y+T*{s2}*20,{grid}),3)':b='255*(lt(mod(X,{grid}),3)+lt(mod(Y,{grid}),3))'",
    "stars":  "geq=lum='255*gt(sin(X*{f1}+Y*{f2}+T*{s1})*cos(X*{f3}-Y*{f1}),0.97)':cb=128:cr=128",
    "matrix": "geq=lum='255*gt(sin(floor(X/{grid})*{f1}+T*{s1}*10),0.96)':cb='100':cr='80'",
    "neon":   "geq=r='255*gt(sin(X/{f1}+T*{s1}),0.97)+128*sin(Y/{f2}+T*{s2})':g='200*gt(cos(Y/{f2}+T*{s2}),0.97)':b='255*sin(X/{f3}+T*{s3})'"
}

TOPIC_EFFECTS = {
    "electric_vehicle": ["tunnel", "wave", "neon"],
    "artificial_intelligence": ["matrix", "grid", "stars"],
    "robotics": ["grid", "neon", "wave"],
    "battery_tech": ["plasma", "tunnel", "neon"],
    "future_tech": ["stars", "spiral", "plasma"]
}

THEME_COLORS = {
    "electric_vehicle": ("0x001833", "0x00D4FF"),
    "artificial_intelligence": ("0x0D001A", "0x8B00FF"),
    "robotics": ("0x001A00", "0x00FF88"),
    "battery_tech": ("0x1A0800", "0xFF6B00"),
    "future_tech": ("0x0A0A1E", "0xFF00FF"),
}

def generate_bottom_panel(
    topic: str,
    subtitle_text: str,
    duration: float,
    output_path: str,
    panel_size: tuple = (1080, 635)
) -> str | None:
    """Generate animated bottom panel with 3D effect + subtitle text."""
    W, H = panel_size
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Random parameters
    p = {
        "r": random.randint(80, 127),
        "g": random.randint(60, 110),
        "f1": round(random.uniform(20, 60), 1),
        "f2": round(random.uniform(25, 70), 1),
        "f3": round(random.uniform(15, 45), 1),
        "s1": round(random.uniform(1.5, 4.0), 2),
        "s2": round(random.uniform(2.0, 5.0), 2),
        "s3": round(random.uniform(1.0, 3.0), 2),
        "cx": random.randint(-100, 100),
        "cy": random.randint(-50, 50),
        "grid": random.choice([30, 40, 50, 60, 80]),
    }
    
    effect_name = random.choice(TOPIC_EFFECTS.get(topic, ["plasma", "tunnel", "wave"]))
    effect_formula = EFFECTS[effect_name].format(**p)
    bg_color, acc_color = THEME_COLORS.get(topic, ("0x001833", "0x00D4FF"))
    
    # Subtitle animation logic
    words = subtitle_text.upper().split()
    subtitle_filters = []
    words_per_sec = max(len(words) / max(duration, 1), 0.5)
    
    # We use a limited window of words to avoid overcrowding, or just let them stay
    for i, word in enumerate(words[:15]): # Limit to 15 words for visibility
        t_start = i / words_per_sec
        t_end = duration # Accumulate words as they are spoken
        safe_word = re.sub(r"[^A-Z0-9 .,!?%]", "", word)[:15]
        if not safe_word: continue
        
        # Shift Y position slightly for each word to create a "scrolling" feel if they accumulate
        # Or just keep them in the center if they replace each other.
        # User asked for "scrolling subtitles", but the snippet showed fixed position.
        # I'll keep them centered but let them stay as requested.
        subtitle_filters.append(
            f"drawtext=text='{safe_word}':fontsize=52:fontcolor=white:x=(w-tw)/2:y=H*0.4+{i*5}:enable='between(t,{t_start:.1f},{t_end:.1f})':shadowcolor=black@0.9:shadowx=3:shadowy=3"
        )
    
    progress = f"drawbox=x=0:y=H-10:w='iw*t/{duration}':h=10:color={acc_color}:t=fill"
    brand = f"drawtext=text='⚡ EVCARIX':fontsize=32:fontcolor={acc_color}@0.7:x=30:y=H-60"
    
    # FFmpeg command — geq must be used as a filter, not as a lavfi input source
    filter_graph = (
        f"[0:v]split[bg][tmp];"
        f"[tmp]{effect_formula},format=yuv420p[fx];"
        f"[bg]format=yuv420p[bgf];"
        f"[bgf][fx]blend=all_mode=screen[out];"
        f"[out]{','.join([progress, *subtitle_filters, brand])}[v]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={bg_color}:size={W}x{H}:rate=30",
        "-filter_complex", filter_graph,
        "-map", "[v]",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-an",
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            return output_path
        logger.error(f"[BottomPanel] FFmpeg error: {result.stderr[-300:]}")
    except Exception as e:
        logger.error(f"[BottomPanel] Generation failed: {e}")
    
    return None
