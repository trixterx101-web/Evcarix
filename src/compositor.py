import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Compositor")

class VideoCompositor:
    def __init__(self):
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

    def compose_split_screen(
        self,
        top_video: str,
        bottom_panel: str,
        audio_path: str,
        output_filename: str,
        video_format: str = "shorts"
    ) -> str | None:
        """Stack top footage and bottom panel into final video."""
        output_path = os.path.join(self.output_dir, output_filename)
        
        if video_format == "shorts":
            # 1080x1920
            top_h, bot_h, W = 1285, 635, 1080
            filter_complex = (
                f"[0:v]scale={W}:{top_h}:force_original_aspect_ratio=increase,crop={W}:{top_h}[top];"
                f"[1:v]scale={W}:{bot_h}[bot];"
                f"[top][bot]vstack=inputs=2[v]"
            )
        else:
            # 1920x1080
            left_w, right_w, H = 1152, 768, 1080
            filter_complex = (
                f"[0:v]scale={left_w}:{H}:force_original_aspect_ratio=increase,crop={left_w}:{H}[left];"
                f"[1:v]scale={right_w}:{H}[right];"
                f"[left][right]hstack=inputs=2[v]"
            )

        cmd = [
            "ffmpeg", "-y",
            "-i", top_video,
            "-i", bottom_panel,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "2:a",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"[Compositor] ✅ Final video produced: {output_path}")
                return output_path
            logger.error(f"[Compositor] FFmpeg error: {result.stderr[-300:]}")
        except Exception as e:
            logger.error(f"[Compositor] Composition failed: {e}")
            
        return None
