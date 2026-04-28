import os
from moviepy.editor import (
    VideoFileClip, concatenate_videoclips, TextClip,
    CompositeVideoClip, ColorClip, AudioFileClip
)


def chunk_text(text, chunk_size=6):
    """Split text into chunks of N words."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks


def assemble_short(video_paths, audio_path, script_text, output_path, fps=30):
    """
    Assembles video clips with audio and bottom subtitles.
    Subtitles appear at the bottom with a semi-transparent background.
    """
    print("[Editor] Loading video clips...")
    clips = []
    for vp in video_paths:
        try:
            c = VideoFileClip(vp).resize((1080, 1920))
            clips.append(c)
        except Exception as e:
            print(f"[Editor] Clip error ({vp}): {e}")

    if not clips:
        raise ValueError("No valid video clips to assemble.")

    video = concatenate_videoclips(clips, method="compose")

    print("[Editor] Loading audio...")
    audio = AudioFileClip(audio_path)
    duration = min(video.duration, audio.duration)
    video = video.subclip(0, duration).set_audio(audio.subclip(0, duration))

    print("[Editor] Generating subtitles...")
    chunks = chunk_text(script_text, chunk_size=6)
    chunk_duration = duration / max(len(chunks), 1)

    subtitle_clips = []
    for i, chunk in enumerate(chunks):
        start = i * chunk_duration
        end = min(start + chunk_duration, duration)

        # Semi-transparent background box
        box_height = 160
        box = ColorClip(size=(1080, box_height), color=(0, 0, 0))
        box = box.set_opacity(0.6).set_start(start).set_end(end)
        box = box.set_position(("center", 1920 - box_height - 80))

        # Subtitle text
        txt = TextClip(
            chunk,
            fontsize=52,
            color="white",
            font="DejaVu-Sans-Bold",
            method="caption",
            size=(1000, None),
            align="center"
        )
        txt = txt.set_start(start).set_end(end)
        txt = txt.set_position(("center", 1920 - box_height - 60))

        subtitle_clips.extend([box, txt])

    final = CompositeVideoClip([video] + subtitle_clips, size=(1080, 1920))

    print(f"[Editor] Writing output to {output_path}...")
    final.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="fast"
    )
    print("[Editor] Done!")
    return output_path
