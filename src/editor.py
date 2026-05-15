import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        """
        Videoları 'filter_complex' kullanarak birleştirir. 
        Zaman damgası (timestamp) hatalarını ve donmaları %100 engeller.
        """
        try:
            logger.info(f"[Editor] Kırılmaz HD Montaj: {len(clips_paths)} klip")
            
            # 1. Girişleri hazırla
            inputs = []
            filter_str = ""
            for i, clip in enumerate(clips_paths):
                inputs.extend(["-i", os.path.abspath(clip)])
                # Her klibi 1080x1920'ye ölçekle ve 30fps'e sabitle
                filter_str += f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
            
            # 2. Clipleri birleştir
            for i in range(len(clips_paths)):
                filter_str += f"[v{i}]"
            filter_str += f"concat=n={len(clips_paths)}:v=1:a=0[vout]"

            temp_video = "temp_merged_video.mp4"
            
            # Pass 1: Görüntüleri birleştir ve standartlaştır
            cmd_v = [
                "ffmpeg", "-y"
            ] + inputs + [
                "-filter_complex", filter_str,
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-threads", "0", "-an", temp_video
            ]
            
            logger.info("[Editor] Görüntü birleştirme (Filter Complex)...")
            subprocess.run(cmd_v, check=True)

            # Pass 2: Sesle birleştir
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", output_path
            ]
            
            logger.info("[Editor] Ses ekleniyor...")
            subprocess.run(final_cmd, check=True)

            # Temizlik
            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Video başarıyla üretildi: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Montaj hatası: {e}")
            return False
