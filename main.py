import asyncio
import os
import datetime
from dotenv import load_dotenv

from src.brain import EvcarixBrain
from src.media_engine import MediaEngine
from src.editor import AutoEditor
from src.uploader import YouTubeUploader

load_dotenv()


class EvcarixOrchestrator:
    def __init__(self):
        self.brain = EvcarixBrain()
        self.media_engine = MediaEngine()
        self.editor = AutoEditor()
        self.uploader = None

        secret_path = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
        if os.path.exists(secret_path):
            try:
                self.uploader = YouTubeUploader(secret_path)
            except Exception as e:
                print(f"YouTube Uploader başlatılamadı: {e}")

    async def run_daily_shorts_workflow(self):
        print(f"\n--- Evcarix Daily Workflow: {datetime.datetime.now()} ---\n")

        # 1. Plan
        plan = self.brain.create_daily_plan()
        script = plan['script']
        topic = plan['topic']
        full_topic = plan['full_topic']
        title = plan.get('title', topic)
        description = plan.get('description', f"{topic}\n\n#ev #electriccar #Evcarix #shorts")
        tags = plan.get('tags', ["ev", "electriccar", "Evcarix", "shorts"])

        print(f"\n[1/6] Plan Hazır: {full_topic}")
        print(f"       Başlık: {title}")

        # 2. Video indir
        print("\n[2/6] Stok videolar indiriliyor...")
        video_paths = self.media_engine.download_stock_videos(
            query=topic,
            output_dir="assets/temp_videos",
            count=5,
            orientation="portrait"
        )
        if not video_paths:
            print("Hata: Video bulunamadı.")
            return

        # 3. Seslendirme
        print("\n[3/6] Seslendirme yapılıyor (Aria Neural)...")
        audio_path = os.path.abspath("assets/daily_voice.mp3")
        await self.media_engine.generate_voiceover(
            text=script,
            output_path=audio_path,
            voice_type="female",
            rate="+10%"
        )

        # 4. Montaj
        print("\n[4/6] Video montajlanıyor...")
        output_filename = "daily_shorts_1.mp4"
        final_video_path = self.editor.assemble_short(
            video_paths=video_paths,
            audio_path=audio_path,
            script_text=script,
            output_filename=output_filename
        )

        # 5. Thumbnail
        print("\n[5/6] Thumbnail oluşturuluyor...")
        thumbnail_path = "output/thumbnails/daily_shorts_1.jpg"
        os.makedirs("output/thumbnails", exist_ok=True)
        self.media_engine.generate_thumbnail(
            video_path=video_paths[0],
            title=title,
            output_path=thumbnail_path
        )

        # 6. YouTube'a yükle
        if self.uploader and os.path.exists(final_video_path):
            print("\n[6/6] YouTube'a yükleniyor...")
            try:
                video_id = self.uploader.upload_video(
                    final_video_path, title, description, tags
                )
                print(f"Yüklendi! Video ID: {video_id}")
            except Exception as e:
                print(f"YouTube yükleme hatası: {e}")
        else:
            print("\n[6/6] YouTube yükleme atlanıyor.")

        print(f"\n--- Tamamlandı! ---")
        print(f"Video : {final_video_path}")
        print(f"Thumbnail: {thumbnail_path}")
        print(f"Başlık: {title}")


if __name__ == "__main__":
    orchestrator = EvcarixOrchestrator()
    asyncio.run(orchestrator.run_daily_shorts_workflow())