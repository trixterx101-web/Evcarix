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
        """Dikey Shorts video montajı — altyazılar alt kısımda yarı şeffaf kutu içinde."""
        audio = AudioFileClip(audio_path)

        clips = []
        for path in video_paths:
            if not os.path.exists(path):
                continue
            try:
                clip = VideoFileClip(path)
                w, h = clip.size
                # 9:16 dikey formata getir
                if w / h > 9 / 16:
                    new_w = h * (9 / 16)
                    clip = clip.crop(x_center=w / 2, width=new_w)
                clip = clip.resize(height=1280)
                if clip.w > 720:
                    clip = clip.crop(x_center=clip.w / 2, width=720)
                clips.append(clip)
            except Exception as e:
                print(f"Klip hatası ({path}): {e}")

        if not clips:
            clips = [ColorClip(size=(720, 1280), color=(0, 0, 0)).set_duration(audio.duration)]

        final_video = concatenate_videoclips(clips, method="compose")

        if final_video.duration < audio.duration:
            final_video = final_video.loop(duration=audio.duration)
        else:
            final_video = final_video.subclip(0, audio.duration)

        final_video = final_video.set_audio(audio)

        # Altyazı — alt kısımda yarı şeffaf kutu
        try:
            words = script_text.split()
            chunk_size = 5
            duration_per_word = audio.duration / max(len(words), 1)
            subtitle_clips = []

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                start_t = i * duration_per_word
                end_t = min((i + chunk_size) * duration_per_word, audio.duration)
                dur = end_t - start_t

                # Yarı şeffaf siyah kutu
                box = ColorClip(size=(720, 180), color=(0, 0, 0))
                box = box.set_opacity(0.6).set_start(start_t).set_duration(dur)
                box = box.set_position(("center", 1280 - 200))

                # Altyazı metni
                txt = TextClip(
                    chunk,
                    fontsize=58,
                    color='white',
                    font='Arial-Bold',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(680, None),
                    align='center'
                ).set_start(start_t).set_duration(dur)
                txt = txt.set_position(("center", 1280 - 185))

                subtitle_clips.extend([box, txt])

            final_video = CompositeVideoClip([final_video] + subtitle_clips)
            print(f"{len(subtitle_clips) // 2} altyazı bloğu eklendi.")
        except Exception as e:
            print(f"Altyazı eklenemedi: {e}")

        output_path = os.path.join(self.output_dir, output_filename)
        final_video.write_videofile(
            output_path, fps=24, codec="libx264", audio_codec="aac", threads=4
        )
        return output_path

    def assemble_long_video(self, video_paths, audio_path, script_text, output_filename, bg_music_path=None):
        """Yatay uzun video montajı."""
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
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        return output_path
