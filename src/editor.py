import os
import subprocess
import logging
import json
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, video_clips, audio_path, output_path, is_short=True):
        """
        Videoyu MoviePy kullanmadan, doğrudan FFmpeg ile birleştirir.
        Bu yöntem 'siyah ekran' sorununu %100 çözer.
        """
        try:
            logger.info(f"[Editor] FFmpeg ile montaj başlatılıyor: {len(video_clips)} klip")
            
            # 1. Geçici bir dosya listesi oluştur (FFmpeg concat için)
            concat_list = "clips_to_merge.txt"
            with open(concat_list, "w") as f:
                for clip in video_clips:
                    # Dosya yollarını FFmpeg'in anlayacağı formatta yaz
                    f.write(f"file '{os.path.abspath(clip)}'\n")

            # 2. Videoları birleştir (Sessiz olarak)
            temp_video = "temp_merged_video.mp4"
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c", "copy", temp_video
            ]
            subprocess.run(concat_cmd, capture_output=True)

            # 3. Sesle birleştir ve final formatı ayarla (Zorunlu yuv420p)
            # -shortest: Ses veya video hangisi biterse orada durur
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

            # Temizlik
            if os.path.exists(concat_list): os.remove(concat_list)
            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Video başarıyla hazırlandı: {output_path}")
            return True

        except Exception as e:
            logger.error(f"[Editor] Montaj sırasında kritik hata: {e}")
            return False
