import os
import subprocess
import logging

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
        output_path = os.path.join(self.output_dir, output_filename)

        if video_format == "shorts":
            # 1080x1920 — dimensions MUST be even for libx264
            W      = 1080
            top_h  = 1284   # even (was 1285)
            bot_h  = 636    # even (was 635) — total = 1920
            filter_complex = (
                f"[0:v]scale={W}:{top_h}:force_original_aspect_ratio=increase,"
                f"crop={W}:{top_h},setsar=1[top];"
                f"[1:v]scale={W}:{bot_h}:force_original_aspect_ratio=disable,setsar=1[bot];"
                f"[top][bot]vstack=inputs=2[v]"
            )
        else:
            # 1920x1080
            H       = 1080
            left_w  = 1152  # even
            right_w = 768   # even
            filter_complex = (
                f"[0:v]scale={left_w}:{H}:force_original_aspect_ratio=increase,"
                f"crop={left_w}:{H},setsar=1[left];"
                f"[1:v]scale={right_w}:{H}:force_original_aspect_ratio=disable,setsar=1[right];"
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
            "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"[Compositor] Final video: {output_path}")
                return output_path
            logger.error(f"[Compositor] FFmpeg error: {result.stderr[-400:]}")
        except subprocess.TimeoutExpired:
            logger.error("[Compositor] Timeout after 300s")
        except Exception as e:
            logger.error(f"[Compositor] Failed: {e}")

        return None
