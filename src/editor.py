import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        """
        Videoyu 1080x1920 Full HD kalitesinde birleştirir.
        Yüksek bitrate ve düşük CRF ile kristal netliğinde görüntü sağlar.
        """
        try:
            logger.info(f"[Editor] HD Montaj başlatılıyor: {len(clips_paths)} klip")
            
            # 1. Concat listesi oluştur
            concat_list = "clips_to_merge.txt"
            with open(concat_list, "w") as f:
                for clip in clips_paths:
                    f.write(f"file '{os.path.abspath(clip)}'\n")

            # 2. Videoları birleştir ve 1080x1920'ye zorla (Yüksek Kalite)
            temp_video = "temp_merged_video.mp4"
            # vf: scale=1080:1920 -> Boyutu ayarla, setsar=1:1 -> Aspect Ratio'yu koru
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-an", temp_video
            ]
            subprocess.run(concat_cmd, capture_output=True)

            # 3. Sesle birleştir ve Final Çıktıyı Yüksek Bitrate ile Ver
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", # Görüntü zaten 2. adımda HD işlendi, burada sadece kopyala
                "-c:a", "aac", "-b:a", "256k",
                "-shortest", output_path
            ]
            
            logger.info("[Editor] Final HD Render...")
            result = subprocess.run(final_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"[Editor] FFmpeg hatası: {result.stderr}")
                return False

            # Temizlik
            if os.path.exists(concat_list): os.remove(concat_list)
            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Ultra HD Video hazır: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Kritik hata: {e}")
            return False
