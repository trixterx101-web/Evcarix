import os
import json
import logging
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, TextClip, ColorClip, ImageClip
)

logger = logging.getLogger("AutoEditor")


# ── Güvenli tip dönüşümü yardımcısı ─────────────────────────────────────────
def to_float(val, default: float = 0.0) -> float:
    """Her türlü timing/duration değerini güvenli biçimde float'a çevirir."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _probe_duration(path: str, default: float = 30.0) -> float:
    """ffprobe ile dosya süresini döndürür."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", path],
            capture_output=True, text=True, timeout=15
        )
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            dur = stream.get("duration")
            if dur:
                return float(dur)
    except Exception:
        pass
    return default


class AutoEditor:
    def __init__(self):
        self.temp_dir = "assets/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        self._fix_imagemagick_policy()

    # ── ImageMagick policy düzeltmesi ────────────────────────────────────────
    def _fix_imagemagick_policy(self):
        policy_path = "/etc/ImageMagick-6/policy.xml"
        if os.path.exists(policy_path):
            try:
                subprocess.run([
                    "sudo", "sed", "-i",
                    's/rights="none" pattern="@\\*"/rights="read|write" pattern="@*"/',
                    policy_path
                ], check=True, capture_output=True)
                logger.info("[Editor] ✅ ImageMagick policy fixed")
            except Exception as e:
                logger.warning(f"[Editor] ⚠️ ImageMagick policy fix failed: {e}")

    # ── PIL tabanlı metin klibi (ImageMagick fallback) ────────────────────────
    def make_text_clip_pil(self, text: str, fontsize: int = 70, color: str = "white",
                           duration: float = 2.0, size: tuple = (1080, 300)) -> ImageClip:
        duration = to_float(duration, 2.0)
        try:
            img = Image.new("RGBA", size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            font_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "assets/fonts/LiberationSans-Bold.ttf",
            ]
            font = None
            for p in font_paths:
                if os.path.exists(p):
                    font = ImageFont.truetype(p, fontsize)
                    break
            if not font:
                font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), text.upper(), font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x, y = (size[0] - w) // 2, (size[1] - h) // 2
            draw.text((x + 2, y + 2), text.upper(), font=font, fill="black")
            draw.text((x, y), text.upper(), font=font, fill=color)
            return ImageClip(np.array(img), duration=duration)
        except Exception as e:
            logger.error(f"[Editor] PIL text fallback failed: {e}")
            return ColorClip(size=(100, 50), color=(0, 0, 0), duration=duration)

    # ── Ken Burns efekti ─────────────────────────────────────────────────────
    def _apply_ken_burns(self, clip, zoom_ratio: float = 0.05):
        try:
            clip_dur = to_float(clip.duration, 5.0)
            if clip_dur <= 0:
                return clip
            def zoom(t):
                return 1 + zoom_ratio * (to_float(t, 0.0) / clip_dur)
            return clip.resize(zoom)
        except Exception:
            return clip

    # ── Geçiş efektleri ──────────────────────────────────────────────────────
    def _add_transitions_sfx(self, clips: list, sfx_path: str = None) -> list:
        processed = []
        for i, clip in enumerate(clips):
            try:
                c = clip.fadein(0.4) if i > 0 else clip
            except Exception:
                c = clip
            processed.append(c)
        return processed

    # ── Altyazı ekleme ───────────────────────────────────────────────────────
    def _add_subtitles(self, video_clip, words_with_times: list):
        subs = []
        w, h = video_clip.size
        for item in (words_with_times or []):
            try:
                word, start_raw, end_raw = item
                # ÖNEMLİ: start/end her zaman float'a çevrilmeli
                start = to_float(start_raw, 0.0)
                end   = to_float(end_raw,   0.0)
                duration = end - start
                if duration <= 0:
                    continue
                color = "yellow" if len(word) > 5 else "white"
                try:
                    txt = TextClip(
                        word.upper(), fontsize=w * 0.12, color=color,
                        font="Liberation-Sans-Bold", stroke_color="black",
                        stroke_width=2, method="caption", size=(w * 0.8, None)
                    ).set_start(start).set_duration(duration).set_position(("center", h * 0.7))
                except Exception:
                    txt = self.make_text_clip_pil(
                        word, fontsize=int(w * 0.12), color=color,
                        duration=duration, size=(int(w * 0.9), int(h * 0.2))
                    ).set_start(start).set_position(("center", h * 0.65))
                subs.append(txt)
            except Exception as e:
                logger.warning(f"[Editor] Altyazı öğesi atlandı: {e}")
        return CompositeVideoClip([video_clip] + subs)

    # ── ffprobe ile klip doğrulama ────────────────────────────────────────────
    def _validate_clip(self, path: str) -> bool:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=duration",
                 "-of", "default=noprint_wrappers=1", path],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    # ── FFmpeg tabanlı fallback montaj ──────────────────────────────────────
    def _generate_fallback_video(self, audio_path: str, output_path: str,
                                 is_short: bool) -> str:
        """Klip yoksa düz renkli arka plan video üretir — her zaman geçerli dosya döndürür."""
        size = "1080x1920" if is_short else "1920x1080"
        duration = _probe_duration(audio_path, 30.0) if (audio_path and os.path.exists(audio_path)) else 30.0
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c=0x001833:size={size}:rate=30",
        ]
        if audio_path and os.path.exists(audio_path):
            cmd += ["-i", audio_path, "-c:a", "aac", "-b:a", "192k"]
        cmd += [
            "-t", str(duration),
            "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
            "-shortest", output_path
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"[Editor] ✅ Fallback renk video üretildi: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"[Editor] _generate_fallback_video hatası: {e}")
        raise RuntimeError("[Editor] Fallback video üretilemedi")

    def _ffmpeg_fallback_assemble(self, clips_paths: list, audio_path: str,
                                  output_path: str, is_short: bool) -> str:
        """
        MoviePy'siz saf FFmpeg montaj.
        Her zaman geçerli bir video yolu döndürür veya exception fırlatır.
        """
        vf = ("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
              if is_short else
              "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080")

        valid_clips = [p for p in clips_paths if p and os.path.exists(p)]
        if not valid_clips:
            logger.warning("[Editor] FFmpeg fallback: klip yok, renk arka plan kullanılıyor.")
            return self._generate_fallback_video(audio_path, output_path, is_short)

        # concat list dosyası
        list_path = os.path.join(self.temp_dir, "concat_list.txt")
        with open(list_path, "w") as f:
            for cp in valid_clips:
                f.write(f"file '{os.path.abspath(cp)}'\n")

        temp_video = os.path.join(self.temp_dir, "ffmpeg_concat_tmp.mp4")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-vf", vf,
            "-c:v", "libx264", "-crf", "23", "-preset", "ultrafast",
            "-an", temp_video
        ]
        try:
            r = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0 or not os.path.exists(temp_video):
                logger.warning(f"[Editor] FFmpeg concat failed: {r.stderr[-300:]}")
                temp_video = None
        except Exception as e:
            logger.error(f"[Editor] FFmpeg concat exception: {e}")
            temp_video = None

        if not temp_video:
            return self._generate_fallback_video(audio_path, output_path, is_short)

        # Ses ekle
        merge_cmd = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", output_path
        ]
        try:
            r2 = subprocess.run(merge_cmd, capture_output=True, text=True, timeout=300)
            if r2.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info(f"[Editor] ✅ FFmpeg fallback montaj başarılı: {output_path}")
                return output_path
            logger.error(f"[Editor] FFmpeg merge failed: {r2.stderr[-300:]}")
        except Exception as e:
            logger.error(f"[Editor] FFmpeg merge exception: {e}")

        raise RuntimeError("[Editor] FFmpeg fallback montaj da başarısız oldu")

    # ── Ana montaj metodu ─────────────────────────────────────────────────────
    def assemble(self, clips_paths: list, audio_path: str, title: str, topic: str,
                 words_with_times: list = None, is_short: bool = True,
                 output_path: str = "final.mp4") -> str:
        """
        Video montajı yapar.
        HİÇBİR ZAMAN None döndürmez — her koşulda geçerli bir dosya yolu döndürür
        ya da RuntimeError fırlatır.
        """
        try:
            v_clips = []
            target_size = (1080, 1920) if is_short else (1920, 1080)

            for p in clips_paths:
                if not p or not os.path.exists(p):
                    continue
                if not self._validate_clip(p):
                    logger.warning(f"[Editor] Bozuk klip atlandı (ffprobe): {os.path.basename(p)}")
                    try:
                        os.remove(p)
                    except Exception:
                        pass
                    continue
                try:
                    c = VideoFileClip(p).without_audio().resize(height=target_size[1])
                    # duration'ın gerçekten sayısal olduğunu doğrula
                    c_dur = to_float(c.duration, -1.0)
                    if c_dur <= 0:
                        logger.warning(f"[Editor] Geçersiz süre ({c_dur}), klip atlandı: {os.path.basename(p)}")
                        c.close()
                        continue
                    if c.w > target_size[0]:
                        c = c.crop(x_center=c.w / 2, width=target_size[0])
                    v_clips.append(self._apply_ken_burns(c))
                except Exception as clip_err:
                    logger.warning(f"[Editor] Klip yüklenemedi ({os.path.basename(p)}): {clip_err}")

            # Klip yoksa fallback
            if not v_clips:
                logger.warning("[Editor] Hiç geçerli klip yok → FFmpeg fallback.")
                return self._ffmpeg_fallback_assemble(clips_paths, audio_path, output_path, is_short)

            final_video = concatenate_videoclips(
                self._add_transitions_sfx(v_clips), method="compose"
            )

            # Ses ekle
            if audio_path and os.path.exists(audio_path):
                try:
                    audio = AudioFileClip(audio_path)
                    vid_dur = to_float(final_video.duration, 30.0)
                    audio_dur = to_float(audio.duration, 0.0)
                    if audio_dur > vid_dur:
                        audio = audio.subclip(0, vid_dur)
                    final_video = final_video.set_audio(audio)
                except Exception as audio_err:
                    logger.warning(f"[Editor] Ses eklenemedi: {audio_err}")

            # Altyazı
            if words_with_times:
                try:
                    final_video = self._add_subtitles(final_video, words_with_times)
                except Exception as sub_err:
                    logger.warning(f"[Editor] Altyazı eklenemedi: {sub_err}")

            final_video.write_videofile(
                output_path, codec="libx264", audio_codec="aac",
                fps=30, preset="ultrafast", logger=None
            )

            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                raise RuntimeError(f"[Editor] write_videofile geçerli dosya üretmedi: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"[Editor] MoviePy montaj başarısız: {e}")
            logger.info("[Editor] FFmpeg saf fallback deneniyor...")
            try:
                return self._ffmpeg_fallback_assemble(clips_paths, audio_path, output_path, is_short)
            except Exception as fallback_err:
                logger.error(f"[Editor] FFmpeg fallback da başarısız: {fallback_err}")
                raise RuntimeError(f"[Editor] Tüm montaj yöntemleri başarısız: {e} | {fallback_err}")
