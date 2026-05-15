import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        """
        Videoyu JET hızında ve HD kalitede birleştirir.
        Darboğazları önlemek için optimize edilmiştir.
        """
        try:
            logger.info(f"[Editor] Hızlı HD Montaj başlatılıyor: {len(clips_paths)} klip")
            
            concat_list = "clips_to_merge.txt"
            with open(concat_list, "w") as f:
                for clip in clips_paths:
                    f.write(f"file '{os.path.abspath(clip)}'\n")

            temp_video = "temp_merged_video.mp4"
            # JET HIZI AYARLARI: -threads 0, -preset ultrafast
            # Kalite için -crf 18 hala duruyor.
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
                "-threads", "0", "-pix_fmt", "yuv420p", "-an", temp_video
            ]
            
            # capture_output=True bazen buffer'ı doldurup FFmpeg'i dondurabilir. 
            # Doğrudan sistem çıktısını kullanıyoruz.
            subprocess.run(concat_cmd, check=True)

            # 3. Sesle birleştir
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                "-threads", "0", "-shortest", output_path
            ]
            
            logger.info("[Editor] Final Hızlı HD Render...")
            subprocess.run(final_cmd, check=True)

            # Temizlik
            if os.path.exists(concat_list): os.remove(concat_list)
            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Video hazır: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Montaj sırasında hata: {e}")
            # Hata anında temizlik yapmaya çalış
            try:
                if os.path.exists("clips_to_merge.txt"): os.remove("clips_to_merge.txt")
                if os.path.exists("temp_merged_video.mp4"): os.remove("temp_merged_video.mp4")
            except: pass
            return False
