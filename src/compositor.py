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
            # 1080x1920 — top video (footage) + bottom panel with subtitles
            W, top_h, bot_h = 1080, 1284, 636  # both even, total = 1920
            filter_complex = (
                f"[0:v]scale={W}:{top_h}:force_original_aspect_ratio=increase,"
                f"crop={W}:{top_h},setsar=1[top];"
                f"[1:v]scale={W}:{bot_h}:force_original_aspect_ratio=disable,setsar=1[bot];"
                f"[top][bot]vstack=inputs=2[v]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", top_video,
                "-i", bottom_panel,
                "-i", audio_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "2:a",
                "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", output_path
            ]
        else:
            # LONG VIDEO: full 1920x1080, NO side panel — footage takes full screen
            # Subtitles are burned in by editor.py
            # bottom_panel is ignored for long format
            filter_complex = (
                "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,"
                "crop=1920:1080,setsar=1[v]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", top_video,
                "-i", audio_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-crf", "22", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest", output_path
            ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0 and os.path.exists(output_path):
                logger.info(f"[Compositor] ✅ {output_path}")
                return output_path
            logger.error(f"[Compositor] FFmpeg error: {result.stderr[-400:]}")
        except subprocess.TimeoutExpired:
            logger.error("[Compositor] Timeout 600s")
        except Exception as e:
            logger.error(f"[Compositor] Failed: {e}")
        return None
