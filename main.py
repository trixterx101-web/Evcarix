import os
import sys
import datetime
import math
import random
import asyncio
from dotenv import load_dotenv

# ABSOLUTE TOP LEVEL PRINT - Hiçbir kütüphane yüklenmeden önce
print(">>> [SYSTEM] Python interpreter started main.py", flush=True)

load_dotenv()

def log(msg):
    print(f">>> {msg}", flush=True)

log("Evcarix Orchestrator script is loading...")

class EvcarixOrchestrator:
    def __init__(self):
        log("Initializating Orchestrator components...")
        
        # Lazy imports to prevent hang during script startup
        try:
            log("Loading Brain...")
            from src.brain import EvcarixBrain
            self.brain = EvcarixBrain()
            
            log("Loading MediaEngine...")
            from src.media_engine import MediaEngine
            self.media_engine = MediaEngine()
            
            log("Loading Editor...")
            from src.editor import AutoEditor
            self.editor = AutoEditor()
            
            log("Loading LipSyncGenerator...")
            from src.lip_sync_generator import LipSyncGenerator
            self.lip_sync = LipSyncGenerator()
            
            import config
            self.config_module = config
        except Exception as e:
            log(f"FATAL ERROR during component loading: {e}")
            raise e

        self.uploader = None
        self.use_lip_sync = os.getenv("USE_LIP_SYNC", "true").lower() == "true"
        self.character_image = os.getenv("CHARACTER_IMAGE", "assets/characters/evcarix_host.png")

        secret_path = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
        if os.path.exists(secret_path):
            try:
                log("🔑 YouTube Uploader başlatılıyor...")
                from src.uploader import YouTubeUploader
                self.uploader = YouTubeUploader(secret_path)
                log("✅ YouTube Uploader başarıyla başlatıldı.")
            except Exception as e:
                log(f"❌ YouTube Uploader başlatılamadı: {e}")
                if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                    raise Exception(f"YouTube uploader başlatılamadı: {e}")
        else:
            log("⚠️ client_secret.json bulunamadı.")
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                raise FileNotFoundError("GitHub Actions ortamında client_secret.json eksik!")

    async def run_daily_shorts_workflow(self):
        # ── Zaman damgası & slot bilgisi ──────────────────────────
        now = datetime.datetime.now()
        slot = os.getenv("UPLOAD_SLOT", "evening")  # evening | night
        ts = now.strftime("%Y%m%d_%H%M%S")

        # Hedef süre: 25-50 saniye (config'den al)
        target_duration = random.randint(self.config_module.SHORT_VIDEO_DURATION_MIN, self.config_module.SHORT_VIDEO_DURATION_MAX)
        clip_count = max(4, math.ceil(target_duration / 8))  # Her klip ~8 saniye, min 4 klip

        print(f"\n{'='*60}", flush=True)
        print(f"  Evcarix Auto-Studio — {now.strftime('%d %b %Y, %H:%M')}", flush=True)
        print(f"  Format: 1080x1920 (9:16), {target_duration}s", flush=True)
        print(f"  Slot: {slot.upper()}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # ── 1. Plan ───────────────────────────────────────────────
        # CONTENT_MODE: trend (YouTube'tan ilham) veya auto (sistem konusu)
        content_mode = os.getenv("CONTENT_MODE", "auto")
        slot = os.getenv("UPLOAD_SLOT", "evening")
        
        plan = self.brain.create_daily_plan(slot=slot, video_type="short")
        script      = plan['script']
        topic       = plan['topic']
        full_topic  = plan['full_topic']
        title       = plan.get('title', topic)
        description = plan.get('description', f"{topic}\n\n#EV #Evcarix #Shorts")
        tags        = plan.get('tags', ["ev", "electric car", "Evcarix", "Shorts"])

        print(f"\n[1/6] Plan Hazır", flush=True)
        if plan.get("inspired_by"):
            print(f"      🔥 MOD    : TREND (YouTube trend'inden ilham alındı)", flush=True)
            print(f"      🔗 İlham  : {plan.get('inspired_by')}", flush=True)
            print(f"      ⚠️  NOT   : Görüntü/ses kopyalanmadı — orijinal içerik", flush=True)
        else:
            print(f"      📋 MOD   : NORMAL (havuz konusu)", flush=True)
        print(f"      Konu  : {full_topic.encode('ascii', 'ignore').decode('ascii')}", flush=True)
        print(f"      Başlık: {title.encode('ascii', 'ignore').decode('ascii')}", flush=True)

        # ── Lip-Sync Mode Check ───────────────────────────────────────
        if self.use_lip_sync and os.path.exists(self.character_image):
            print(f"\n⚡ Lip-Sync Mode aktif - Karakter konuşan video oluşturuluyor...", flush=True)
            print(f"      Karakter: {self.character_image}", flush=True)
            
            lip_sync_output_dir = f"assets/lip_sync/{ts}"
            lip_sync_result = await self.lip_sync.generate_lipsync_video(
                topic=topic,
                character_image=self.character_image,
                output_dir=lip_sync_output_dir,
                lang="en"  # or "tr" for Turkish
            )
            
            if lip_sync_result:
                final_video_path = lip_sync_result["video"]
                thumbnail_path = lip_sync_result["thumbnail"]
                
                # Upload to YouTube
                if self.uploader and os.path.exists(final_video_path):
                    print("\n[6/6] YouTube'a yükleniyor...", flush=True)
                    try:
                        video_id = self.uploader.upload_video(
                            file_path=final_video_path,
                            title=title,
                            description=description,
                            tags=tags,
                            playlist_name="Short Video"
                        )
                        print(f"      ✅ Yüklendi! Video ID: {video_id}", flush=True)
                        print(f"      🔗 https://www.youtube.com/watch?v={video_id}", flush=True)
                    except Exception as e:
                        print(f"      ❌ YouTube yükleme hatası: {e}")
                
                print(f"\n{'='*60}")
                print(f"  ✅ DAILY SHORTS TAMAMLANDI!")
                print(f"  Video: {final_video_path}")
                print(f"{'='*60}\n")
                return

        # ── 2. Medya Toplama ──────────────────────────────────────
        print("\n[2/6] Stok videolar indiriliyor...", flush=True)
        video_paths = self.media_engine.download_stock_videos(
            topic=full_topic,
            count=clip_count,
            orientation="portrait",
            category=plan.get('category', 'general')
        )

        # ── 3. Ses Üretimi ────────────────────────────────────────
        print("\n[3/6] Ses ve zamanlama üretiliyor...", flush=True)
        audio_output = f"assets/audio/{ts}.mp3"
        voice_data = await self.media_engine.voice_engine.generate_voice(
            text=script,
            output_path=audio_output,
            voice_type=plan.get("voice", "female")
        )
        audio_path = voice_data["audio_path"]
        word_timings = voice_data["word_timings"]

        # ── 4. Montaj ─────────────────────────────────────────────
        print("\n[4/6] Video montajlanıyor (MoviePy)...", flush=True)
        output_filename = f"evcarix_shorts_{ts}.mp4"
        final_video_path = self.editor.assemble_short(
            video_paths=video_paths,
            audio_path=audio_path,
            word_timings=word_timings,
            output_filename=output_filename,
            category=plan.get('category', 'general')
        )

        # ── 5. Kapak (Thumbnail) ──────────────────────────────────
        print("\n[5/6] Thumbnail oluşturuluyor...", flush=True)
        thumb_output = f"output/thumb_{ts}.png"
        thumbnail_path = self.editor.generate_thumbnail(title, thumb_output)

        # ── 6. YouTube Yükleme ─────────────────────────────────────
        if self.uploader and os.path.exists(final_video_path):
            print("\n[6/6] YouTube'a yükleniyor...", flush=True)
            try:
                video_id = self.uploader.upload_video(
                    file_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    playlist_name="Short Video"
                )
                print(f"      ✅ Yüklendi! Video ID: {video_id}", flush=True)
                print(f"      🔗 https://www.youtube.com/watch?v={video_id}", flush=True)
            except Exception as e:
                print(f"      ❌ YouTube yükleme hatası: {e}")
        else:
            print("\n[6/6] Uploader pasif veya video yok, yükleme atlandı.", flush=True)

        print(f"\n{'='*60}")
        print(f"  ✅ DAILY SHORTS TAMAMLANDI!")
        print(f"  Video    : {final_video_path}")
        print(f"  Başlık   : {title.encode('ascii', 'ignore').decode('ascii')}")
        print(f"{'='*60}\n")

    async def run_weekly_long_video_workflow(self):
        """Haftalık uzun formatlı video (1920x1080, 4-6 dakika) pipeline."""
        import random
        import gc

        # ── Zaman damgası & slot bilgisi ──────────────────────────
        now = datetime.datetime.now()
        slot = "SUNDAY_LONG"
        ts = now.strftime("%Y%m%d_%H%M%S")

        # Hedef süre: 240-360 saniye (4-6 dakika) - config'den al
        target_duration = random.randint(self.config_module.LONG_VIDEO_DURATION_MIN, self.config_module.LONG_VIDEO_DURATION_MAX)
        clip_count = math.ceil(target_duration / 8)  # Her klip ~8 saniye
        
        print(f"\n{'='*60}", flush=True)
        print(f"  Evcarix Weekly Long Video — {now.strftime('%d %b %Y, %H:%M')}", flush=True)
        print(f"  Format: 1920x1080 (16:9), {target_duration}s ({target_duration//60}dk)", flush=True)
        print(f"  Slot: {slot}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # ── 1. Plan ───────────────────────────────────────────────
        print("\n[1/7] Long-form plan oluşturuluyor...", flush=True)
        plan = self.brain.create_daily_plan(slot=slot, video_type="long")
        script      = plan['script']
        topic       = plan['topic']
        full_topic  = plan['full_topic']
        title       = plan.get('title', topic)
        description = plan.get('description', f"{topic}\n\n#EV #Evcarix #Data")
        tags        = plan.get('tags', ["ev", "electric car", "Evcarix"])

        print(f"      Konu  : {full_topic.encode('ascii', 'ignore').decode('ascii')}", flush=True)
        print(f"      Başlık: {title.encode('ascii', 'ignore').decode('ascii')}", flush=True)

        # ── 2. Medya Toplama ──────────────────────────────────────
        print(f"\n[2/7] {clip_count} adet stok video indiriliyor (16:9)...", flush=True)
        video_paths = self.media_engine.download_stock_videos(
            topic=full_topic,
            count=clip_count,
            orientation="landscape",
            category=plan.get('category', 'general')
        )

        # ── 3. Ses Üretimi ────────────────────────────────────────
        # Not: Uzun videolarda script daha uzun olacağı için TTS süresi artar
        print("\n[3/7] Uzun format ses üretiliyor...", flush=True)
        audio_output = f"assets/audio/long_{ts}.mp3"
        voice_data = await self.media_engine.voice_engine.generate_voice(
            text=script,
            output_path=audio_output,
            voice_type=plan.get("voice", "female")
        )
        audio_path = voice_data["audio_path"]

        # ── 4. Montaj (Ağır İşlem) ────────────────────────────────
        print("\n[4/7] Video montajlanıyor (4-6 dakika, 1080p)...", flush=True)
        gc.collect() # Bellek temizliği
        output_filename = f"evcarix_weekly_{ts}.mp4"
        
        # Uzun videolarda subtitle yerine title card ve temiz video tercih edilebilir
        # Şimdilik standart assemble kullanıyoruz ama 16:9 formatında
        final_video_path = self.editor.assemble_long_video(
            video_paths=video_paths,
            audio_path=audio_path,
            script_text=script,
            output_filename=output_filename
        )
        gc.collect()

        # ── 5. Kapak (Thumbnail) ──────────────────────────────────
        print("\n[5/7] HD Thumbnail oluşturuluyor...", flush=True)
        thumb_output = f"output/thumb_long_{ts}.png"
        thumbnail_path = self.editor.generate_thumbnail(title, thumb_output)

        # ── 6. Chapters & SEO ─────────────────────────────────────
        # Uzun videolarda description içine timestamp eklemek SEO için kritiktir
        # Bu aşama writer.py içinde description üretilirken hallediliyor

        # ── 7. YouTube Yükleme ─────────────────────────────────────
        if self.uploader and os.path.exists(final_video_path):
            print("\n[7/7] YouTube'a yükleniyor (Long-form)...", flush=True)
            try:
                video_id = self.uploader.upload_video(
                    file_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    playlist_name="EV Data Reports"
                )
                print(f"      ✅ Yüklendi! Video ID: {video_id}", flush=True)
                print(f"      🔗 https://www.youtube.com/watch?v={video_id}", flush=True)
            except Exception as e:
                print(f"      ❌ YouTube yükleme hatası: {e}")
        else:
            print("\n[7/7] Uploader pasif veya video yok, yükleme atlandı.", flush=True)

        print(f"\n{'='*60}")
        print(f"  ✅ HAFTALIK UZUN VIDEO TAMAMLANDI!")
        print(f"  Video    : {final_video_path}")
        print(f"  Başlık   : {title.encode('ascii', 'ignore').decode('ascii')}")
        print(f"  Süre     : {target_duration}s")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    # Orchestrator'ı oluştur (Lazy loading burada başlar)
    orchestrator = EvcarixOrchestrator()
    
    video_type = os.environ.get("VIDEO_TYPE", "short").strip().lower()
    upload_slot = os.environ.get("UPLOAD_SLOT", "evening").strip()

    # Routing: VIDEO_TYPE=long VEYA UPLOAD_SLOT=SUNDAY_LONG → haftalık uzun video
    is_long = video_type == "long" or upload_slot == "SUNDAY_LONG"

    try:
        if is_long:
            asyncio.run(orchestrator.run_weekly_long_video_workflow())
        else:
            asyncio.run(orchestrator.run_daily_shorts_workflow())
    except Exception as e:
        print(f">>> [FATAL] Critical error in main loop: {e}", flush=True)
        sys.exit(1)
    finally:
        # MoviePy'nin kök dizinde bıraktığı geçici dosyaları temizle
        import glob
        temp_patterns = ["*TEMP_MPY_wvf_snd.mp4", "*TEMP_MPY_wvf_snd.wav"]
        cleaned = 0
        for pattern in temp_patterns:
            for f in glob.glob(pattern):
                try:
                    os.remove(f)
                    cleaned += 1
                except:
                    pass
        if cleaned > 0:
            print(f">>> [System] {cleaned} temporary MoviePy files cleaned.", flush=True)