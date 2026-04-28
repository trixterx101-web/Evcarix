<<<<<<< HEAD
import asyncio
import os
import datetime
from dotenv import load_dotenv

# Modül importları
from src.brain import EvcarixBrain
from src.media_engine import MediaEngine
from src.editor import AutoEditor
from src.uploader import YouTubeUploader

# Ortam değişkenlerini yükle
load_dotenv()

class EvcarixOrchestrator:
    def __init__(self):
        self.brain = EvcarixBrain()
        self.media_engine = MediaEngine()
        self.editor = AutoEditor()
        self.uploader = None
        
        # YouTube Uploader'ı hazırla
        secret_path = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
        if os.path.exists(secret_path):
            try:
                self.uploader = YouTubeUploader(secret_path)
            except Exception as e:
                print(f"YouTube Uploader başlatılamadı: {e}")
        
    async def run_daily_shorts_workflow(self):
        print(f"\n--- Evcarix Daily Workflow Başlatıldı: {datetime.datetime.now()} ---\n")
        
        # 1. Plan Oluştur (Konu ve Script Al)
        plan = self.brain.create_daily_plan()
        script = plan['script']
        topic = plan['topic']
        full_topic = plan['full_topic']
        
        print(f"\n[1/5] Plan Hazır: {full_topic}")
        
        # 2. Videoları İndir (Pexels)
        print("\n[2/5] Stok videolar indiriliyor...")
        video_paths = self.media_engine.download_stock_videos(
            query=topic, 
            output_dir="assets/temp_videos", 
            count=5, 
            orientation="portrait"
        )
        
        if not video_paths:
            print("Hata: Video bulunamadı, akış durduruluyor.")
            return

        # 3. Seslendirme (Aria Neural +%10 Hız)
        print("\n[3/5] Seslendirme yapılıyor (Aria Neural)...")
        audio_path = os.path.abspath("assets/daily_voice.mp3")
        await self.media_engine.generate_voiceover(
            text=script, 
            output_path=audio_path, 
            voice_type="female", # Aria
            rate="+10%"
        )

        # 4. Montaj ve Altyazı
        print("\n[4/5] Video montajlanıyor ve altyazılar ekleniyor...")
        output_filename = "daily_shorts_1.mp4"
        final_video_path = self.editor.assemble_short(
            video_paths=video_paths, 
            audio_path=audio_path, 
            script_text=script, 
            output_filename=output_filename
        )

        # 5. YouTube'a Yükle
        if self.uploader and os.path.exists(final_video_path):
            print("\n[5/5] YouTube'a yükleniyor...")
            title = f"{topic} #Shorts #EV #Technology"
            description = f"{topic}\n\n#ev #electriccar #technology #shorts"
            tags = ["ev", "electric car", "technology", "news", "shorts"]
            
            try:
                video_id = self.uploader.upload_video(final_video_path, title, description, tags)
                print(f"Video başarıyla yüklendi! ID: {video_id}")
            except Exception as e:
                print(f"YouTube yükleme hatası: {e}")
        else:
            print("\n[5/5] YouTube yükleme atlanıyor (Uploader hazır değil veya video yok).")

        print(f"\n--- İşlem Başarıyla Tamamlandı! ---")
        print(f"Final Video: {final_video_path}")

if __name__ == "__main__":
    orchestrator = EvcarixOrchestrator()
    asyncio.run(orchestrator.run_daily_shorts_workflow())
=======
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
>>>>>>> d0b04483447cc004bbce9fb8f096e62cafafcaca
