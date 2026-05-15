import subprocess
import logging
import os

logger = logging.getLogger("Fallback")

COLOR_MAP = {
    "electric_vehicle": "0x00D4FF",
    "artificial_intelligence": "0x8B00FF", 
    "robotics": "0x00FF88",
    "battery_tech": "0xFF6B00",
    "future_tech": "0xFF00FF",
    "default": "0x0A0A0F"
}

def generate_fallback_video(duration: int, topic: str, output_path: str) -> str:
    """
    Generate a simple animated background video using only FFmpeg.
    Uses FFmpeg lavfi filters for animated gradient/plasma effect.
    """
    try:
        clean_topic = topic.lower().replace(" ", "_")
        color = COLOR_MAP.get(clean_topic, COLOR_MAP["default"])
        
        logger.info(f"[Fallback] Generating animated video for {topic} ({color})...")
        
        # Create a more dynamic plasma effect in the background
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={color}:size=1080x1920:rate=30",
            "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30",
            "-filter_complex", "[0:v][1:v]blend=all_mode='overlay':all_opacity=0.1",
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except Exception as e:
        logger.error(f"[Fallback] Video generation failed: {e}")
        # Simplest solid color fallback
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:size=1080x1920:rate=30",
            "-t", str(duration), "-c:v", "libx264", output_path
        ])
        return output_path

def generate_whoosh_sfx(output_path: str) -> str:
    """Generates a simple synthetic whoosh-like sound if no SFX found."""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anoisesrc=d=0.5:c=white:amp=0.2",
            "-af", "afade=t=in:ss=0:d=0.2,afade=t=out:st=0.3:d=0.2",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path
    except:
        return ""
