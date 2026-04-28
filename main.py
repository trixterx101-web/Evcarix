import os
import json
from dotenv import load_dotenv

load_dotenv()

from src.brain import Brain
from src.media_engine import MediaEngine
from src.editor import assemble_short

# Optional TTS
try:
    import edge_tts
    import asyncio
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "thumbnails"), exist_ok=True)


async def generate_audio(script, output_path, voice="en-US-AriaNeural"):
    """Generate TTS audio using edge-tts."""
    communicate = edge_tts.Communicate(script, voice)
    await communicate.save(output_path)
    print(f"[TTS] Audio saved: {output_path}")


def main():
    print("=" * 50)
    print("  EVCARIX — Automated YouTube Shorts Pipeline")
    print("=" * 50)

    # Step 1: Create daily plan
    print("\n[Step 1/6] Creating daily content plan...")
    brain = Brain()
    plans = brain.create_daily_plan(num_videos=1)

    media = MediaEngine()

    for plan in plans:
        idx = plan["video_index"]
        topic = plan["topic"]
        title = plan["title"]
        script = plan["script"]
        description = plan["description"]

        print(f"\n{'=' * 40}")
        print(f"Processing Video {idx}: {title}")
        print(f"{'=' * 40}")

        # Step 2: Get video clips
        print(f"\n[Step 2/6] Downloading video clips for: {topic[:50]}...")
        clips = media.get_video_clips(topic, num_clips=4)
        if not clips:
            print("[Main] No clips found, skipping video.")
            continue

        # Step 3: Generate audio
        audio_path = os.path.join(OUTPUT_DIR, f"audio_{idx}.mp3")
        if TTS_AVAILABLE:
            print(f"\n[Step 3/6] Generating TTS audio...")
            import asyncio
            asyncio.run(generate_audio(script, audio_path))
        else:
            print("[Step 3/6] edge-tts not available, skipping audio.")
            audio_path = None

        if not audio_path or not os.path.exists(audio_path):
            print("[Main] No audio file, skipping video.")
            continue

        # Step 4: Assemble video
        print(f"\n[Step 4/6] Assembling video...")
        video_output = os.path.join(OUTPUT_DIR, f"daily_shorts_{idx}.mp4")
        try:
            assemble_short(
                video_paths=clips,
                audio_path=audio_path,
                script_text=script,
                output_path=video_output
            )
        except Exception as e:
            print(f"[Main] Assembly error: {e}")
            continue

        # Step 5: Generate thumbnail
        print(f"\n[Step 5/6] Generating thumbnail...")
        thumbnail_path = os.path.join(OUTPUT_DIR, "thumbnails", f"daily_shorts_{idx}.jpg")
        media.generate_thumbnail(
            video_path=clips[0],
            title=title,
            output_path=thumbnail_path
        )

        # Step 6: Upload to YouTube (optional)
        print(f"\n[Step 6/6] Ready to upload:")
        print(f"  Video   : {video_output}")
        print(f"  Thumbnail: {thumbnail_path}")
        print(f"  Title   : {title}")
        print(f"  Description:\n{description[:200]}...")

        # Save upload info
        upload_info = {
            "video_path": video_output,
            "thumbnail_path": thumbnail_path,
            "title": title,
            "description": description,
            "tags": plan["tags"]
        }
        info_path = os.path.join(OUTPUT_DIR, f"upload_info_{idx}.json")
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump(upload_info, f, indent=2, ensure_ascii=False)
        print(f"  Upload info saved: {info_path}")

    print("\n✅ Pipeline complete!")


if __name__ == "__main__":
    main()
