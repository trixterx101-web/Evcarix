import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        """
        Videoyu ve sesi FFmpeg ile kusursuz bir şekilde birleştirir.
        Görüntü ve ses senkronizasyonunu garanti altına alır.
        """
        try:
            logger.info(f"[Editor] FFmpeg montajı: {len(clips_paths)} klip + Ses")
            
            # 1. Ses dosyasının varlığını ve boyutunu kontrol et
            if not os.path.exists(audio_path) or os.path.getsize(audio_path) < 100:
                logger.error(f"[Editor] Ses dosyası geçersiz veya boş: {audio_path}")
                return False

            # 2. Geçici bir dosya listesi oluştur (FFmpeg concat için)
            concat_list = "clips_to_merge.txt"
            with open(concat_list, "w") as f:
                for clip in clips_paths:
                    f.write(f"file '{os.path.abspath(clip)}'\n")

            # 3. Videoları birleştir (Sessiz olarak)
            temp_video = "temp_merged_video.mp4"
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list, "-c", "copy", "-an", temp_video
            ]
            subprocess.run(concat_cmd, capture_output=True)

            # 4. Sesle birleştir (Explicit Mapping ile sesi zorla ekle)
            # -map 0:v:0 -> İlk dosyadan (video) görüntü al
            # -map 1:a:0 -> İkinci dosyadan (audio) ses al
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", output_path
            ]
            
            logger.info("[Editor] Final render (Video + Ses birleştiriliyor)...")
            result = subprocess.run(final_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"[Editor] FFmpeg hatası: {result.stderr}")
                return False

            # Temizlik
            if os.path.exists(concat_list): os.remove(concat_list)
            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Video ve Ses başarıyla birleştirildi: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Kritik hata: {e}")
            return False
