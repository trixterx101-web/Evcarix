import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        """
        Videoyu 1080x1920 formatına, en boy oranını koruyarak (pad) birleştirir.
        Görüntüde bozulma veya kesilme olmaz.
        """
        try:
            logger.info(f"[Editor] Profesyonel HD Montaj: {len(clips_paths)} klip")
            
            concat_list = "clips_to_merge.txt"
            with open(concat_list, "w") as f:
                for clip in clips_paths:
                    f.write(f"file '{os.path.abspath(clip)}'\n")

            temp_video = "temp_merged_video.mp4"
            # Ölçeklendirme Filtresi: Görüntüyü sığdır (decrease) ve siyahla doldur (pad)
            # setsar=1 ile kare piksel garantisi veriyoruz.
            scale_filter = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1"
            
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list,
                "-vf", scale_filter,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-threads", "0", "-pix_fmt", "yuv420p", "-an", temp_video
            ]
            
            logger.info("[Editor] Ölçeklendirme ve Birleştirme (Pass 1)...")
            subprocess.run(concat_cmd, check=True)

            # 3. Sesle birleştir (Mapping ve Audio Encoding)
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-threads", "0", "-shortest", output_path
            ]
            
            logger.info("[Editor] Final Render (Video + Ses)...")
            subprocess.run(final_cmd, check=True)

            # Temizlik
            if os.path.exists(concat_list): os.remove(concat_list)
            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Profesyonel HD Video hazır: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Montaj hatası: {e}")
            return False
