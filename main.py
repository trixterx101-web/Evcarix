import os
import sys
import datetime
import math
import random
import asyncio
from dotenv import load_dotenv

# ABSOLUTE TOP LEVEL PRINT - Hiçbir kütüphane yüklenmeden önce
print(">>> [SYSTEM] Python interpreter started main.py", flush=True)

# Add project root to sys.path for robust imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

def log(msg):
    print(f">>> {msg}", flush=True)

print("=== EVCARIX NEW PIPELINE ACTIVE ===", flush=True)

class EvcarixOrchestrator:
    def __init__(self):
        log("Initializating Orchestrator components...")
        
        # Lazy imports to prevent hang during script startup
        try:
            log("Loading Brain (from src.brain)...")
            from src.brain import EvcarixBrain
            log("Initializing Brain...")
            self.brain = EvcarixBrain()
            log("Brain loaded successfully.")
            
            log("Loading MediaEngine (from src.media_engine)...")
            from src.media_engine import MediaEngine
            log("Initializing MediaEngine...")
            self.media_engine = MediaEngine()
            log("MediaEngine loaded successfully.")
            
            log("Loading Editor (from src.editor)...")
            from src.editor import AutoEditor
            log("Initializing Editor...")
            self.editor = AutoEditor()
            log("Editor loaded successfully.")
            
            log("Loading LipSyncGenerator (from src.lip_sync_generator)...")
            from src.lip_sync_generator import LipSyncGenerator
            log("Initializing LipSyncGenerator...")
            self.lip_sync = LipSyncGenerator()
            log("LipSyncGenerator loaded successfully.")
            
            log("Loading Config...")
            import config
            self.config_module = config
            log("Config loaded successfully.")
        except Exception as e:
            log(f"FATAL ERROR during component loading: {e}")
            raise e

        self.uploader = None
        self.use_lip_sync = os.getenv("USE_LIP_SYNC", "true").lower() == "true"
        self.character_image = os.getenv("CHARACTER_IMAGE", "assets/characters/evcarix_host.png")

        secret_path = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
        if os.path.exists(secret_path):
            try:
                log("[Uploader] YouTube Uploader baslatiliyor...")
                from src.uploader import YouTubeUploader
                self.uploader = YouTubeUploader(secret_path)
                log("[Uploader] YouTube Uploader basariyla baslatildi.")
            except Exception as e:
                log(f"[Uploader] YouTube uploader başlatılamadı: {e}")
                log("[Uploader] ⚠️ UYARI: Video üretilecek ancak otomatik yükleme yapılmayacak.")
                # CI ortamında bile artık raise etmiyoruz, video üretilsin ki artifact'tan alınabilsin.
                self.uploader = None

    async def run_daily_shorts_workflow(self):
        # ── Zaman damgası & slot bilgisi ──────────────────────────
        now = datetime.datetime.now()
        slot = os.getenv("UPLOAD_SLOT", "evening")  # evening | night
        ts = now.strftime("%Y%m%d_%H%M%S")

        # Hedef süre: 25-50 saniye (config'den al)
        target_duration = random.randint(self.config_module.SHORT_VIDEO_DURATION_MIN, self.config_module.SHORT_VIDEO_DURATION_MAX)
        clip_count = max(6, math.ceil(target_duration / 4))  # Her klip ~5s olduğu için /4 güvenli

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
                if self.uploader and self.uploader.youtube and os.path.exists(final_video_path):
                    print("\n[6/6] YouTube'a yükleniyor...", flush=True)
                    try:
                        video_id = self.uploader.upload_video(
                            file_path=final_video_path,
                            title=title,
                            description=description,
                            tags=tags,
                            playlist_name="Short Video",
                            thumbnail_path=thumbnail_path if os.path.exists(thumbnail_path) else None
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
        video_paths = await self.media_engine.download_stock_videos(
            plan=plan,
            target_clip_count=clip_count,
            topic=full_topic
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

        # ── 5. Kapak (Thumbnail) İptal Edildi ─────────────────────
        print("\n[5/6] Thumbnail üretimi manuel yükleme için atlandı.", flush=True)
        thumbnail_path = None

        # ── 6. YouTube Yükleme ─────────────────────────────────────────
        if self.uploader and self.uploader.youtube and os.path.exists(final_video_path):
            print("\n[6/6] YouTube'a yükleniyor...", flush=True)
            print("      ⚠️  Thumbnail manuel eklenecek, atlanıyor.", flush=True)
            try:
                thumb_path = thumbnail_path if (thumbnail_path and os.path.exists(thumbnail_path)) else None
                video_id = self.uploader.upload_video(
                    file_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    playlist_name="Short Video",
                    thumbnail_path=thumb_path
                )
                print(f"      ✅ Yüklendi! Video ID: {video_id}", flush=True)
                print(f"      🔗 https://www.youtube.com/watch?v={video_id}", flush=True)
            except Exception as e:
                print(f"      ❌ YouTube yükleme hatası: {e}", flush=True)
                if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                    raise
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
        clip_count = math.ceil(target_duration / 5)  # Her klip ~5 saniye
        
        print(f"\n{'='*60}", flush=True)
        print(f"  Evcarix Weekly Long Video — {now.strftime('%d %b %Y, %H:%M')}", flush=True)
        print(f"  Format: 1920x1080 (16:9), {target_duration}s ({target_duration//60}dk)", flush=True)
        print(f"  Slot: {slot}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # ── 1. Plan ───────────────────────────────────────────────
        print("\n[1/7] Long-form plan oluşturuluyor...", flush=True)
        # Brain'e hedef süreyi ve video tipini bildir
        plan = self.brain.create_daily_plan(slot=slot, video_type="long")
        script      = plan['script']
        topic       = plan['topic']
        full_topic  = plan['full_topic']
        title       = plan.get('title', topic)
        description = plan.get('description', f"{topic}\n\n#EV #Evcarix #Data")
        tags        = plan.get('tags', ["ev", "electric car", "Evcarix"])

        print(f"      Konu  : {full_topic.encode('ascii', 'ignore').decode('ascii')}", flush=True)
        print(f"      Başlık: {title.encode('ascii', 'ignore').decode('ascii')}")

        # ── 2. Medya Toplama ──────────────────────────────────────
        print(f"\n[2/7] {clip_count} adet stok video indiriliyor (16:9)...", flush=True)
        video_paths = await self.media_engine.download_stock_videos(
            plan=plan,
            target_clip_count=clip_count,
            topic=full_topic
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
        print("\n[4/7] Video montajlanıyor (16:9 format)...", flush=True)
        gc.collect() # Bellek temizliği
        output_filename = f"evcarix_weekly_{ts}.mp4"
        
        # assemble_weekly_long_video: 16:9 formatında, title/outro kartlı premium montaj
        final_video_path = self.editor.assemble_weekly_long_video(
            video_clips=video_paths,
            audio_path=audio_path,
            title=title,
            target_duration=target_duration,
            output_path=output_filename
        )
        gc.collect()

        # ── 5. Kapak (Thumbnail) — Uzun video için profesyonel üret ─────────
        print("\n[5/7] Thumbnail üretiliyor (1280x720 professional)...", flush=True)
        thumbnail_path = None
        try:
            from src.thumbnail_generator import ThumbnailGenerator
            import re as _re
            tg = ThumbnailGenerator()
            thumb_out = os.path.join("output", f"thumbnail_{ts}.jpg")
            # Stat'ı başlıktan çıkar
            _stat = ""
            for _pat in [r'(\d+%)', r'(\d+V)', r'(\d+KM)', r'(\d+K)', r'(\$\d+[K]?)', r'(\d+YR)']:
                _m = _re.search(_pat, title.upper())
                if _m:
                    _stat = _m.group(1)
                    break
            if not _stat and "?" in title:
                _stat = "FACT?"
            elif not _stat:
                _stat = "DATA"
            thumbnail_path = tg.create(
                title=title,
                stat=_stat,
                category=plan.get('category', 'default'),
                output_path=thumb_out,
                is_short=False
            )
            if thumbnail_path and os.path.exists(thumbnail_path):
                print(f"      ✅ Thumbnail hazır: {thumbnail_path}", flush=True)
            else:
                thumbnail_path = None
                print("      ⚠️ Thumbnail üretilemedi, atlanıyor.", flush=True)
        except Exception as e:
            print(f"      ⚠️ Thumbnail hatası: {e}", flush=True)
            thumbnail_path = None

        # ── 6. Chapters & SEO ─────────────────────────────────────
        # Uzun videolarda description içine timestamp eklemek SEO için kritiktir
        # Bu aşama writer.py içinde description üretilirken hallediliyor

        # ── 7. YouTube Yükleme ─────────────────────────────────────────
        if self.uploader and self.uploader.youtube and os.path.exists(final_video_path):
            print("\n[7/7] YouTube'a yükleniyor (Long-form)...", flush=True)
            print("      ⚠️  Thumbnail manuel eklenecek, atlanıyor.", flush=True)
            try:
                thumb_path = thumbnail_path if (thumbnail_path and os.path.exists(thumbnail_path)) else None
                video_id = self.uploader.upload_video(
                    file_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    playlist_name="EV Data Reports",
                    thumbnail_path=thumb_path
                )
                print(f"      ✅ Yüklendi! Video ID: {video_id}", flush=True)
                print(f"      🔗 https://www.youtube.com/watch?v={video_id}", flush=True)
            except Exception as e:
                print(f"      ❌ YouTube yükleme hatası: {e}", flush=True)
                if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                    raise
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