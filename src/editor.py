import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoFileClip, AudioFileClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips, ImageClip,
    TextClip
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

    def _apply_cinematic_effects(self, clip):
        """v10.0: Pro-Level HD Effects & Ken Burns"""
        import random
        from moviepy.video.fx.all import speedx, lum_contrast, colorx
        
        # 1. Subtle Speed Ramping (0.95x - 1.05x)
        spd = random.uniform(0.95, 1.05)
        clip = speedx(clip, factor=spd)
        
        # 2. Advanced Ken Burns Effect (Zoom & Pan)
        w, h = clip.size
        zoom_speed = random.uniform(0.05, 0.15)
        mode = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right"])
        
        def effect_fn(get_frame, t):
            frame = get_frame(t)
            img = Image.fromarray(frame)
            
            # Zoom logic
            zoom = 1.0 + (zoom_speed * (t / clip.duration)) if mode == "zoom_in" else \
                   (1.0 + zoom_speed) - (zoom_speed * (t / clip.duration))
            
            # Pan logic (simulated by cropping after zoom)
            new_w, new_h = int(w * zoom), int(h * zoom)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            
            if "pan_left" in mode: left = int((new_w - w) * (t / clip.duration))
            if "pan_right" in mode: left = int((new_w - w) * (1 - t / clip.duration))
            
            return np.array(img.crop((left, top, left + w, top + h)))
            
        clip = clip.fl(effect_fn)
        
        # 3. HDR-ready Color Grading
        clip = colorx(clip, factor=random.uniform(1.0, 1.1))
        clip = lum_contrast(clip, lum=random.randint(0, 5), contrast=random.uniform(0.05, 0.1))
        
        return clip

    def _apply_ken_burns(self, clip, zoom_ratio=0.1):
        """Statik bir görüntüye yavaşça zoom yaparak Ken Burns efekti verir."""
        def zoom(t):
            return 1 + zoom_ratio * (t / clip.duration)
        return clip.resize(zoom)

    def _create_dynamic_subtitles(self, words_with_times, video_width, video_height):
        """
        Kelimeleri tek tek, büyük ve renkli altyazılar olarak oluşturur.
        Global Shorts trendlerine (Alex Hormozi tarzı) uygundur.
        """
        from moviepy.editor import TextClip, CompositeVideoClip
        
        subs = []
        for word, start, end in words_with_times:
            # Önemli kelimeleri sarı, diğerlerini beyaz yap
            color = "yellow" if len(word) > 5 else "white"
            
            txt = TextClip(
                word.upper(),
                fontsize=video_width * 0.12, # Oldukça büyük
                color=color,
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(video_width * 0.8, None)
            ).set_start(start).set_duration(end - start).set_position(('center', video_height * 0.65))
            
            subs.append(txt)
        return subs
        """Creates a high-quality animated gradient background."""
        def make_frame(t):
            img = Image.new("RGB", (width, height), (10, 10, 20))
            draw = ImageDraw.Draw(img)
            shift = int(t * 50) % width
            for x in range(0, width, 200):
                draw.rectangle([x + shift - width if x + shift > width else x + shift, 0,
                                x + shift - width + 100 if x + shift > width else x + shift + 100, height],
                               fill=(20, 20, 40))
            return np.array(img)

        from moviepy.editor import VideoClip
        return VideoClip(make_frame, duration=duration)

    def _overlay_progress_bar(self, clip, total_duration: float,
                              bar_color=(0, 212, 255), bar_height: int = 6):
        """
        Uzun videolar için alt progress bar overlay.
        İnce, şık, dikkat çekici — retention artırır.
        bar_color: (R,G,B) — varsayılan cyan (#00D4FF)
        bar_height: piksel yüksekliği
        """
        W, H = clip.w, clip.h

        def make_bar_frame(t):
            progress = min(t / total_duration, 1.0)
            frame = np.zeros((bar_height, W, 3), dtype=np.uint8)
            filled = int(W * progress)
            # Arka plan (koyu gri)
            frame[:, :, :] = (30, 30, 30)
            # Dolum (cyan gradient)
            if filled > 0:
                for x in range(filled):
                    ratio = x / max(filled, 1)
                    r = int(bar_color[0] * ratio + 0 * (1 - ratio))
                    g = int(bar_color[1] * ratio)
                    b = int(bar_color[2])
                    frame[:, x] = (r, g, b)
                # Parlak uç
                tip_start = max(0, filled - 4)
                frame[:, tip_start:filled] = (255, 255, 255)
            return frame

        from moviepy.editor import VideoClip, CompositeVideoClip
        bar_clip = (
            VideoClip(make_bar_frame, duration=total_duration, ismask=False)
            .set_position((0, H - bar_height))
        )
        return CompositeVideoClip([clip, bar_clip], size=(W, H))

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
            # Renk: beyaz metin, sarı highlight (ilk 2 kelime)
            line_color = (255, 230, 0) if y_start < 1420 else (255, 255, 255)
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    draw.text((x + dx, y_start + dy), line, font=font, fill=(0, 0, 0, 255))
            draw.text((x, y_start), line, font=font, fill=line_color + (255,))
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
        
        # Video süresini tam olarak audio süresine eşitle (Kesilmeyi önlemek için kritik)
        target_duration = audio.duration
        print(f"[Editor] Audio: {audio.duration:.2f}s | Target synced to audio.")

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
                
                # v8.0 Cinematic Effects
                clip = self._apply_cinematic_effects(clip)
                
                clips.append(clip)
            except Exception as e:
                print(f"[Editor] Klip hatası ({path}): {e}")

        if len(clips) >= 2:
            base_video = concatenate_videoclips(clips, method="compose")
            # Video süresi her zaman audio süresine tam eşit olmalı
            if base_video.duration < target_duration:
                import math
                repeats = math.ceil(target_duration / base_video.duration)
                print(f"[Editor] Klip sayısı az ({len(clips)}), {repeats} kez döngüye alınıyor (karıştırılarak).")
                
                # Her döngüde farklı sıra olması için shuffle ekleyerek birleştir
                all_looped_clips = list(clips)
                for _ in range(repeats - 1):
                    shuffled = list(clips)
                    random.shuffle(shuffled)
                    all_looped_clips.extend(shuffled)
                
                looped = concatenate_videoclips(all_looped_clips, method="compose")
                base_video = looped.subclip(0, target_duration)
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

        # ── Step 4: 1s Intro Card (As requested: "1. görsel 1 saniye çıksın") ──
        try:
            from src.thumbnail_generator import ThumbnailGenerator
            tg = ThumbnailGenerator()
            hook_img_path = os.path.join(self.output_dir, f"intro_{output_filename}.jpg")
            clean_title = output_filename.replace("_", " ").replace(".mp4", "").upper()
            
            # 1s sürecek bir intro görseli üret
            tg.create(title=clean_title, category=category, is_short=True, 
                      output_path=hook_img_path)
            
            if os.path.exists(hook_img_path):
                from moviepy.editor import ImageClip
                intro_card = ImageClip(hook_img_path).set_duration(1.0).set_fps(30)
                # Video metni (audio) hemen başlasın (audio senkronu bozulmasın diye 0'dan başlar)
                # Ama görüntü 1s sonra footage'a geçer
                base_video = CompositeVideoClip([
                    intro_card,
                    base_video.set_start(1.0)
                ], size=(1080, 1920)).set_duration(target_duration)
                print("[Editor] 1s Intro Card eklendi.")
        except Exception as e:
            print(f"[Editor] Intro Card hatası: {e}")

        # Ses ve video tam senkron
        base_video = base_video.set_audio(audio)
        final_w, final_h = 1080, 1920
        all_layers = [base_video]

        if word_timings:
            # Altyazı klipleri base_video.duration üzerinden, audio süresiyle sınırlı
            subtitle_clips = self._build_subtitle_clips(
                word_timings, min(base_video.duration, target_duration)
            )
            all_layers.extend(subtitle_clips)
        else:
            print("[Editor] Uyarı: word_timings boş, altyazı eklenmedi.")

        final_video = CompositeVideoClip(all_layers, size=(final_w, final_h))

        # Whoosh transitions
        final_video = self._add_transitions_sfx(final_video, clips)
        
        if final_video.w != final_w or final_video.h != final_h:
            final_video = final_video.resize((final_w, final_h))

        output_path = os.path.join(self.output_dir, output_filename)
        os.makedirs(self.output_dir, exist_ok=True)

        # HD Kalite export (8000k bitrate, 60fps, CRF 18)
        final_video.write_videofile(
            output_path,
            fps=60,
            codec="libx264",
            audio_codec="aac",
            bitrate="8000k",
            audio_bitrate="320k",
            threads=8,
            preset="slow",
            logger="bar",
            ffmpeg_params=["-crf", "18", "-pix_fmt", "yuv420p", "-colorspace", "bt709"],
        )
        audio.close()
        final_video.close()
        print(f"[Editor] [OK] Video hazir: {output_path}")
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

    def generate_thumbnail(self, title: str, output_path: str,
                           category="default", bg_image_path: str = None, is_short: bool = False) -> str:
        """
        v9.0 Premium Thumbnail Wrapper with Automatic Logic Detection.
        """
        try:
            from .thumbnail_generator import ThumbnailGenerator
            gen = ThumbnailGenerator()
            
            # ── Automatic Logic Detection ──
            # 1. Comparison Detection
            is_comp = False
            title_lower = title.lower()
            if any(x in title_lower for x in [" vs ", " versus ", " vs. ", " compared to "]):
                is_comp = True
            
            # 2. Smart Stat Extraction (Percentages, Volts, Range, Money)
            stat = ""
            import re
            # Try to find: 800V, -45%, 1000KM, $30K, etc.
            stat_patterns = [
                r'(\d+%)',          # 45%
                r'(\d+V)',          # 800V
                r'(\d+KM)',         # 1000KM
                r'(\d+K)',          # 500K
                r'(\$\d+[K]?)',     # $30K
                r'(\d+YR)'          # 5YR
            ]
            for p in stat_patterns:
                m = re.search(p, title.upper())
                if m:
                    stat = m.group(1)
                    break
            
            # If still empty, check for '?' or '!' to make it a hook
            if not stat and "?" in title:
                stat = "FACT?"
            elif not stat and "!" in title:
                stat = "NEW!"

            return gen.create(
                title=title, 
                stat=stat, 
                category=category, 
                output_path=output_path, 
                bg_image_path=bg_image_path, 
                is_short=is_short,
                is_comparison=is_comp
            )
        except Exception as e:
            print(f"[Editor] High-Impact Thumbnail Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    def assemble_long_video(self, video_paths, audio_path, script_text,
                            output_filename, bg_music_path=None, category="default"):
        """
        FFmpeg kullanarak hızlı uzun video montajı. 25 saniyelik Premium Hook ekler.
        """
        import subprocess
        import tempfile
        import os
        from moviepy.editor import AudioFileClip, ImageClip

        output_path = os.path.join(self.output_dir, output_filename)
        os.makedirs(self.output_dir, exist_ok=True)
        tmp_dir = tempfile.mkdtemp(prefix="evcarix_long_")
        
        # ── Step 0: Premium Multi-Image Hook (25 Seconds) ──
        # Using 5 distinct AI images (5s each) for a dynamic intro.
        hook_video_path = None
        try:
            from .thumbnail_generator import ThumbnailGenerator
            tg = ThumbnailGenerator()
            clean_title = output_filename.replace("_", " ").replace(".mp4", "").upper()
            bg_hint = video_paths[0] if video_paths and os.path.exists(video_paths[0]) else None
            
            print(f"[Editor] [LongHook] 5 adet premium görsel üretiliyor...")
            hook_clips = []
            for i in range(5):
                h_img_path = os.path.join(self.output_dir, f"hook_long_{i}_{output_filename}.jpg")
                # Vary the prompt slightly for each image
                variation = f" angle {i+1}" if i > 0 else ""
                tg.create(title=clean_title + variation, category=category, is_short=False, 
                          output_path=h_img_path, bg_image_path=bg_hint)
                
                if os.path.exists(h_img_path):
                    h_dur = 5.0
                    h_clip = ImageClip(h_img_path).set_duration(h_dur).resize((1920, 1080))
                    # Ken Burns: Zoom in or out alternately
                    if i % 2 == 0:
                        h_clip = h_clip.resize(lambda t: 1.0 + 0.08 * (t / h_dur))
                    else:
                        h_clip = h_clip.resize(lambda t: 1.08 - 0.08 * (t / h_dur))
                    h_clip = h_clip.set_fps(30).set_position('center')
                    hook_clips.append(h_clip)
            
            if hook_clips:
                print(f"[Editor] [LongHook] 25 saniyelik çoklu giriş videosu birleştiriliyor...")
                hook_out = os.path.join(tmp_dir, "hook_clip.mp4")
                final_hook_clip = concatenate_videoclips(hook_clips, method="compose")
                final_hook_clip.write_videofile(hook_out, fps=30, codec="libx264", bitrate="8000k", logger=None)
                if os.path.exists(hook_out):
                    hook_video_path = hook_out
        except Exception as e:
            print(f"[Editor] [LongHook] Hata: {e}")

        # List valid clips
        valid_paths = [p for p in (video_paths or []) if p and os.path.exists(p)]
        # Add Hook to the front if successful
        final_sources = ([hook_video_path] if hook_video_path else []) + valid_paths
        
        # --- Adım 1: Normalize Clips ---
        normalized = []
        for i, path in enumerate(final_sources[:40]):
            out_clip = os.path.join(tmp_dir, f"clip_{i:03d}.mp4")
            # Hook ise 25s, diğerleri max 8s
            dur_limit = "25" if path == hook_video_path else "8"
            
            cmd = [
                "ffmpeg", "-y", "-i", path, "-t", dur_limit,
                "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an", "-threads", "4",
                out_clip
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=60)
                if os.path.exists(out_clip) and os.path.getsize(out_clip) > 10000:
                    normalized.append(out_clip)
            except Exception: continue

        if not normalized:
            return None # Fail gracefully

        # --- Adım 2: Concat ---
        concat_list = os.path.join(tmp_dir, "concat.txt")
        with open(concat_list, "w") as f:
            for c in normalized: f.write(f"file '{c}'\n")

        silent_video = os.path.join(tmp_dir, "silent.mp4")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", silent_video], capture_output=True)

        # --- Adım 3: Final Merge with Audio ---
        try:
            with AudioFileClip(audio_path) as audio_obj:
                audio_duration = audio_obj.duration
        except: audio_duration = 200
        
        cmd_final = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", silent_video, "-i", audio_path,
            "-map", "0:v:0", "-map", "1:a:0", "-t", str(audio_duration),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k", "-ac", "2", output_path
        ]
        subprocess.run(cmd_final, capture_output=True)
        # Final render status
        if os.path.exists(output_path):
            print(f"[Editor] [OK] Uzun video hazır (+25s Hook): {output_path}")
        else:
            print(f"[Editor] [Hata] Final video dosyası oluşturulamadı.")

        # Cleanup
        import shutil
        try: shutil.rmtree(tmp_dir, ignore_errors=True)
        except: pass

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
        print(f"[Editor] 🎤 Audio süresi: {audio.duration:.1f}s | Hedef: {target_duration}s")
        
        # Audio süresini kullan, loop yapma (metin tekrarını önlemek için)
        # Video süresini audio süresine eşitle
        if audio.duration < target_duration:
            print(f"[Editor] ⚠️ Audio, hedeften kısa ({audio.duration:.1f}s < {target_duration}s). Video süresi audio'ya göre ayarlanıyor.")
            target_duration = audio.duration
        elif audio.duration > target_duration:
            print(f"[Editor] ✂️ Audio, hedeften uzun. {target_duration}s noktasına kesiliyor.")
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
                # v8.0 Cinematic Effects
                clip = self._apply_cinematic_effects(clip)
                clips.append(clip)
            except Exception as e:
                print(f"[Editor] Klip hatası ({path}): {e}")

        if len(clips) >= 1:
            # 1 veya daha fazla klip varsa — döngüye al
            base_video = concatenate_videoclips(clips)  # method="compose" kaldırıldı — MoviePy bug fix
            if base_video.duration < target_duration:
                import math
                repeats = math.ceil(target_duration / base_video.duration)
                looped_clips = []
                for _ in range(repeats):
                    shuffled = list(clips)
                    random.shuffle(shuffled)
                    looped_clips.extend(shuffled)
                base_video = concatenate_videoclips(looped_clips).subclip(0, target_duration)
            else:
                base_video = base_video.subclip(0, target_duration)
            print(f"[Editor] ✅ {len(clips)} klip kullanılıyor, süre: {base_video.duration:.1f}s")
        else:
            print("[Editor] ⚠️ Hiç klip yok, gradient arka plan kullanılıyor...")
            base_video = self._make_motion_background(target_duration, width=1920, height=1080)

        # Title card (Pillow ile - ImageMagick bağımlılığını kaldırmak için)
        def make_card(text, subtitle="Evcarix Deep Dive"):
            img = Image.new("RGB", (1920, 1080), (10, 10, 25))
            draw = ImageDraw.Draw(img)
            
            # Draw some techy lines
            for i in range(0, 1920, 100):
                draw.line([(i, 0), (i, 1080)], fill=(20, 20, 50), width=1)
            for i in range(0, 1080, 100):
                draw.line([(0, i), (1920, i)], fill=(20, 20, 50), width=1)
            
            f_main = self._load_font("bold", 100)
            f_sub = self._load_font("regular", 50)
            
            # Main Title
            bbox = draw.textbbox((0, 0), text.upper(), font=f_main)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            draw.text(((1920-tw)//2, (1080-th)//2 - 50), text.upper(), font=f_main, fill=(255, 255, 255))
            
            # Subtitle
            sbox = draw.textbbox((0, 0), subtitle, font=f_sub)
            sw, sh = sbox[2]-sbox[0], sbox[3]-sbox[1]
            draw.text(((1920-sw)//2, (1080-th)//2 + 100), subtitle, font=f_sub, fill=(0, 212, 255))
            
            return np.array(img)

        title_frame = make_card(title)
        title_card = ImageClip(title_frame).set_duration(1.0).set_fps(30)
        
        outro_frame = make_card("THANKS FOR WATCHING", "Subscribe for more EV data")
        outro_card = ImageClip(outro_frame).set_duration(1.0).set_fps(30)

        # Ana video sesini ekle
        base_video = base_video.set_audio(audio)

        # Birleştirme: Title (1s) + Base (target) + Outro (1s)
        # NOT: concatenate_videoclips yerine CompositeVideoClip kullanıyoruz.
        # Bu, "çizgi çizgi" (stride/codec) hatalarını ve donmaları engeller.
        final_video = CompositeVideoClip([
            title_card,
            base_video.set_start(1.0),
            outro_card.set_start(1.0 + base_video.duration)
        ], size=(1920, 1080))

        # Video export
        output_full_path = os.path.join(self.output_dir, output_path)
        os.makedirs(self.output_dir, exist_ok=True)

        # Progress bar ekle (uzun video için retention mekanizması)
        try:
            final_video = self._overlay_progress_bar(
                final_video, total_duration=final_video.duration
            )
            print("[Editor] ✅ Progress bar eklendi.")
        except Exception as e:
            print(f"[Editor] ⚠️ Progress bar hatası (atlanıyor): {e}")

        final_video.write_videofile(
            output_full_path, fps=30, codec="libx264",
            audio_codec="aac", preset="ultrafast",
            threads=4, bitrate="8000k",
            ffmpeg_params=["-ac", "2"]
        )
        audio.close()
        final_video.close()
        print(f"[Editor] Long-form video kaydedildi: {output_full_path}")
        return output_full_path
