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
