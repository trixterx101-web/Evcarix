import os
import sys
import datetime
import math
import random
import asyncio
from dotenv import load_dotenv

# ABSOLUTE TOP LEVEL PRINT - Hiçbir kütüphane yüklenmeden önce
print(">>> [SYSTEM] Python interpreter started main.py v2", flush=True)

# Add project root to sys.path for robust imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

def log(message: str) -> None:
    """Flush-guaranteed print helper used throughout the orchestrator."""
    print(message, flush=True)

def safe_path(path, label="file") -> str:
    """Path'in None olmadığını ve dosyanın var olduğunu doğrular."""
    if path is None:
        raise ValueError(f"[Main] {label} path is None")
    if not os.path.exists(path):
        raise FileNotFoundError(f"[Main] {label} not found: {path}")
    return path

class EvcarixOrchestrator:
    def __init__(self):
        log("Initializating Orchestrator components...")
        
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
            
            log("Loading New Split-Screen Engine Components...")
            from src.footage_library import FootageLibrary
            from src.bottom_panel import generate_bottom_panel
            from src.compositor import VideoCompositor
            self.footage_library = FootageLibrary()
            self.compositor = VideoCompositor()
            log("New Production Engine components loaded successfully.")

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
                self.uploader = None

    def _upload_thumbnail(self, video_id: str, title: str, topic: str,
                          thumb_path: str = None, is_short: bool = False) -> None:
        """Thumbnail üretir ve YouTube'a yükler. Hata olursa sessizce geçer."""
        if not video_id:
            return
        try:
            from src.thumbnail_generator import ThumbnailGenerator
            tg = ThumbnailGenerator()
            if not thumb_path or not os.path.exists(thumb_path):
                out_dir = "output"
                os.makedirs(out_dir, exist_ok=True)
                thumb_path = os.path.join(out_dir, f"thumbnail_{video_id}.jpg")
                tg.create(title=title, topic=topic, output_path=thumb_path, is_short=is_short)
            if os.path.exists(thumb_path) and self.uploader and self.uploader.youtube:
                self.uploader.youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=thumb_path
                ).execute()
                log(f"      ✅ Thumbnail yüklendi: {thumb_path}")
        except Exception as e:
            log(f"      ⚠️ Thumbnail yükleme atlandı: {e}")

    async def run_daily_shorts_workflow(self):
        # ── Zaman damgası & slot bilgisi ──────────────────────────
        now = datetime.datetime.now()
        slot = os.getenv("UPLOAD_SLOT", "evening")
        ts = now.strftime("%Y%m%d_%H%M%S")

        target_duration = random.randint(self.config_module.SHORT_VIDEO_DURATION_MIN, self.config_module.SHORT_VIDEO_DURATION_MAX)
        clip_count = max(6, math.ceil(target_duration / 4))

        print(f"\n{'='*60}", flush=True)
        print(f"  Evcarix Auto-Studio — {now.strftime('%d %b %Y, %H:%M')}", flush=True)
        print(f"  Format: 1080x1920 (9:16), {target_duration}s", flush=True)
        print(f"  Slot: {slot.upper()}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # ── 1. Plan ───────────────────────────────────────────────
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
                lang="en"
            )
            
            if lip_sync_result:
                final_video_path = lip_sync_result["video"]
                thumbnail_path   = lip_sync_result["thumbnail"]
                
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
                        log(f"      ✅ Yüklendi! Video ID: {video_id}")
                        log(f"      🔗 https://www.youtube.com/watch?v={video_id}")
                        # ── Thumbnail yükle ──────────────────────────────────
                        self._upload_thumbnail(video_id, title, topic,
                                               thumb_path=thumbnail_path, is_short=True)
                    except Exception as e:
                        print(f"      ❌ YouTube yükleme hatası: {e}")
                
                print(f"\n{'='*60}")
                print(f"  ✅ DAILY SHORTS TAMAMLANDI!")
                print(f"  Video: {final_video_path}")
                print(f"{'='*60}\n")
                return

        # ── 2. Medya Toplama ─────────────────────────────────────
        print("\n[2/6] Footage toplanıyor (YouTube CC / Pexels)...", flush=True)
        cat_map = {
            "battery": "battery_tech", "electric": "electric_vehicle", "ev": "electric_vehicle",
            "ai": "artificial_intelligence", "neural": "artificial_intelligence",
            "robot": "robotics", "future": "future_tech", "quantum": "future_tech"
        }
        topic_key = "default"
        for k, v in cat_map.items():
            if k in full_topic.lower():
                topic_key = v
                break

        top_video_list = self.footage_library.get_fresh_clips(topic=topic_key, count=6, format="shorts")
        top_video = top_video_list[0] if top_video_list else None
        
        if not top_video:
            print("      ⚠️ Hiç klip bulunamadı, fallback üretiliyor...", flush=True)
            from src.utils.fallback import generate_fallback_video
            top_video = f"assets/footage/fallback_{ts}.mp4"
            os.makedirs("assets/footage", exist_ok=True)
            generate_fallback_video(30, topic, top_video)
            top_video_list = [top_video]

        # ── 3. Ses Üretimi ────────────────────────────────────────
        print("\n[3/6] Ses üretiliyor...", flush=True)
        audio_output = f"assets/audio/{ts}.mp3"
        voice_data = await self.media_engine.voice_engine.generate_voice(
            text=script,
            output_path=audio_output,
            voice_type=plan.get("voice", "female")
        )
        
        if not voice_data or not voice_data.get("audio_path"):
            raise RuntimeError("[Main] TTS üretimi başarısız oldu.")
             
        audio_path = safe_path(voice_data["audio_path"], "TTS Audio")
        
        from moviepy.editor import AudioFileClip
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        audio_clip.close()

        # ── 4. Alt Panel & Montaj ─────────────────────────────────
        print("\n[4/6] Split-Screen Video üretiliyor (3D Panel + Subtitles)...", flush=True)
        
        from src.bottom_panel import generate_bottom_panel
        bottom_panel_path = f"assets/panels/bottom_{ts}.mp4"
        bottom_res = generate_bottom_panel(
            topic=topic_key,
            subtitle_text=script,
            duration=duration,
            output_path=bottom_panel_path,
            panel_size=(1080, 635)
        )
        
        if not bottom_res:
            raise RuntimeError("[Main] Alt panel üretilemedi.")

        top_assembled = f"assets/footage/top_assembled_{ts}.mp4"
        self.editor.assemble(
            clips_paths=top_video_list,
            audio_path=audio_path,
            output_path=top_assembled,
            is_short=True,
            title=script,
        )

        output_filename = f"evcarix_shorts_{ts}.mp4"
        final_video_path = self.compositor.compose_split_screen(
            top_video=top_assembled,
            bottom_panel=bottom_res,
            audio_path=audio_path,
            output_filename=output_filename,
            video_format="shorts"
        )

        if not final_video_path or not os.path.exists(final_video_path):
            raise RuntimeError(f"[Main] Montaj çıktısı bulunamadı.")
        print(f"      ✅ Split-Screen Video hazır: {final_video_path}", flush=True)

        # ── 5. Thumbnail ──────────────────────────────────────────
        print("\n[5/6] Thumbnail üretiliyor...", flush=True)
        thumbnail_path = None
        try:
            from src.thumbnail_generator import ThumbnailGenerator
            tg = ThumbnailGenerator()
            thumb_out = os.path.join("output", f"thumbnail_{ts}.jpg")
            os.makedirs("output", exist_ok=True)
            thumbnail_path = tg.create(
                title=title, topic=topic_key,
                output_path=thumb_out, is_short=True
            )
            if thumbnail_path and os.path.exists(thumbnail_path):
                print(f"      ✅ Thumbnail hazır: {thumbnail_path}", flush=True)
            else:
                thumbnail_path = None
        except Exception as e:
            print(f"      ⚠️ Thumbnail hatası: {e}", flush=True)
            thumbnail_path = None

        # ── 6. YouTube Yükleme ────────────────────────────────────
        if self.uploader and self.uploader.youtube and os.path.exists(final_video_path):
            print("\n[6/6] YouTube'a yükleniyor...", flush=True)
            try:
                video_id = self.uploader.upload_video(
                    file_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    playlist_name="Short Video",
                    thumbnail_path=None   # upload_video'ya verme, aşağıda ayrıca yüklüyoruz
                )
                log(f"      ✅ Yüklendi! Video ID: {video_id}")
                log(f"      🔗 https://www.youtube.com/watch?v={video_id}")
                # ── Thumbnail YouTube'a yükle ────────────────────────
                self._upload_thumbnail(video_id, title, topic_key,
                                       thumb_path=thumbnail_path, is_short=True)
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
        import gc

        now = datetime.datetime.now()
        slot = "SUNDAY_LONG"
        ts = now.strftime("%Y%m%d_%H%M%S")

        target_duration = random.randint(self.config_module.LONG_VIDEO_DURATION_MIN, self.config_module.LONG_VIDEO_DURATION_MAX)
        clip_count = math.ceil(target_duration / 5)
        
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
        print(f"      Başlık: {title.encode('ascii', 'ignore').decode('ascii')}")

        # ── 2. Medya Toplama ─────────────────────────────────────
        print(f"\n[2/7] Footage toplanıyor (16:9 CC / Pexels)...", flush=True)
        cat_map = {
            "battery": "battery_tech", "electric": "electric_vehicle", "ev": "electric_vehicle",
            "ai": "artificial_intelligence", "neural": "artificial_intelligence",
            "robot": "robotics", "future": "future_tech", "quantum": "future_tech"
        }
        topic_key = "default"
        for k, v in cat_map.items():
            if k in full_topic.lower():
                topic_key = v
                break

        top_video_list = self.footage_library.get_fresh_clips(topic=topic_key, count=clip_count, format="long")
        top_video = top_video_list[0] if top_video_list else None
        
        if not top_video:
            print("      ⚠️ Klip bulunamadı, fallback üretiliyor...", flush=True)
            from src.utils.fallback import generate_fallback_video
            top_video = f"assets/footage/fallback_long_{ts}.mp4"
            generate_fallback_video(60, topic, top_video)
            top_video_list = [top_video]

        # ── 3. Ses Üretimi ────────────────────────────────────────
        print("\n[3/7] Uzun format ses üretiliyor...", flush=True)
        audio_output = f"assets/audio/long_{ts}.mp3"
        voice_data = await self.media_engine.voice_engine.generate_voice(
            text=script,
            output_path=audio_output,
            voice_type=plan.get("voice", "female")
        )
        audio_path = voice_data["audio_path"]
        
        from moviepy.editor import AudioFileClip
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration
        audio_clip.close()

        # ── 4. Tam 16:9 Video (multi-clip + altyazı, yan panel yok) ──
        print("\n[4/7] Full 16:9 Video üretiliyor (multi-clip + altyazı)...", flush=True)
        gc.collect()

        output_filename = f"evcarix_weekly_{ts}.mp4"
        final_video_path = os.path.join("output", output_filename)
        os.makedirs("output", exist_ok=True)

        assembled = self.editor.assemble(
            clips_paths=top_video_list,
            audio_path=audio_path,
            output_path=final_video_path,
            is_short=False,
            title=script,
        )
        if not assembled or not os.path.exists(final_video_path):
            raise RuntimeError("[Main] Montaj çıktısı bulunamadı.")
        print(f"      ✅ Video hazır: {final_video_path}", flush=True)
        gc.collect()

        # ── 5. Thumbnail ──────────────────────────────────────────
        print("\n[5/7] Thumbnail üretiliyor (1280x720 professional)...", flush=True)
        thumbnail_path = None
        try:
            from src.thumbnail_generator import ThumbnailGenerator
            import re as _re
            tg = ThumbnailGenerator()
            thumb_out = os.path.join("output", f"thumbnail_{ts}.jpg")
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
                topic=topic_key,
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

        # ── 6. Chapters & SEO ────────────────────────────────────
        # description içinde timestamp'ler writer.py tarafından ekleniyor

        # ── 7. YouTube Yükleme ────────────────────────────────────
        if self.uploader and self.uploader.youtube and os.path.exists(final_video_path):
            print("\n[7/7] YouTube'a yükleniyor (Long-form)...", flush=True)
            try:
                video_id = self.uploader.upload_video(
                    file_path=final_video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    playlist_name="EV Data Reports",
                    thumbnail_path=None   # aşağıda ayrıca yüklüyoruz
                )
                log(f"      ✅ Yüklendi! Video ID: {video_id}")
                log(f"      🔗 https://www.youtube.com/watch?v={video_id}")
                # ── Thumbnail YouTube'a yükle ────────────────────────
                self._upload_thumbnail(video_id, title, topic_key,
                                       thumb_path=thumbnail_path, is_short=False)
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
    orchestrator = EvcarixOrchestrator()
    
    video_type = os.environ.get("VIDEO_TYPE", "short").strip().lower()
    upload_slot = os.environ.get("UPLOAD_SLOT", "evening").strip()

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
