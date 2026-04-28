import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips, ImageClip
)
import PIL.Image

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS


class AutoEditor:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.font_bold = self._load_font("bold", 72)
        self.font_regular = self._load_font("regular", 60)

    def _load_font(self, style="bold", size=60):
        """Platform bağımsız font yükleme."""
        bold_paths = [
            "fonts/Roboto-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        regular_paths = [
            "fonts/Roboto-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        paths = bold_paths if style == "bold" else regular_paths
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    # ─────────────────────────────────────────────────────────────────
    # Pillow tabanlı altyazı frame üretici
    # ─────────────────────────────────────────────────────────────────
    def _make_subtitle_frame(self, text, width=1080, height=1920):
        """
        Belirli bir metin için şeffaf RGBA altyazı karesi üretir.
        Pillow kullanır — ImageMagick gerektirmez.
        """
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        font = self.font_bold
        max_w = width - 80  # 40px padding her iki yan

        # Kelimeyi satırlara böl
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
        total_h = len(lines) * line_h + 30
        box_w = max_w + 50
        box_h = total_h + 20

        # Alt kısım: Y=1480 civarı (güvenli bölge)
        y_start = 1480

        # Yarı saydam arka plan kutusu
        box_x = (width - box_w) // 2
        box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 170))
        # Köşeleri yumuşat
        img.paste(box_img, (box_x, y_start - 15), box_img)

        # Metin satırlarını çiz
        text_y = y_start
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            x = (width - line_w) // 2

            # Kalın gölge (outline)
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    draw.text((x + dx, text_y + dy), line, font=font, fill=(0, 0, 0, 255))

            # Ana metin (parlak sarı)
            draw.text((x, text_y), line, font=font, fill=(255, 230, 0, 255))
            text_y += line_h

        return np.array(img)

    def _build_subtitle_clips(self, word_timings, video_duration, width=1080, height=1920):
        """
        word_timings listesinden senkronize ImageClip altyazıları üretir.
        6 kelimelik gruplar halinde gösterir.
        """
        subtitle_clips = []
        chunk_size = 5

        for i in range(0, len(word_timings), chunk_size):
            chunk = word_timings[i: i + chunk_size]
            chunk_text = " ".join(w["text"] for w in chunk)
            start_t = chunk[0]["start"]
            end_t = chunk[-1]["start"] + chunk[-1]["duration"]
            duration = round(end_t - start_t, 3)
            if duration <= 0.05:
                continue
            if start_t >= video_duration:
                break

            frame = self._make_subtitle_frame(chunk_text, width, height)
            clip = (
                ImageClip(frame, ismask=False)
                .set_start(start_t)
                .set_duration(min(duration, video_duration - start_t))
                .set_position((0, 0))
            )
            subtitle_clips.append(clip)

        print(f"[Editor] {len(subtitle_clips)} altyazı bloğu oluşturuldu.")
        return subtitle_clips

    # ─────────────────────────────────────────────────────────────────
    # Ana montaj fonksiyonu
    # ─────────────────────────────────────────────────────────────────
    def assemble_short(self, video_paths, audio_path, word_timings, output_filename):
        """
        Dikey Shorts video montajı — 1080x1920, tam senkron Pillow altyazıları.
        """
        audio = AudioFileClip(audio_path)
        target_duration = audio.duration

        # ── Stok videolar ──
        clips = []
        for path in video_paths:
            if not os.path.exists(path):
                continue
            try:
                clip = VideoFileClip(path)
                w, h = clip.size
                # 9:16 kırp
                target_ratio = 9 / 16
                if w / h > target_ratio:
                    new_w = int(h * target_ratio)
                    clip = clip.crop(x_center=w / 2, width=new_w)
                else:
                    new_h = int(w / target_ratio)
                    clip = clip.crop(y_center=h / 2, height=new_h)
                clip = clip.resize(width=1080)
                clips.append(clip)
            except Exception as e:
                print(f"Klip hatası ({path}): {e}")

        if not clips:
            clips = [ColorClip(size=(1080, 1920), color=(10, 10, 30)).set_duration(target_duration)]

        base_video = concatenate_videoclips(clips, method="compose")

        if base_video.duration < target_duration:
            base_video = base_video.loop(duration=target_duration)
        else:
            base_video = base_video.subclip(0, target_duration)

        base_video = base_video.set_audio(audio)

        # ── Altyazılar ──
        all_layers = [base_video]
        if word_timings:
            subtitle_clips = self._build_subtitle_clips(word_timings, target_duration)
            all_layers.extend(subtitle_clips)
        else:
            print("[Editor] Uyarı: word_timings boş, altyazı eklenemedi.")

        final_video = CompositeVideoClip(all_layers, size=(1080, 1920))

        output_path = os.path.join(self.output_dir, output_filename)
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="6000k",
            threads=4,
            preset="fast",
            logger="bar"
        )
        print(f"[Editor] Video hazır: {output_path}")
        return output_path

    # ─────────────────────────────────────────────────────────────────
    # Premium Thumbnail
    # ─────────────────────────────────────────────────────────────────
    def generate_premium_thumbnail(self, video_path, title, output_path,
                                   channel_name="EVCARIX", slogan="NO HYPE. JUST NUMBERS. ⚡"):
        """
        YouTube için profesyonel thumbnail üretir.
        - 1280x720 (YouTube standardı)
        - Gradient overlay
        - Büyük, okunabilir başlık
        - Kanal branding (alt bant)
        """
        try:
            from moviepy.editor import VideoFileClip as VFC
            clip = VFC(video_path)
            # Videonun %15'inde bir kareyi al (genellikle güzel sahne)
            frame_time = min(clip.duration * 0.15, clip.duration - 0.1)
            frame = clip.get_frame(frame_time)
            clip.close()
            bg = Image.fromarray(frame).resize((1280, 720), PIL.Image.Resampling.LANCZOS)
        except Exception as e:
            print(f"[Thumbnail] Video karesi alınamadı: {e}")
            bg = Image.new("RGB", (1280, 720), (10, 10, 40))

        # ── Karanlık gradient overlay ──
        overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        for y in range(bg.height):
            # Üst %30 hafif, alt %70 koyu
            t = y / bg.height
            alpha = int(80 + 160 * t**1.6)
            ov_draw.rectangle([(0, y), (bg.width, y + 1)], fill=(5, 5, 20, alpha))
        bg = bg.convert("RGBA")
        bg = Image.alpha_composite(bg, overlay).convert("RGB")
        draw = ImageDraw.Draw(bg)

        # ── Font yükleme ──
        title_font = self._load_font("bold", 90)
        ch_font = self._load_font("bold", 44)
        sl_font = self._load_font("regular", 28)

        # ── Başlık metni — en fazla 2 satır ──
        max_title_w = bg.width - 80
        words = title.split()
        lines, current = [], ""
        for w in words:
            test = (current + " " + w).strip()
            bbox = draw.textbbox((0, 0), test, font=title_font)
            if bbox[2] - bbox[0] > max_title_w:
                if current:
                    lines.append(current)
                current = w
            else:
                current = test
        if current:
            lines.append(current)
        lines = lines[:2]  # Maksimum 2 satır

        # Başlık Y pozisyonu — ortada biraz üst
        line_h = title_font.size + 16
        total_text_h = len(lines) * line_h
        y_title = (bg.height - total_text_h) // 2 - 40

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            lw = bbox[2] - bbox[0]
            x = (bg.width - lw) // 2

            # Gölge / outline efekti
            stroke = 5
            for dx in range(-stroke, stroke + 1):
                for dy in range(-stroke, stroke + 1):
                    draw.text((x + dx, y_title + dy), line, font=title_font, fill=(0, 0, 0))

            # Parlak sarı-turuncu gradient efekti (2 renk arası)
            draw.text((x, y_title), line, font=title_font, fill=(255, 220, 0))
            y_title += line_h

        # ── Alt bant (kanal + slogan) ──
        band_h = 120
        band_y = bg.height - band_h
        band = Image.new("RGBA", (bg.width, band_h), (0, 0, 0, 220))
        bg_rgba = bg.convert("RGBA")
        bg_rgba.paste(band, (0, band_y), band)
        bg = bg_rgba.convert("RGB")
        draw = ImageDraw.Draw(bg)

        # Kanal adı — yeşil
        cb = draw.textbbox((0, 0), channel_name, font=ch_font)
        cx = (bg.width - (cb[2] - cb[0])) // 2
        # Outline
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((cx + dx, band_y + 18 + dy), channel_name, font=ch_font, fill=(0, 0, 0))
        draw.text((cx, band_y + 18), channel_name, font=ch_font, fill=(0, 240, 80))

        # Slogan — beyaz
        sb = draw.textbbox((0, 0), slogan, font=sl_font)
        sx = (bg.width - (sb[2] - sb[0])) // 2
        draw.text((sx, band_y + 75), slogan, font=sl_font, fill=(220, 220, 220))

        # ── EV ikonu / rozet ──
        try:
            badge_text = "⚡EV"
            badge_font = self._load_font("bold", 36)
            bb = draw.textbbox((0, 0), badge_text, font=badge_font)
            bw, bh = bb[2] - bb[0] + 30, bb[3] - bb[1] + 16
            badge_x, badge_y = 40, 40
            badge_bg = Image.new("RGBA", (bw, bh), (0, 200, 255, 220))
            bg_rgba2 = bg.convert("RGBA")
            bg_rgba2.paste(badge_bg, (badge_x, badge_y), badge_bg)
            bg = bg_rgba2.convert("RGB")
            draw = ImageDraw.Draw(bg)
            draw.text((badge_x + 15, badge_y + 8), badge_text, font=badge_font, fill=(0, 0, 0))
        except Exception:
            pass

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        bg.save(output_path, "JPEG", quality=97)
        print(f"[Editor] Premium Thumbnail kaydedildi: {output_path}")
        return output_path

    def assemble_long_video(self, video_paths, audio_path, script_text, output_filename, bg_music_path=None):
        """Yatay uzun video montajı (Full HD 1920x1080)."""
        audio = AudioFileClip(audio_path)
        clips = []
        for path in video_paths:
            if not os.path.exists(path):
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
                print(f"Klip hatası: {e}")

        if not clips:
            clips = [ColorClip(size=(1920, 1080), color=(0, 0, 0)).set_duration(audio.duration)]

        final_video = concatenate_videoclips(clips, method="compose")
        if final_video.duration < audio.duration:
            final_video = final_video.loop(duration=audio.duration)
        else:
            final_video = final_video.subclip(0, audio.duration)

        if bg_music_path and os.path.exists(bg_music_path):
            from moviepy.editor import CompositeAudioClip
            bg = AudioFileClip(bg_music_path).volumex(0.1)
            if bg.duration < audio.duration:
                bg = bg.loop(duration=audio.duration)
            else:
                bg = bg.subclip(0, audio.duration)
            final_video = final_video.set_audio(CompositeAudioClip([audio, bg]))
        else:
            final_video = final_video.set_audio(audio)

        output_path = os.path.join(self.output_dir, output_filename)
        final_video.write_videofile(
            output_path, fps=30, codec="libx264", audio_codec="aac", bitrate="12000k"
        )
        return output_path
