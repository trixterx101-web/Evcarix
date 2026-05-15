import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        try:
            logger.info(f"[Editor] FFmpeg ile montaj başlatılıyor: {len(clips_paths)} klip")

            concat_list = "clips_to_merge.txt"
            with open(concat_list, "w") as f:
                for clip in clips_paths:
                    f.write(f"file '{os.path.abspath(clip)}'\n")

            temp_video = "temp_merged_video.mp4"
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c", "copy", temp_video
            ]
            subprocess.run(concat_cmd, capture_output=True)

            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", output_path
            ]

            logger.info("[Editor] Final render (FFmpeg)...")
            result = subprocess.run(final_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                logger.error(f"[Editor] FFmpeg hatası: {result.stderr}")
                return False

            if os.path.exists(concat_list): os.remove(concat_list)
            if os.path.exists(temp_video): os.remove(temp_video)

            logger.info(f"[Editor] ✅ Video hazırlandı: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Kritik hata: {e}")
<<<<<<< Updated upstream
            return False
=======
            return False
>>>>>>> Stashed changes
