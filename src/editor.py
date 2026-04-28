from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips
)
import os
import PIL.Image

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS


class AutoEditor:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def assemble_short(self, video_paths, audio_path, script_text, output_filename):
        """Dikey Shorts video montajı — Full HD (1080x1920) ve iyileştirilmiş altyazılar."""
        audio = AudioFileClip(audio_path)

        clips = []
        for path in video_paths:
            if not os.path.exists(path):
                continue
            try:
                clip = VideoFileClip(path)
                w, h = clip.size
                # 9:16 dikey formata getir (Full HD 1080x1920 hedefli)
                target_ratio = 9 / 16
                if w / h > target_ratio:
                    new_w = h * target_ratio
                    clip = clip.crop(x_center=w / 2, width=new_w)
                else:
                    new_h = w / target_ratio
                    clip = clip.crop(y_center=h / 2, height=new_h)
                
                clip = clip.resize(width=1080) # 1080x1920
                clips.append(clip)
            except Exception as e:
                print(f"Klip hatası ({path}): {e}")

        if not clips:
            clips = [ColorClip(size=(1080, 1920), color=(0, 0, 0)).set_duration(audio.duration)]

        final_video = concatenate_videoclips(clips, method="compose")

        if final_video.duration < audio.duration:
            final_video = final_video.loop(duration=audio.duration)
        else:
            final_video = final_video.subclip(0, audio.duration)

        final_video = final_video.set_audio(audio)

        # Başlangıç Kancası (0.8 saniye süren dikkat çekici başlık ekranı)
        try:
            hook_txt = TextClip(
                script_text.split()[:5][0].upper() + "...", # İlk kelime veya kısa başlık
                fontsize=110,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=5,
                method='caption',
                size=(1000, None),
                align='center'
            ).set_duration(0.8).set_position('center').set_start(0)
            
            # Arka plana hafif bir karartma ekleyelim ki yazı okunsun
            hook_bg = ColorClip(size=(1080, 1920), color=(0,0,0)).set_opacity(0.4).set_duration(0.8)
            
            final_video = CompositeVideoClip([final_video, hook_bg, hook_txt])
        except Exception as e:
            print(f"Hook ekranı eklenemedi: {e}")

        # Altyazı — Daha okunaklı ve sığacak şekilde
        try:
            words = script_text.split()
            chunk_size = 6 # Okunaklı bloklar için 6 kelime
            duration_per_word = audio.duration / max(len(words), 1)
            subtitle_clips = []

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) # Orijinal büyük/küçük harf korunuyor
                start_t = i * duration_per_word
                end_t = min((i + chunk_size) * duration_per_word, audio.duration)
                dur = end_t - start_t

                if dur <= 0: continue

                # Altyazı metni
                txt = TextClip(
                    chunk,
                    fontsize=70,
                    color='white', 
                    font='Arial-Bold',
                    method='caption',
                    size=(900, None), 
                    align='center'
                ).set_start(start_t).set_duration(dur)
                
                # Yarı-şeffaf siyah kutu (opacity=0.6)
                bg_w, bg_h = 950, txt.h + 40
                bg = ColorClip(size=(bg_w, bg_h), color=(0, 0, 0)).set_opacity(0.6).set_start(start_t).set_duration(dur)
                
                # Ekranın ALT bölümünde konumlandırma
                pos_y = 1550 
                txt = txt.set_position(("center", pos_y + 20))
                bg = bg.set_position(("center", pos_y))

                subtitle_clips.extend([bg, txt])

            if subtitle_clips:
                final_video = CompositeVideoClip([final_video] + subtitle_clips)
                print(f"{len(subtitle_clips)//2} altyazı bloğu eklendi.")
        except Exception as e:
            print(f"Altyazı eklenemedi: {e}")

        output_path = os.path.join(self.output_dir, output_filename)
        # Daha yüksek kalite (bitrate artırıldı)
        final_video.write_videofile(
            output_path, fps=30, codec="libx264", audio_codec="aac", 
            bitrate="8000k", threads=4, preset="medium"
        )
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
                    clip = clip.crop(y_center=h / 2, height=w / (16 / 9))
                elif w / h > 16 / 9:
                    clip = clip.crop(x_center=w / 2, width=h * (16 / 9))
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
