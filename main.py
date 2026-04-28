import os
import json
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

from src.brain import Brain
from src.media_engine import MediaEngine
from src.editor import assemble_short

# İsteğe bağlı TTS (Seslendirme)
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
    """edge-tts kullanarak ses dosyası oluşturur."""
    communicate = edge_tts.Communicate(script, voice)
    await communicate.save(output_path)
    print(f"[TTS] Ses kaydedildi: {output_path}")


def main():
    print("=" * 50)
    print("  EVCARIX — Otomatik YouTube Shorts Hattı")
    print("=" * 50)

    # Adım 1: Günlük planı oluştur
    print("\n[Adım 1/6] Günlük içerik planı hazırlanıyor...")
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
        print(f"Video {idx} İşleniyor: {title}")
        print(f"{'=' * 40}")

        # Adım 2: Video kliplerini indir
        print(f"\n[Adım 2/6] Klipler indiriliyor: {topic[:50]}...")
        clips = media.get_video_clips(topic, num_clips=4)
        if not clips:
            print("[Main] Klip bulunamadı, bu video atlanıyor.")
            continue

        # Adım 3: Seslendirme oluştur
        audio_path = os.path.join(OUTPUT_DIR, f"audio_{idx}.mp3")
        if TTS_AVAILABLE:
            print(f"\n[Adım 3/6] Seslendirme (TTS) üretiliyor...")
            import asyncio
            try:
                asyncio.run(generate_audio(script, audio_path))
            except Exception as e:
                print(f"[TTS] Hata: {e}")
                audio_path = None
        else:
            print("[Adım 3/6] edge-tts kütüphanesi eksik, ses atlanıyor.")
            audio_path = None

        if not audio_path or not os.path.exists(audio_path):
            print("[Main] Ses dosyası yok, video oluşturulamaz.")
            continue

        # Adım 4: Videoyu birleştir (Montaj)
        print(f"\n[Adım 4/6] Montaj yapılıyor...")
        video_output = os.path.join(OUTPUT_DIR, f"daily_shorts_{idx}.mp4")
        try:
            assemble_short(
                video_paths=clips,
                audio_path=audio_path,
                script_text=script,
                output_path=video_output
            )
        except Exception as e:
            print(f"[Main] Montaj hatası: {e}")
            continue

        # Adım 5: Kapak fotoğrafı (Thumbnail) oluştur
        print(f"\n[Adım 5/6] Kapak fotoğrafı üretiliyor...")
        thumbnail_path = os.path.join(OUTPUT_DIR, "thumbnails", f"daily_shorts_{idx}.jpg")
        media.generate_thumbnail(
            video_path=clips[0],
            title=title,
            output_path=thumbnail_path
        )

        # Adım 6: YouTube'a Yükle
        print(f"\n[Adım 6/6] YouTube'a yükleniyor...")
        try:
            # Mevcut upload_video.py dosyasındaki fonksiyonu çağırır
            from upload_video import upload_video_to_youtube
            
            upload_video_to_youtube(
                video_file=video_output,
                title=title,
                description=description,
                tags=plan["tags"],
                thumbnail_file=thumbnail_path
            )
            print("✅ Video başarıyla YouTube'a yüklendi!")
        except Exception as e:
            print(f"❌ Yükleme sırasında bir hata oluştu: {e}")

    print("\n✅ Tüm süreç tamamlandı!")


if __name__ == "__main__":
    main()
