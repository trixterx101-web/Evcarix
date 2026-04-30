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

        # Alt-orta konum: Y=950-1050 civarı (video ortasının altı, Shorts güvenli bölge)
        y_start = 980

        # Yarı saydam siyah arka plan kutusu
        box_x = (width - box_w) // 2
        box_img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 200))
        img.paste(box_img, (box_x, y_start - 15), box_img)

        # Metin satırlarını çiz
        text_y = y_start
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            x = (width - line_w) // 2

            # Çok kalın siyah outline/shadow (Shorts tarzı)
            for dx in [-3, -2, -1, 0, 1, 2, 3]:
                for dy in [-3, -2, -1, 0, 1, 2, 3]:
                    draw.text((x + dx, text_y + dy), line, font=font, fill=(0, 0, 0, 255))

            # Ana metin — BİLDİR (beyaz, bold, net)
            draw.text((x, text_y), line, font=font, fill=(255, 255, 255, 255))
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
    def _make_motion_background(self, duration, width=1080, height=1920):
        """Stok video yoksa kullanılacak yavaş gradient arka plan clip'i üretir."""
        from moviepy.editor import VideoClip

        def make_frame(t):
            progress = t / duration if duration > 0 else 0
            # Koyu gradient: lacivert → mor → koyu turuncu (yavaş geçiş)
            r = int(8 + 35 * progress + 12 * np.sin(progress * np.pi * 2))
            g = int(10 + 5 * np.sin(progress * np.pi * 3))
            b = int(30 - 15 * progress + 8 * np.cos(progress * np.pi * 2))
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (max(0, r), max(0, g), max(0, b))
            # Hafif yatay vignette
            for x in range(width):
                v = 1.0 - 0.25 * abs((x / width) - 0.5)
                frame[:, x] = (frame[:, x] * v).astype(np.uint8)
            return frame

        return VideoClip(make_frame, duration=duration)

    def assemble_short(self, video_paths, audio_path, word_timings, output_filename,
                       ai_fallback_images=None, thumbnail_path=None, category="general"):
        """
        Dikey Shorts video montajı — 1080x1920, tam senkron Pillow altyazıları.
        ai_fallback_images: Stok video yoksa kullanılacak AI görüntü path listesi.
        thumbnail_path: Video sonuna eklenir (YouTube manuel thumbnail seçimi için).
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
                target_ratio = 9 / 16
                if w / h > target_ratio:
                    new_w = int(h * target_ratio)
                    clip = clip.crop(x_center=w / 2, width=new_w)
                else:
                    new_h = int(w * target_ratio)
                    clip = clip.crop(y_center=h / 2, height=new_h)
                clip = clip.resize(width=1080)
                clips.append(clip)
            except Exception as e:
                print(f"Klip hatası ({path}): {e}")

        if len(clips) >= 2:
            # Normal stok video montajı
            base_video = concatenate_videoclips(clips, method="compose")
            if base_video.duration < target_duration:
                base_video = base_video.loop(duration=target_duration)
            else:
                base_video = base_video.subclip(0, target_duration)
        elif ai_fallback_images and any(os.path.exists(p) for p in ai_fallback_images):
            # AI görüntü fallback: Ken Burns (yavaş zoom) efekti
            print("[Editor] Stok video az — AI görüntüleri Ken Burns efektiyle kullanılıyor...")
            valid_images = [p for p in ai_fallback_images if os.path.exists(p)]
            img_clips = []
            segment = target_duration / max(len(valid_images), 1)
            for i, img_path in enumerate(valid_images):
                try:
                    from moviepy.editor import ImageClip
                    img = ImageClip(img_path)
                    # 1080x1920'e sığdır, kırp
                    iw, ih = img.size
                    if iw / ih > 9 / 16:
                        new_w = int(ih * 9 / 16)
                        # Yavaş pan: soldan sağa
                        start_x = max(0, (iw - new_w) // 2 - 50)
                        end_x = min(iw - new_w, (iw - new_w) // 2 + 50)
                        pan_t = (i % 2)  # her görüntüde farklı yön
                        if pan_t == 0:
                            img = img.crop(x1=start_x, y1=0, x2=start_x + new_w, y2=ih)
                        else:
                            img = img.crop(x1=end_x, y1=0, x2=end_x + new_w, y2=ih)
                    else:
                        new_h = int(iw * 16 / 9)
                        img = img.crop(x1=0, y1=(ih - new_h) // 2, x2=iw, y2=(ih + new_h) // 2)
                    img = img.resize(width=1080)
                    # Yavaş zoom: %105'ten %100'e
                    img = img.resize(lambda t: 1.0 + 0.05 * (1 - t / segment))
                    img = img.set_duration(segment).set_start(i * segment)
                    img_clips.append(img)
                except Exception as e:
                    print(f"AI görüntü clip hatası: {e}")
            if img_clips:
                base_video = CompositeVideoClip(img_clips, size=(1080, 1920))
                if base_video.duration < target_duration:
                    base_video = base_video.loop(duration=target_duration)
            else:
                base_video = self._make_motion_background(target_duration)
        else:
            # Motion gradient fallback (en son çare)
            print("[Editor] Stok video ve AI görüntü yok — motion gradient arka plan kullanılıyor...")
            base_video = self._make_motion_background(target_duration)

        base_video = base_video.set_audio(audio)

        # ── Thumbnail frame'i video sonuna ekle (YouTube manuel secim icin) ──
        if thumbnail_path and os.path.exists(thumbnail_path):
            try:
                from moviepy.editor import ImageClip
                thumb_dur = 3.0  # YouTube frame secimi icin yeterli sure
                thumb_img = ImageClip(thumbnail_path).set_duration(thumb_dur)
                # Dikey videoya letterbox olarak sigdir
                # Thumbnail'i tam 9:16 ekrana sigdir (kirmizi/beyaz Shorts kutusu full screen)
                thumb_img = thumb_img.resize((1080, 1920))
                thumb_img = thumb_img.set_position(("center", "center"))
                thumb_bg = ColorClip(size=(1080, 1920), color=(5, 5, 15)).set_duration(thumb_dur)
                thumb_layer = CompositeVideoClip([thumb_bg, thumb_img], size=(1080, 1920))
                base_video = concatenate_videoclips([base_video, thumb_layer], method="compose")
                print(f"[Editor] Thumbnail frame video sonuna eklendi ({thumb_dur}s)")
            except Exception as e:
                print(f"[Editor] Thumbnail frame eklenemedi: {e}")

        # ── Altyazılar ──
        all_layers = [base_video]
        if word_timings:
            subtitle_clips = self._build_subtitle_clips(word_timings, target_duration)
            all_layers.extend(subtitle_clips)
        else:
            print("[Editor] Uyarı: word_timings boş, altyazı eklenemedi.")

        final_video = CompositeVideoClip(all_layers, size=(1080, 1920))

        # Kesin 9:16 boyut garantisi (ffmpeg output kesinlikle 1080x1920 olsun)
        if final_video.w != 1080 or final_video.h != 1920:
            final_video = final_video.resize((1080, 1920))

        output_path = os.path.join(self.output_dir, output_filename)
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            threads=4,
            preset="ultrafast",
            logger="bar"
        )
        print(f"[Editor] Video hazır: {output_path}")
        return output_path

    # ─────────────────────────────────────────────────────────────────
    # Premium Thumbnail — Video frame kullanmaz, tamamen Pillow + gradient
    # ─────────────────────────────────────────────────────────────────
    def generate_premium_thumbnail(self, video_path, title, output_path,
                                   channel_name="EVCARIX", slogan="NO HYPE. JUST NUMBERS. ⚡"):
        """
        YouTube için profesyonel AI-style thumbnail üretir.
        - 1280x720, koyu gradient arka plan (mavi→mor→turuncu)
        - Büyük sarı/beyaz başlık (max 2 satır)
        - EV temalı şekiller (Pillow ile çizilmiş ikonlar)
        - Kanal branding (alt bant)
        """
        W, H = 1080, 1920

        # ── Gradient arka plan oluştur (koyu mavi → mor → turuncu-kırmızı) ──
        bg = Image.new("RGB", (W, H), (0, 0, 0))
        pixels = bg.load()
        for y in range(H):
            t = y / H
            # Üst: koyu mavi-lacivert (5, 10, 35) → Orta: mor (25, 5, 45) → Alt: koyu turuncu (45, 20, 5)
            r = int(5 + 40 * t + 15 * np.sin(t * np.pi))
            g = int(10 - 5 * t)
            b = int(35 - 25 * t + 10 * np.sin(t * np.pi))
            for x in range(W):
                # Hafif yatay vignette
                vignette = 1.0 - 0.3 * abs((x / W) - 0.5)
                pixels[x, y] = (int(r * vignette), int(g * vignette), int(b * vignette))

        # ── EV temalı dekoratif şekiller ──
        deco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        deco_draw = ImageDraw.Draw(deco)
        # Sağ üst köşe: büyük yarı-saydam pil/şimşek sembolü (basit geometri)
        # Şimşek çizgisi
        lightning_points = [(W - 180, 80), (W - 220, 180), (W - 160, 180), (W - 200, 280)]
        deco_draw.polygon(lightning_points, fill=(255, 220, 0, 30))
        # Sol alt: dairesel halka
        deco_draw.ellipse([(-60, H - 200), (140, H)], outline=(0, 255, 150, 25), width=8)
        # Sağ alt: küçük çizgiler (data/grafik hissi)
        for i in range(5):
            x1 = W - 300 + i * 40
            h = 60 + i * 25
            deco_draw.rectangle([x1, H - 120 - h, x1 + 20, H - 120], fill=(0, 200, 255, 20))
        bg = Image.alpha_composite(bg.convert("RGBA"), deco).convert("RGB")
        draw = ImageDraw.Draw(bg)

        # ── Font yükleme — dikey 9:16 için optimize boyutlar ──
        title_font = self._load_font("bold", 96)
        ch_font = self._load_font("bold", 44)
        sl_font = self._load_font("regular", 26)

        # ── Başlık metni — en fazla 2 satır, ortada ──
        max_title_w = W - 120
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
        lines = lines[:2]

        line_h = title_font.size + 18
        total_text_h = len(lines) * line_h + (len(lines) - 1) * 18
        y_title = (H - total_text_h) // 2 - 80

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (W - lw) // 2

            # Kırmızı kutu arka plan (Shorts tarzı text box)
            pad_x, pad_y = 24, 16
            box_rect = [x - pad_x, y_title - pad_y, x + lw + pad_x, y_title + lh + pad_y]
            draw.rectangle(box_rect, fill=(220, 20, 20))  # Canlı kırmızı

            # Beyaz bold metin kutunun ortasında
            draw.text((x, y_title), line, font=title_font, fill=(255, 255, 255))
            y_title += line_h + 18  # Satırlar arası boşluk

        # ── Alt bant (kanal + slogan) ──
        band_h = 110
        band_y = H - band_h
        band = Image.new("RGBA", (W, band_h), (0, 0, 0, 200))
        bg_rgba = bg.convert("RGBA")
        bg_rgba.paste(band, (0, band_y), band)
        bg = bg_rgba.convert("RGB")
        draw = ImageDraw.Draw(bg)

        # Kanal adı — parlak yeşil
        cb = draw.textbbox((0, 0), channel_name, font=ch_font)
        cx = (W - (cb[2] - cb[0])) // 2
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                draw.text((cx + dx, band_y + 16 + dy), channel_name, font=ch_font, fill=(0, 0, 0))
        draw.text((cx, band_y + 16), channel_name, font=ch_font, fill=(0, 255, 120))

        # Slogan — beyaz
        sb = draw.textbbox((0, 0), slogan, font=sl_font)
        sx = (W - (sb[2] - sb[0])) // 2
        draw.text((sx, band_y + 68), slogan, font=sl_font, fill=(230, 230, 230))

        # ── Sol üst köşe EV rozet ──
        try:
            badge_text = "⚡ EV"
            badge_font = self._load_font("bold", 34)
            bb = draw.textbbox((0, 0), badge_text, font=badge_font)
            bw, bh = bb[2] - bb[0] + 28, bb[3] - bb[1] + 14
            badge_x, badge_y = 35, 35
            badge_bg = Image.new("RGBA", (bw, bh), (0, 255, 150, 200))
            bg_rgba2 = bg.convert("RGBA")
            bg_rgba2.paste(badge_bg, (badge_x, badge_y), badge_bg)
            bg = bg_rgba2.convert("RGB")
            draw = ImageDraw.Draw(bg)
            draw.text((badge_x + 14, badge_y + 7), badge_text, font=badge_font, fill=(0, 0, 0))
        except Exception:
            pass

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        bg.save(output_path, "JPEG", quality=95)
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
