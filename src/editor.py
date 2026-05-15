import os
import logging
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, ColorClip, ImageClip
from moviepy.video.fx.all import resize, fadein

logger = logging.getLogger("AutoEditor")

class AutoEditor:
    def __init__(self):
        self.temp_dir = "assets/temp"
        os.makedirs(self.temp_dir, exist_ok=True)
        self._fix_imagemagick_policy()

    def _fix_imagemagick_policy(self):
        """Fix ImageMagick security policy on Ubuntu/GitHub Actions"""
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
                logger.warning(f"[Editor] ⚠️ Could not fix ImageMagick policy: {e}")

    def make_text_clip_pil(self, text: str, fontsize: int = 70, color: str = "white", duration: float = 2.0, size: tuple = (1080, 300)) -> ImageClip:
        """Fallback text renderer using PIL when ImageMagick/TextClip fails."""
        try:
            img = Image.new("RGBA", size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Use LiberationSans as standard in Ubuntu/GitHub Actions
            font_paths = [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "assets/fonts/LiberationSans-Bold.ttf"
            ]
            font = None
            for p in font_paths:
                if os.path.exists(p):
                    font = ImageFont.truetype(p, fontsize)
                    break
            if not font: font = ImageFont.load_default()

            # Center text
            bbox = draw.textbbox((0, 0), text.upper(), font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x, y = (size[0] - w) // 2, (size[1] - h) // 2
            
            # Draw shadow
            draw.text((x+2, y+2), text.upper(), font=font, fill="black")
            # Draw main text
            draw.text((x, y), text.upper(), font=font, fill=color)
            
            arr = np.array(img)
            return ImageClip(arr, duration=duration)
        except Exception as e:
            logger.error(f"[Editor] PIL Text fallback failed: {e}")
            return ColorClip(size=(100, 50), color=(0,0,0,0), duration=duration)

    def _apply_ken_burns(self, clip, zoom_ratio: float = 0.05):
        try:
            def zoom(t):
                return 1 + zoom_ratio * (t / clip.duration)
            return clip.resize(zoom)
        except: return clip

    def _add_transitions_sfx(self, clips: list, sfx_path: str = None) -> list:
        processed = []
        for i, clip in enumerate(clips):
            c = clip.fadein(0.4) if i > 0 else clip
            if sfx_path and i > 0 and os.path.exists(sfx_path):
                try:
                    whoosh = AudioFileClip(sfx_path).volumex(0.3)
                    c = c.set_audio(CompositeVideoClip([c.audio.set_start(0), whoosh]).audio)
                except: pass
            processed.append(c)
        return processed

    def _add_subtitles(self, video_clip, words_with_times: list):
        subs = []
        w, h = video_clip.size
        for word, start, end in (words_with_times or []):
            duration = end - start
            if duration <= 0: continue
            
            color = "yellow" if len(word) > 5 else "white"
            try:
                # Try standard TextClip first
                txt = TextClip(
                    word.upper(), fontsize=w * 0.12, color=color,
                    font='Liberation-Sans-Bold', stroke_color='black', stroke_width=2,
                    method='caption', size=(w * 0.8, None)
                ).set_start(start).set_duration(duration).set_position(('center', h * 0.7))
            except:
                # Fallback to PIL
                logger.warning(f"[Editor] TextClip failed for '{word}', using PIL fallback")
                txt = self.make_text_clip_pil(
                    word, fontsize=int(w * 0.12), color=color, 
                    duration=duration, size=(int(w * 0.9), int(h * 0.2))
                ).set_start(start).set_position(('center', h * 0.65))
            
            subs.append(txt)
        return CompositeVideoClip([video_clip] + subs)

    def _validate_clip(self, path: str) -> bool:
        """ffprobe ile klibin okunabilir olup olmadığını hızlıca doğrular."""
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1", path],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def assemble(self, clips_paths: list, audio_path: str, title: str, topic: str,
                 words_with_times: list = None, is_short: bool = True, output_path: str = "final.mp4"):
        try:
            v_clips = []
            target_size = (1080, 1920) if is_short else (1920, 1080)

            for p in clips_paths:
                if not p or not os.path.exists(p):
                    continue
                # Bozuk dosyaları ffprobe ile önceden eliyoruz
                if not self._validate_clip(p):
                    logger.warning(f"[Editor] Bozuk klip atlandı (ffprobe failed): {os.path.basename(p)}")
                    try:
                        os.remove(p)  # Önbellekten temizle
                    except Exception:
                        pass
                    continue
                try:
                    c = VideoFileClip(p).without_audio().resize(height=target_size[1])
                    if c.w > target_size[0]:
                        c = c.crop(x_center=c.w / 2, width=target_size[0])
                    v_clips.append(self._apply_ken_burns(c))
                except Exception as clip_err:
                    logger.warning(f"[Editor] Klip yüklenemedi, atlanıyor ({os.path.basename(p)}): {clip_err}")

            if not v_clips:
                logger.warning("[Editor] Hiç geçerli klip yok, fallback üretiliyor...")
                from src.utils.fallback import generate_fallback_video
                p = os.path.join(self.temp_dir, "fallback.mp4")
                generate_fallback_video(30, topic, p)
                v_clips = [VideoFileClip(p)]

            final_video = concatenate_videoclips(self._add_transitions_sfx(v_clips), method="compose")

            if audio_path and os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)
                final_video = final_video.set_audio(audio.set_duration(final_video.duration))

            if words_with_times:
                final_video = self._add_subtitles(final_video, words_with_times)

            final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=30, preset="ultrafast")
            return output_path
        except Exception as e:
            logger.error(f"[Editor] Assemble failed: {e}")
            return None
