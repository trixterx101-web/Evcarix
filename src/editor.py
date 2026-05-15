import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        """
        Her klibi 7 saniyeye kırparak birleştirir. 
        Deha hızlı render ve akıcı bir görsel döngü sağlar.
        """
        try:
            logger.info(f"[Editor] Akıllı Kırpma ve HD Montaj: {len(clips_paths)} klip")
            
            inputs = []
            filter_str = ""
            # Her klip için maksimum süre (saniye)
            # 11 klip varsa ve ses 42 saniyeyse, her klip yaklaşık 4-5 saniye yeterlidir.
            # 7 saniye vererek pay bırakıyoruz.
            max_clip_dur = 7 

            for i, clip in enumerate(clips_paths):
                inputs.extend(["-i", os.path.abspath(clip)])
                # trim=end=7: Her klibin sadece ilk 7 saniyesini al
                filter_str += (
                    f"[{i}:v]trim=duration={max_clip_dur},setpts=PTS-STARTPTS,"
                    f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                )
            
            for i in range(len(clips_paths)):
                filter_str += f"[v{i}]"
            filter_str += f"concat=n={len(clips_paths)}:v=1:a=0[vout]"

            temp_video = "temp_merged_video.mp4"
            
            cmd_v = [
                "ffmpeg", "-y"
            ] + inputs + [
                "-filter_complex", filter_str,
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-threads", "0", "-an", temp_video
            ]
            
            logger.info(f"[Editor] Video işleniyor (Klipler {max_clip_dur} saniyeye kırpıldı)...")
            subprocess.run(cmd_v, check=True)

            # Pass 2: Sesle birleştir ve ses bittiğinde kes (-shortest)
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", output_path
            ]
            
            logger.info("[Editor] Ses senkronizasyonu ve Final Çıktı...")
            subprocess.run(final_cmd, check=True)

            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Video (Kırpılmış & HD) hazır: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Montaj hatası: {e}")
            return False
