import os
import logging
import random
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, ColorClip
from moviepy.video.fx.all import resize, fadein, fadeout

logger = logging.getLogger("AutoEditor")

class AutoEditor:
    def __init__(self):
        self.temp_dir = "assets/temp"
        os.makedirs(self.temp_dir, exist_ok=True)

    def _apply_ken_burns(self, clip, zoom_ratio: float = 0.05):
        """Slow zoom effect for static images or video clips."""
        try:
            duration = clip.duration
            def zoom(t):
                return 1 + zoom_ratio * (t / duration)
            return clip.resize(zoom)
        except Exception as e:
            logger.warning(f"[Editor] Ken Burns failed: {e}")
            return clip

    def _add_transitions_sfx(self, clips: list, sfx_path: str = None) -> list:
        """
        Adds crossfade transitions between clips and optional Whoosh SFX.
        """
        processed = []
        for i, clip in enumerate(clips):
            # Apply fade in for all except first, or use crossfade logic
            c = clip.fadein(0.4) if i > 0 else clip
            
            # If SFX is provided, layer it at the start of the transition
            if sfx_path and i > 0 and os.path.exists(sfx_path):
                try:
                    whoosh = AudioFileClip(sfx_path).volumex(0.3).set_start(0)
                    new_audio = CompositeVideoClip([c.audio.set_start(0), whoosh]).audio
                    c = c.set_audio(new_audio)
                except: pass
            processed.append(c)
        return processed

    def _build_intro_card(self, title: str, topic: str, is_short: bool = True, duration: float = 1.5):
        """Short intro card using ThumbnailGenerator."""
        try:
            from src.thumbnail_generator import ThumbnailGenerator
            tg = ThumbnailGenerator()
            path = os.path.join(self.temp_dir, "intro_card_temp.jpg")
            tg.create(title, topic, path, is_short)
            
            clip = VideoFileClip(path).set_duration(duration)
            return self._apply_ken_burns(clip, 0.1) # Faster zoom for intro
        except Exception as e:
            logger.error(f"[Editor] Intro card build failed: {e}")
            color = (10, 10, 20)
            return ColorClip(size=(1080, 1920) if is_short else (1280, 720), color=color, duration=duration)

    def _add_subtitles(self, video_clip, words_with_times: list):
        """
        Animated word-by-word subtitles.
        Expects list of (word, start, end).
        """
        subs = []
        w, h = video_clip.size
        for word, start, end in words_with_times:
            # High-impact style
            color = "yellow" if len(word) > 5 else "white"
            txt = TextClip(
                word.upper(),
                fontsize=w * 0.12,
                color=color,
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(w * 0.8, None)
            ).set_start(start).set_duration(end - start).set_position(('center', h * 0.7))
            subs.append(txt)
            
        return CompositeVideoClip([video_clip] + subs)

    def assemble(self, clips_paths: list, audio_path: str, title: str, topic: str, 
                 words_with_times: list = None, is_short: bool = True, output_path: str = "final.mp4"):
        """Main assembly method."""
        try:
            logger.info(f"[Editor] Starting assembly of {len(clips_paths)} clips.")
            
            # Load and prepare clips
            v_clips = []
            target_size = (1080, 1920) if is_short else (1920, 1080)
            
            for p in clips_paths:
                if not os.path.exists(p): continue
                try:
                    c = VideoFileClip(p).without_audio()
                    # Resize and Crop to Fill
                    c = c.resize(height=target_size[1])
                    if c.w > target_size[0]:
                        c = c.crop(x_center=c.w/2, width=target_size[0])
                    v_clips.append(self._apply_ken_burns(c))
                except: continue

            if not v_clips:
                # Generate fallback if no clips
                from src.utils.fallback import generate_fallback_video
                fallback_path = os.path.join(self.temp_dir, "fallback_video.mp4")
                generate_fallback_video(60, topic, fallback_path)
                v_clips = [VideoFileClip(fallback_path)]

            # Intro Card
            intro = self._build_intro_card(title, topic, is_short)
            
            # Combine with transitions
            all_video_clips = self._add_transitions_sfx([intro] + v_clips)
            final_video = concatenate_videoclips(all_video_clips, method="compose")
            
            # Audio
            full_audio = AudioFileClip(audio_path)
            final_video = final_video.set_audio(full_audio.set_duration(final_video.duration))
            
            # Subtitles
            if words_with_times:
                final_video = self._add_subtitles(final_video, words_with_times)

            # Progress Bar for long videos
            if not is_short:
                final_video = self._overlay_progress_bar(final_video)

            # Render
            logger.info(f"[Editor] Rendering final video to {output_path}...")
            final_video.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="aac", 
                fps=30, 
                preset="ultrafast",
                threads=4
            )
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Assemble failed: {e}")
            return None

    def _overlay_progress_bar(self, clip, color=(0, 212, 255), height=5):
        """Thin progress bar at the bottom."""
        def make_frame(t):
            bar_w = int(clip.w * (t / clip.duration))
            return ColorClip(size=(max(1, bar_w), height), color=color).get_frame(t)
        
        bar = ColorClip(size=(clip.w, height), color=color).set_duration(clip.duration)
        # Using a mask or composite for progress effect
        # Simplest: a series of clips or a custom filter
        return clip # Placeholder for progress bar logic to avoid complex render issues
