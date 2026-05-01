import asyncio
import os
import random
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
                print("✅ YouTube Uploader başarıyla başlatıldı.")
            except Exception as e:
                print(f"❌ YouTube Uploader başlatılamadı: {e}")
                # Hata durumunda işlemi durdur ki neden yüklenemediğini anlayalım
                if os.getenv("CI"):
                    raise Exception(f"YouTube uploader başlatılamadı: {e}")
        else:
            print("⚠️ client_secret.json bulunamadı.")
            if os.getenv("CI"):
                raise FileNotFoundError("GitHub Actions ortamında client_secret.json eksik!")

    async def run_daily_shorts_workflow(self):
        # ── Zaman damgası & slot bilgisi ──────────────────────────
        now = datetime.datetime.now()
        slot = os.getenv("UPLOAD_SLOT", "evening")  # evening | night
        ts = now.strftime("%Y%m%d_%H%M%S")

        print(f"\n{'='*60}")
        print(f"  Evcarix Auto-Studio — {now.strftime('%d %b %Y, %H:%M')}")
        print(f"  Slot: {slot.upper()}")
        print(f"{'='*60}\n")

        # ── 1. Plan ───────────────────────────────────────────────
        plan = self.brain.create_daily_plan(slot=slot)
        script      = plan['script']
        topic       = plan['topic']
        full_topic  = plan['full_topic']
        title       = plan.get('title', topic)
        description = plan.get('description', f"{topic}\n\n#EV #Evcarix #Shorts")
        tags        = plan.get('tags', ["ev", "electric car", "Evcarix", "Shorts"])

        print(f"\n[1/6] Plan Hazır")
        print(f"      Konu  : {full_topic.encode('ascii', 'ignore').decode('ascii')}")
        print(f"      Başlık: {title.encode('ascii', 'ignore').decode('ascii')}")

        # ── 2. AI Video Klip Üretimi ──────────────────────────────────
        print("\n[2/6] AI video klip üretimi (5-10 saniye)...")
        ai_video_clips = self.media_engine.generate_ai_video_clips(
            topic=topic,
            count=6,
            output_dir=f"assets/ai_videos/{ts}",
            duration=8  # 8 saniye per klip
        )

        # ── 3. Stok videolar (AI yetersizse) ───────────────────────
        video_paths = []
        if len(ai_video_clips) < 4:
            print("\n[3/6] AI videolar yetersiz, stok videolar indiriliyor...")
            import re
            search_query = re.sub(r'[^\w\s]', '', topic).strip()
            video_paths = self.media_engine.download_stock_videos(
                query=search_query,
                output_dir=f"assets/temp_videos/{ts}",
                count=5,
                orientation="portrait",
                category=plan.get("category", "general")
            )
        
        # Combine AI clips and stock videos
        all_video_clips = ai_video_clips + video_paths
        random.shuffle(all_video_clips)
        
        ai_fallback_images = []
        if len(all_video_clips) < 2:
            print("⚠️ Video kaynağı az — AI görüntü fallback devreye giriyor...")
            ai_fallback_images = self.media_engine.generate_ai_fallback_images(topic, count=5, output_dir=f"assets/ai_fallback/{ts}")

        # ── 4. Seslendirme ────────────────────────────────────────
        print("\n[4/6] Seslendirme yapılıyor...")
        audio_path = os.path.abspath(f"assets/voice_{ts}.mp3")
        voice_result = await self.media_engine.generate_voiceover(
            text=script,
            output_path=audio_path,
            voice_type=plan.get('voice', 'female'),
            rate=random.choice(["+0%", "+2%", "-2%"])   # Hafif hız varyasyonu
        )
        word_timings = voice_result['word_timings']

        # ── 5. Video montajı ──
        print("\n[5/6] Video montajlanıyor...")
        output_filename = f"shorts_{ts}.mp4"
        final_video_path = self.editor.assemble_short(
            video_paths=all_video_clips,
            audio_path=audio_path,
            word_timings=word_timings,
            output_filename=output_filename,
            ai_fallback_images=ai_fallback_images if ai_fallback_images else None,
            category=plan.get("category", "general")
        )

        # ── 7. YouTube'a yükle ────────────────────────────────────
        if self.uploader and os.path.exists(final_video_path):
            print("\n[7/7] YouTube'a yükleniyor...")

            # İnsan gibi küçük bir bekleme (5-25 sn) yükleme öncesi
            pre_upload_delay = random.randint(5, 25)
            print(f"      Yükleme öncesi {pre_upload_delay}sn bekleniyor...")
            await asyncio.sleep(pre_upload_delay)

            try:
                video_id = self.uploader.upload_video(
                    final_video_path, title, description, tags
                )
                print(f"      ✅ Yüklendi! Video ID: {video_id}")
                print(f"      🔗 https://www.youtube.com/watch?v={video_id}")

            except Exception as e:
                print(f"      ❌ YouTube yükleme hatası: {e}")
                raise e # GitHub Actions'ın hata olduğunu anlaması için hatayı fırlatıyoruz
        else:
            print("\n[6/6] YouTube yükleme atlandı (uploader yok veya video bulunamadı).")

        print(f"\n{'='*60}")
        print(f"  ✅ TAMAMLANDI!")
        print(f"  Video    : {final_video_path}")
        print(f"  Başlık   : {title.encode('ascii', 'ignore').decode('ascii')}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    orchestrator = EvcarixOrchestrator()
    asyncio.run(orchestrator.run_daily_shorts_workflow())