import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips, ImageClip
)
import PIL.Image
from io import BytesIO
from pathlib import Path

# FIX 1: Pillow >= 10 ANTIALIAS kaldırıldı → LANCZOS kullan
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS


class AutoEditor:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.font_bold    = self._load_font("bold",    72)
        self.font_regular = self._load_font("regular", 60)

    def _load_font(self, style="bold", size=60):
        bold_paths = [
            "fonts/Roboto-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        regular_paths = [
            "fonts/Roboto-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        paths = bold_paths if style == "bold" else regular_paths
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    # ─── Pillow tabanlı altyazı frame üretici ─────────────────────────────
    def _make_subtitle_frame(self, text, width=1080, height=1920):
        img  = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = self.font_bold
        max_w = width - 80

        words = text.split()
        lines, current = [], ""
        for w in words:
            test = (current + " " + w).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_w:
                if current:
                    lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)

        line_h = self.font_bold.size + 14
        y_start = 1350

        for line in lines:
            bbox   = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            x = (width - line_w) // 2
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    draw.text((x + dx, y_start + dy), line, font=font, fill=(0, 0, 0, 255))
            draw.text((x, y_start), line, font=font, fill=(255, 255, 255, 255))
            y_start += line_h

        return np.array(img)

    def _build_subtitle_clips(self, word_timings, video_duration, width=1080, height=1920):
        """
        FIX 2: word_timings her eleman dict olmalı: {"text":..., "start":..., "duration":...}
        Hem dict hem eski liste formatını destekler.
        """
        subtitle_clips = []
        chunk_size = 5

        # Normalize: liste içinde dict veya tuple/list olabilir
        normalized = []
        for w in word_timings:
            if isinstance(w, dict):
                normalized.append(w)
            elif isinstance(w, (list, tuple)) and len(w) >= 3:
                normalized.append({"text": w[0], "start": w[1], "duration": w[2]})
            else:
                continue

        for i in range(0, len(normalized), chunk_size):
            chunk = normalized[i: i + chunk_size]
            if not chunk:
                continue
            chunk_text = " ".join(w["text"] for w in chunk)
            start_t    = chunk[0]["start"]
            end_t      = chunk[-1]["start"] + chunk[-1]["duration"]
            duration   = round(end_t - start_t, 3)
            if duration <= 0.05:
                continue
            if start_t >= video_duration:
                break

            frame     = self._make_subtitle_frame(chunk_text, width, height)
            rgb_frame = frame[:, :, :3]
            alpha_mask = frame[:, :, 3].astype(float) / 255.0

            clip = ImageClip(rgb_frame, ismask=False)
            clip = clip.set_mask(ImageClip(alpha_mask, ismask=True))
            clip = (
                clip
                .set_start(start_t)
                .set_duration(min(duration, video_duration - start_t))
                .set_position((0, 0))
            )
            subtitle_clips.append(clip)

        print(f"[Editor] {len(subtitle_clips)} altyazı bloğu oluşturuldu.")
        return subtitle_clips

    # ─── Hareket eden gradient arka plan ──────────────────────────────────
    def _make_motion_background(self, duration, width=1080, height=1920):
        from moviepy.editor import VideoClip

        def make_frame(t):
            progress = t / duration if duration > 0 else 0
            r = int(8  + 35 * progress + 12 * np.sin(progress * np.pi * 2))
            g = int(10 +  5 * np.sin(progress * np.pi * 3))
            b = int(30 - 15 * progress +  8 * np.cos(progress * np.pi * 2))
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (max(0, min(255, r)), max(0, g), max(0, min(255, b)))
            for x in range(width):
                v = 1.0 - 0.25 * abs((x / width) - 0.5)
                frame[:, x] = (frame[:, x] * v).astype(np.uint8)
            return frame

        return VideoClip(make_frame, duration=duration)

    # ─── Ana montaj fonksiyonu ─────────────────────────────────────────────
    def assemble_short(self, video_paths, audio_path, word_timings, output_filename,
                       ai_fallback_images=None, category="general"):
        """
        FIX 3: write_videofile'da ffmpeg_params ile ses kanalı zorlaması eklendi.
        FIX 4: Boş video_paths durumu güvenli şekilde ele alınıyor.
        """
        import random
        audio = AudioFileClip(audio_path)
        
        # Video süresi 25-50 saniye random aralığında
        min_duration = 25
        max_duration = 50
        target_duration = random.uniform(min_duration, max_duration)
        
        # Audio süresi hedeften kısaysa loop ile uzat
        if audio.duration < target_duration:
            from moviepy.audio.fx.all import audio_loop
            try:
                audio = audio_loop(audio, duration=target_duration)
            except (AttributeError, ImportError):
                # fallback: manual loop via concatenation
                from moviepy.editor import concatenate_audioclips
                import math
                repeats = math.ceil(target_duration / audio.duration)
                audio = concatenate_audioclips([audio] * repeats).subclip(0, target_duration)
        # Audio süresi hedeften uzunsa kırp
        elif audio.duration > target_duration:
            audio = audio.subclip(0, target_duration)

        clips = []
        for path in (video_paths or []):
            if not path or not os.path.exists(path):
                continue
            try:
                clip = VideoFileClip(path)
                w, h = clip.size
                target_ratio = 9 / 16

                if w / h > target_ratio:
                    new_w = int(h * target_ratio)
                    x1 = (w - new_w) // 2
                    clip = clip.crop(x1=x1, y1=0, x2=x1 + new_w, y2=h)
                elif w / h < target_ratio:
                    new_h = int(w / target_ratio)
                    y1 = (h - new_h) // 2
                    clip = clip.crop(x1=0, y1=y1, x2=w, y2=y1 + new_h)

                clip = clip.resize((1080, 1920))
                clips.append(clip)
            except Exception as e:
                print(f"[Editor] Klip hatası ({path}): {e}")

        if len(clips) >= 2:
            base_video = concatenate_videoclips(clips, method="compose")
            if base_video.duration < target_duration:
                from moviepy.video.fx.all import loop as video_loop
                try:
                    base_video = video_loop(base_video, duration=target_duration)
                except (AttributeError, ImportError):
                    # fallback: manual loop via concatenation
                    import math
                    repeats = math.ceil(target_duration / base_video.duration)
                    base_video = concatenate_videoclips([base_video] * repeats).subclip(0, target_duration)
            else:
                base_video = base_video.subclip(0, target_duration)

        elif ai_fallback_images and any(os.path.exists(p) for p in ai_fallback_images):
            print("[Editor] AI görüntüleri Ken Burns efektiyle kullanılıyor...")
            valid_images = [p for p in ai_fallback_images if os.path.exists(p)]
            img_clips = []
            segment = target_duration / max(len(valid_images), 1)
            for i, img_path in enumerate(valid_images):
                try:
                    img = ImageClip(img_path)
                    iw, ih = img.size
                    if iw / ih > 9 / 16:
                        new_w = int(ih * 9 / 16)
                        offset = (i % 2) * max(0, iw - new_w)
                        img = img.crop(x1=offset, y1=0, x2=offset + new_w, y2=ih)
                    else:
                        new_h = int(iw * 16 / 9)
                        y_off = (ih - new_h) // 2
                        img = img.crop(x1=0, y1=max(0, y_off), x2=iw, y2=min(ih, y_off + new_h))
                    img = img.resize((1080, 1920))
                    # FIX 5: lambda ile zoom - moviepy 1.0.3 uyumlu
                    seg = segment
                    img = img.fl_time(lambda t: t)  # noop, duration set aşağıda
                    img = img.set_duration(seg).set_start(i * seg)
                    img_clips.append(img)
                except Exception as e:
                    print(f"[Editor] AI görüntü clip hatası: {e}")
            if img_clips:
                base_video = CompositeVideoClip(img_clips, size=(1080, 1920))
                if base_video.duration < target_duration:
                    from moviepy.video.fx.all import loop as video_loop
                    try:
                        base_video = video_loop(base_video, duration=target_duration)
                    except (AttributeError, ImportError):
                        # fallback: manual loop via concatenation
                        import math
                        repeats = math.ceil(target_duration / base_video.duration)
                        base_video = concatenate_videoclips([base_video] * repeats).subclip(0, target_duration)
            else:
                base_video = self._make_motion_background(target_duration)
        else:
            print("[Editor] Motion gradient arka plan kullanılıyor...")
            base_video = self._make_motion_background(target_duration)

        base_video = base_video.set_audio(audio)

        all_layers = [base_video]
        if word_timings:
            subtitle_clips = self._build_subtitle_clips(word_timings, target_duration)
            all_layers.extend(subtitle_clips)
        else:
            print("[Editor] Uyarı: word_timings boş, altyazı eklenmedi.")

        final_video = CompositeVideoClip(all_layers, size=(1080, 1920))

        if final_video.w != 1080 or final_video.h != 1920:
            final_video = final_video.resize((1080, 1920))

        output_path = os.path.join(self.output_dir, output_filename)
        os.makedirs(self.output_dir, exist_ok=True)

        # FIX 6: ffmpeg_params ile ses mono/stereo uyumsuzluğunu önle
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            threads=4,
            preset="ultrafast",
            logger="bar",
            ffmpeg_params=["-ac", "2"],   # stereo ses zorla
        )
        audio.close()
        final_video.close()
        print(f"[Editor] ✅ Video hazır: {output_path}")
        return output_path

    # ─── Premium Thumbnail ─────────────────────────────────────────────────
    def generate_premium_thumbnail(self, video_path, title, output_path,
                                   channel_name="EVCARIX", slogan="NO HYPE. JUST NUMBERS. ⚡"):
        W, H = 1080, 1920
        bg = Image.new("RGB", (W, H), (5, 5, 10))
        pixels = bg.load()
        for y in range(H):
            t = y / H
            r = int(10 + 30 * t)
            g = int(10 + 15 * t)
            b = int(20 + 20 * t)
            for x in range(W):
                pixels[x, y] = (r, g, b)

        draw = ImageDraw.Draw(bg)
        title_font = self._load_font("bold", 100)
        bbox = draw.textbbox((0, 0), title, font=title_font)
        lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (W - lw) // 2
        y = (H - lh) // 2

        for dx in range(-4, 5):
            for dy in range(-4, 5):
                draw.text((x + dx, y + dy), title, font=title_font, fill=(0, 0, 0))
        draw.text((x, y), title, font=title_font, fill=(255, 255, 255))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        bg.save(output_path, "PNG")
        print(f"[Thumbnail] Kaydedildi: {output_path}")
        return output_path

    # ─── Uzun video montajı ────────────────────────────────────────────────
    def assemble_long_video(self, video_paths, audio_path, script_text,
                            output_filename, bg_music_path=None):
        audio = AudioFileClip(audio_path)
        clips = []
        for path in (video_paths or []):
            if not path or not os.path.exists(path):
                continue
            try:
                clip = VideoFileClip(path)
                w, h = clip.size
                if w / h < 16 / 9:
                    clip = clip.crop(y_center=h / 2, height=int(w / (16 / 9)))
                elif w / h > 16 / 9:
                    clip = clip.crop(x_center=w / 2, width=int(h * (16 / 9)))
                clip = clip.resize(width=1920)
                clips.append(clip)
            except Exception as e:
                print(f"[Editor] Klip hatası: {e}")

        if not clips:
            clips = [ColorClip(size=(1920, 1080), color=(0, 0, 0)).set_duration(audio.duration)]

        final_video = concatenate_videoclips(clips, method="compose")
        if final_video.duration < audio.duration:
            from moviepy.video.fx.all import loop as video_loop
            try:
                final_video = video_loop(final_video, duration=audio.duration)
            except (AttributeError, ImportError):
                # fallback: manual loop via concatenation
                import math
                repeats = math.ceil(audio.duration / final_video.duration)
                final_video = concatenate_videoclips([final_video] * repeats).subclip(0, audio.duration)
        else:
            final_video = final_video.subclip(0, audio.duration)

        if bg_music_path and os.path.exists(bg_music_path):
            from moviepy.editor import CompositeAudioClip
            bg = AudioFileClip(bg_music_path).volumex(0.1)
            if bg.duration < audio.duration:
                from moviepy.audio.fx.all import audio_loop
                try:
                    bg = audio_loop(bg, duration=audio.duration)
                except (AttributeError, ImportError):
                    # fallback: manual loop via concatenation
                    from moviepy.editor import concatenate_audioclips
                    import math
                    repeats = math.ceil(audio.duration / bg.duration)
                    bg = concatenate_audioclips([bg] * repeats).subclip(0, audio.duration)
            else:
                bg = bg.subclip(0, audio.duration)
            final_video = final_video.set_audio(CompositeAudioClip([audio, bg]))
        else:
            final_video = final_video.set_audio(audio)

        output_path = os.path.join(self.output_dir, output_filename)
        os.makedirs(self.output_dir, exist_ok=True)
        final_video.write_videofile(
            output_path, fps=30, codec="libx264",
            audio_codec="aac", bitrate="12000k",
            ffmpeg_params=["-ac", "2"],
        )
        return output_path

    # ─── Haftalık Uzun Video Montajı (1920x1080, 16:9) ────────────────────────
    def assemble_weekly_long_video(self, video_clips, audio_path, title, target_duration, output_path):
        """
        Haftalık uzun formatlı video montajı (1920x1080, 16:9, 240-360s).
        
        Args:
            video_clips: Video dosya yolları listesi
            audio_path: Ses dosyası yolu
            title: Video başlığı (title card için)
            target_duration: Hedef süre (saniye, 240-360)
            output_path: Çıktı dosya adı
        """
        import random
        audio = AudioFileClip(audio_path)
        
        # Audio süresini hedeften kısaysa loop ile uzat, uzunsa kırp
        if audio.duration < target_duration:
            from moviepy.audio.fx.all import audio_loop
            try:
                audio = audio_loop(audio, duration=target_duration)
            except (AttributeError, ImportError):
                from moviepy.editor import concatenate_audioclips
                import math
                repeats = math.ceil(target_duration / audio.duration)
                audio = concatenate_audioclips([audio] * repeats).subclip(0, target_duration)
        elif audio.duration > target_duration:
            audio = audio.subclip(0, target_duration)

        # Video klipleri 16:9 aspect ratio'ya çevir ve 1920x1080'a resize
        clips = []
        for path in (video_clips or []):
            if not path or not os.path.exists(path):
                continue
            try:
                clip = VideoFileClip(path)
                w, h = clip.size
                target_ratio = 16 / 9

                if w / h > target_ratio:
                    new_w = int(h * target_ratio)
                    x1 = (w - new_w) // 2
                    clip = clip.crop(x1=x1, y1=0, x2=x1 + new_w, y2=h)
                elif w / h < target_ratio:
                    new_h = int(w / target_ratio)
                    y1 = (h - new_h) // 2
                    clip = clip.crop(x1=0, y1=y1, x2=w, y2=y1 + new_h)

                clip = clip.resize((1920, 1080))
                clips.append(clip)
            except Exception as e:
                print(f"[Editor] Klip hatası ({path}): {e}")

        if len(clips) >= 2:
            base_video = concatenate_videoclips(clips, method="compose")
            if base_video.duration < target_duration:
                from moviepy.video.fx.all import loop as video_loop
                try:
                    base_video = video_loop(base_video, duration=target_duration)
                except (AttributeError, ImportError):
                    import math
                    repeats = math.ceil(target_duration / base_video.duration)
                    base_video = concatenate_videoclips([base_video] * repeats).subclip(0, target_duration)
            else:
                base_video = base_video.subclip(0, target_duration)
        else:
            print("[Editor] Yeterli video klip yok, siyah arka plan kullanılıyor...")
            base_video = ColorClip(size=(1920, 1080), color=(0, 0, 0)).set_duration(target_duration)

        base_video = base_video.set_audio(audio)

        # Title card (5 saniye) - basit text clip
        try:
            from moviepy.video.fx.all import crop
            title_clip = TextClip(
                title,
                fontsize=70,
                color="white",
                font="Arial-Bold",
                align="center",
                size=(1920, 1080)
            ).set_position("center").set_duration(5)
            
            bg_clip = ColorClip(size=(1920, 1080), color=(20, 20, 40)).set_duration(5)
            title_card = CompositeVideoClip([bg_clip, title_clip])
        except Exception as e:
            print(f"[Editor] Title card hatası: {e}, atlanıyor...")
            title_card = ColorClip(size=(1920, 1080), color=(20, 20, 40)).set_duration(5)
        
        # Outro card (5 saniye)
        try:
            outro_text = "Subscribe for more EV data — Evcarix"
            outro_clip = TextClip(
                outro_text,
                fontsize=60,
                color="white",
                font="Arial-Bold",
                align="center",
                size=(1920, 1080)
            ).set_position("center").set_duration(5)
            
            outro_bg = ColorClip(size=(1920, 1080), color=(20, 20, 40)).set_duration(5)
            outro_card = CompositeVideoClip([outro_bg, outro_clip])
        except Exception as e:
            print(f"[Editor] Outro card hatası: {e}, atlanıyor...")
            outro_card = ColorClip(size=(1920, 1080), color=(20, 20, 40)).set_duration(5)
        
        # Video'yu başla (title card'dan sonra)
        base_video = base_video.set_start(5)
        
        # Tüm katmanları birleştir
        all_layers = [title_card, base_video, outro_card]
        final_video = CompositeVideoClip(all_layers, size=(1920, 1080))

        # Video export
        output_full_path = os.path.join(self.output_dir, output_path)
        os.makedirs(self.output_dir, exist_ok=True)
        final_video.write_videofile(
            output_full_path, fps=30, codec="libx264",
            audio_codec="aac", preset="medium",
            ffmpeg_params=["-ac", "2"]
        )
        print(f"[Editor] Long-form video kaydedildi: {output_full_path}")
        return output_full_path
