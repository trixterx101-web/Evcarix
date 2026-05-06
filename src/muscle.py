import os
import json
import asyncio
import datetime
from src.media_engine import MediaEngine
from src.editor import AutoEditor
from src.uploader import YouTubeUploader

class EvcarixMuscle:
    def __init__(self):
        self.media_engine = MediaEngine()
        self.editor = AutoEditor()
        self.uploader = None
        
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
        if os.path.exists(client_secret):
            self.uploader = YouTubeUploader(client_secret)

    async def execute_plan(self, plan_path="daily_plan.json"):
        print("Evcarix Muscle: Plan işleniyor...")
        if not os.path.exists(plan_path):
            print(f"Hata: {plan_path} bulunamadı!")
            return

        with open(plan_path, "r", encoding="utf-8") as f:
            plan = json.load(f)

        timestamp = plan['timestamp']
        config = plan['config']
        script = plan['script']
        voice_type = plan['voice']
        specific_topic = plan['topic']

        # Gerekli klasörler
        for folder in ["assets", "output"]:
            if not os.path.exists(folder):
                os.makedirs(folder)

        # 1. Medya Hazırla
        print(f"Ses ({voice_type}) ve görüntü hazırlanıyor...")
        audio_path = os.path.abspath(f"assets/audio_{timestamp}.mp3")
        video_clips_dir = os.path.abspath(f"assets/clips_{timestamp}")
        os.makedirs(video_clips_dir, exist_ok=True)
        
        await self.media_engine.generate_voiceover(script, audio_path, voice_type=voice_type)
        
        orientation = "portrait" if config['type'] == "short" else "landscape"
        video_paths = self.media_engine.download_stock_videos(
            plan, 
            target_clip_count=10 if config['type'] == "long" else 6
        )
        
        # 2. Montaj
        print(f"Video montajlanıyor ({config['type']})...")
        output_name = f"Evcarix_{timestamp}.mp4"
        
        if config['type'] == "short":
            output_path = self.editor.assemble_short(video_paths, audio_path, script, output_name)
        else:
            bg_music = os.path.abspath("assets/background_music.mp3")
            output_path = self.editor.assemble_long_video(video_paths, audio_path, script, output_name, bg_music_path=bg_music)
        
        # 3. Thumbnail
        if video_paths:
            print("Thumbnail oluşturuluyor...")
            thumb_path = os.path.join("output", f"Thumb_{timestamp}.jpg")
            self.media_engine.generate_thumbnail(video_paths[0], specific_topic, thumb_path)
        
        # 4. Yükle
        if self.uploader and os.path.exists(output_path):
            print("YouTube'a yükleniyor...")
            title = f"{specific_topic} #Shorts #EV" if config['type'] == "short" else f"Elektrikli Araç Dünyası: {specific_topic}"
            description = f"{specific_topic} hakkında en son gelişmeler Evcarix'te!\n\n#ev #electriccar #technology"
            tags = ["ev", "electric car", "technology", "news"]
            
            try:
                self.uploader.upload_video(output_path, title, description, tags)
            except Exception as e:
                print(f"Yükleme hatası: {e}")
        
        print("Evcarix Muscle: İşlem tamamlandı.")

if __name__ == "__main__":
    muscle = EvcarixMuscle()
    asyncio.run(muscle.execute_plan())
