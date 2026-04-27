from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ColorClip
import os
import PIL.Image

# MoviePy fix for Pillow 10+
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

class AutoEditor:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def assemble_short(self, video_paths, audio_path, script_text, output_filename):
        """Dikey (Shorts) video montajı yapar ve altyazı ekler."""
        audio = AudioFileClip(audio_path)
        
        clips = []
        for path in video_paths:
            if not os.path.exists(path):
                continue
            clip = VideoFileClip(path)
            
            # Dikey formata (9:16) getir
            w, h = clip.size
            target_ratio = 9/16
            current_ratio = w/h
            
            if current_ratio > target_ratio:
                new_w = h * target_ratio
                clip = clip.crop(x_center=w/2, width=new_w)
            
            # Tüm klipleri aynı boyuta getir (720x1280)
            clip = clip.resize(height=1280)
            if clip.w > 720:
                clip = clip.crop(x_center=clip.w/2, width=720)
            
            clips.append(clip)

        if not clips:
            clips = [ColorClip(size=(720, 1280), color=(0,0,0)).set_duration(audio.duration)]

        from moviepy.editor import concatenate_videoclips
        final_video = concatenate_videoclips(clips, method="compose")
        
        if final_video.duration < audio.duration:
            final_video = final_video.loop(duration=audio.duration)
        else:
            final_video = final_video.subclip(0, audio.duration)
            
        final_video = final_video.set_audio(audio)
        
        # Gelişmiş Altyazı Ekleme
        try:
            words = script_text.split()
            if len(words) > 0:
                # Kelimeleri sürelere böl (Basit senkronizasyon)
                duration_per_word = audio.duration / len(words)
                subtitle_clips = []
                
                # Her seferinde 3-4 kelime göster
                chunk_size = 3
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size]).upper()
                    start_t = i * duration_per_word
                    end_t = min((i + chunk_size) * duration_per_word, audio.duration)
                    
                    txt = TextClip(
                        chunk,
                        fontsize=80,
                        color='yellow',
                        font='Arial-Bold',
                        stroke_color='black',
                        stroke_width=2,
                        method='caption',
                        size=(final_video.w * 0.8, None)
                    ).set_start(start_t).set_duration(end_t - start_t).set_pos('center')
                    
                    subtitle_clips.append(txt)
                
                final_video = CompositeVideoClip([final_video] + subtitle_clips)
                print(f"{len(subtitle_clips)} adet altyazı bloğu eklendi.")
        except Exception as e:
            print(f"Altyazı eklenemedi: {e}")

        output_path = os.path.join(self.output_dir, output_filename)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        return output_path

    def assemble_long_video(self, video_paths, audio_path, script_text, output_filename, bg_music_path=None):
        """Yatay (16:9) uzun video montajı yapar."""
        audio = AudioFileClip(audio_path)
        
        clips = []
        for path in video_paths:
            if not os.path.exists(path):
                continue
            clip = VideoFileClip(path)
            
            # Yatay formata (16:9) getir
            w, h = clip.size
            target_ratio = 16/9
            current_ratio = w/h
            
            if current_ratio < target_ratio:
                # Dikey videoyu yanlardan kırp veya doldur (şimdilik kırpıyoruz)
                new_h = w / target_ratio
                clip = clip.crop(y_center=h/2, height=new_h)
            elif current_ratio > target_ratio:
                new_w = h * target_ratio
                clip = clip.crop(x_center=w/2, width=new_w)
            
            clip = clip.resize(width=1920) # Standart Full HD
            clips.append(clip)

        if not clips:
            clips = [ColorClip(size=(1920, 1080), color=(0,0,0)).set_duration(audio.duration)]

        from moviepy.editor import concatenate_videoclips, CompositeAudioClip
        final_video = concatenate_videoclips(clips, method="compose")
        
        if final_video.duration < audio.duration:
            final_video = final_video.loop(duration=audio.duration)
        else:
            final_video = final_video.subclip(0, audio.duration)

        # Arka plan müziği ekle
        final_audio = audio
        if bg_music_path and os.path.exists(bg_music_path):
            bg_music = AudioFileClip(bg_music_path).volumex(0.1) # %10 ses seviyesi
            if bg_music.duration < audio.duration:
                bg_music = bg_music.loop(duration=audio.duration)
            else:
                bg_music = bg_music.subclip(0, audio.duration)
            final_audio = CompositeAudioClip([audio, bg_music])

        final_video = final_video.set_audio(final_audio)

        # Alt kısma şık bir başlık/bilgi bandı
        try:
            txt_clip = TextClip(script_text[:100] + "...", fontsize=40, color='white', font='Arial-Bold', 
                               method='caption', size=(final_video.w*0.6, None), stroke_color='black', stroke_width=1)
            txt_clip = txt_clip.set_pos(('center', 'bottom')).set_duration(audio.duration).set_start(0).margin(bottom=50, opacity=0)
            final_video = CompositeVideoClip([final_video, txt_clip])
        except Exception as e:
            print(f"Altyazı eklenemedi: {e}")

        output_path = os.path.join(self.output_dir, output_filename)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        return output_path

if __name__ == "__main__":
    # Test için ImageMagick kurulu olmalı veya altyazısız denenebilir
    pass
