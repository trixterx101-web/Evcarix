import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("Editor")

class AutoEditor:
    def assemble(self, clips_paths, audio_path, output_path, is_short=True,
                 title=None, topic=None, words_with_times=None):
        """
        Videoyu ses süresiyle milisaniyelik hassasiyetle eşitler.
        'Ses bitti, video devam ediyor' sorununu kesin olarak çözer.
        """
        try:
            logger.info(f"[Editor] Hassas Senkronizasyon Montajı: {len(clips_paths)} klip")
            
            # 1. Ses süresini ffprobe ile al
            duration = self._get_audio_duration(audio_path)
            logger.info(f"[Editor] Ses süresi: {duration}s")

            inputs = []
            filter_str = ""
            max_clip_dur = 7 # Her klip max 7 saniye

            for i, clip in enumerate(clips_paths):
                inputs.extend(["-i", os.path.abspath(clip)])
                filter_str += (
                    f"[{i}:v]trim=duration={max_clip_dur},setpts=PTS-STARTPTS,"
                    f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}];"
                )
            
            for i in range(len(clips_paths)):
                filter_str += f"[v{i}]"
            filter_str += f"concat=n={len(clips_paths)}:v=1:a=0[vout]"

            temp_video = "temp_merged_video.mp4"
            
            # Pass 1: Görüntü
            cmd_v = [
                "ffmpeg", "-y"
            ] + inputs + [
                "-filter_complex", filter_str,
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-threads", "0", "-an", temp_video
            ]
            subprocess.run(cmd_v, check=True)

            # Pass 2: Sesle tam süresinde birleştir
            # -t {duration} -> Videoyu tam ses süresinde keser.
            final_cmd = [
                "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", # Re-encode garantisi
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(duration), # Kesin süre
                "-shortest", output_path
            ]
            
            logger.info("[Editor] Final Senkronize Render...")
            subprocess.run(final_cmd, check=True)

            if os.path.exists(temp_video): os.remove(temp_video)
            
            logger.info(f"[Editor] ✅ Jilet gibi senkronize video hazır: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Montaj hatası: {e}")
            return False

    def _get_audio_duration(self, path):
        """Ses dosyasının süresini saniye cinsinden döndürür."""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(result.stdout.strip())
        except:
            return 45.0 # Fallback
