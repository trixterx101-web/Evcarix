import asyncio
import os
import random
import datetime
from dotenv import load_dotenv

from src.brain import EvcarixBrain
from src.media_engine import MediaEngine
from src.editor import AutoEditor
from src.uploader import YouTubeUploader
from src.lip_sync_generator import LipSyncGenerator

load_dotenv()


class EvcarixOrchestrator:
    def __init__(self):
        self.brain = EvcarixBrain()
        self.media_engine = MediaEngine()
        self.editor = AutoEditor()
        self.lip_sync = LipSyncGenerator()
        self.uploader = None

        self.use_lip_sync = os.getenv("USE_LIP_SYNC", "false").lower() == "true"
        self.character_image = os.getenv("CHARACTER_IMAGE", "assets/character.jpg")
        
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
        # CONTENT_MODE: trend (YouTube'tan ilham) veya auto (sistem konusu)
        content_mode = os.getenv("CONTENT_MODE", "auto")
        slot = os.getenv("UPLOAD_SLOT", "evening")
        
        plan = self.brain.create_daily_plan(slot=slot)
        script      = plan['script']
        topic       = plan['topic']
        full_topic  = plan['full_topic']
        title       = plan.get('title', topic)
        description = plan.get('description', f"{topic}\n\n#EV #Evcarix #Shorts")
        tags        = plan.get('tags', ["ev", "electric car", "Evcarix", "Shorts"])

        print(f"\n[1/6] Plan Hazır")
        if plan.get("inspired_by"):
            print(f"      🔥 MOD    : TREND (YouTube trend'inden ilham alındı)")
            print(f"      🔗 İlham  : {plan.get('inspired_by')}")
            print(f"      ⚠️  NOT   : Görüntü/ses kopyalanmadı — orijinal içerik")
        else:
            print(f"      📋 MOD   : NORMAL (havuz konusu)")
        print(f"      Konu  : {full_topic.encode('ascii', 'ignore').decode('ascii')}")
        print(f"      Başlık: {title.encode('ascii', 'ignore').decode('ascii')}")

        # ── Lip-Sync Mode Check ───────────────────────────────────────
        if self.use_lip_sync and os.path.exists(self.character_image):
            print(f"\n⚡ Lip-Sync Mode aktif - Karakter konuşan video oluşturuluyor...")
            print(f"      Karakter: {self.character_image}")
            
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
                    print("\n[6/6] YouTube'a yükleniyor...")
                    try:
                        video_id = self.uploader.upload_video(
                            final_video_path, title, description, tags
                        )
                        print(f"      ✅ Yüklendi! Video ID: {video_id}")
                        print(f"      🔗 https://www.youtube.com/watch?v={video_id}")
                    except Exception as e:
                        print(f"      ❌ YouTube yükleme hatası: {e}")
                
                print(f"\n{'='*60}")
                print(f"  ✅ TAMAMLANDI!")
                print(f"  Video    : {final_video_path}")
                print(f"  Başlık   : {title.encode('ascii', 'ignore').decode('ascii')}")
                print(f"{'='*60}\n")
                return
            else:
                print("⚠️ Lip-sync başarısız, normal moda geçiliyor...")

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

        # ── Kullanılan klipleri kaydet — bir daha seçilmesin ──────────
        if all_video_clips:
            self.media_engine.mark_clips_as_used(all_video_clips)
        print(f"[Main] 🔄 Klip geçmişi güncellendi — bir sonraki video farklı görüntüler kullanacak.")

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

    async def run_weekly_long_video_workflow(self):
        """Haftalık uzun formatlı video (1920x1080, 4-6 dakika) pipeline."""
        import math
        import random
        
        # ── Zaman damgası & slot bilgisi ──────────────────────────
        now = datetime.datetime.now()
        slot = "SUNDAY_LONG"
        ts = now.strftime("%Y%m%d_%H%M%S")
        
        # Hedef süre: 240-360 saniye (4-6 dakika)
        target_duration = random.randint(240, 360)
        clip_count = math.ceil(target_duration / 8)  # Her klip ~8 saniye
        
        print(f"\n{'='*60}")
        print(f"  Evcarix Weekly Long Video — {now.strftime('%d %b %Y, %H:%M')}")
        print(f"  Format: 1920x1080 (16:9), {target_duration}s ({target_duration//60}dk)")
        print(f"  Slot: {slot}")
        print(f"{'='*60}\n")

        # ── 1. Plan (long-form script) ───────────────────────────
        print("\n[1/7] Long-form plan oluşturuluyor...")
        content_mode = os.getenv("CONTENT_MODE", "auto")
        
        plan = self.brain.create_daily_plan(slot=slot)
        script = plan['script']
        topic = plan['topic']
        full_topic = plan['full_topic']
        title = plan.get('title', topic)
        description = plan.get('description', f"{topic}\n\n#EV #Evcarix #LongForm")
        tags = plan.get('tags', ["ev", "electric car", "Evcarix", "long form", "deep dive"])

        print(f"      Konu  : {full_topic.encode('ascii', 'ignore').decode('ascii')}")
        print(f"      Başlık: {title.encode('ascii', 'ignore').decode('ascii')}")
        print(f"      Süre  : {target_duration}s")

        # ── 2. AI Video Klip Üretimi (daha fazla klip) ───────────
        print(f"\n[2/7] AI video klip üretimi ({clip_count} klip, 6-10s)...")
        ai_video_clips = self.media_engine.generate_ai_video_clips(
            topic=topic,
            count=clip_count,
            output_dir=f"assets/ai_videos/{ts}",
            duration=8
        )

        # ── 3. Stok videolar (AI yetersizse) ─────────────────────
        video_paths = []
        if len(ai_video_clips) < clip_count:
            print(f"\n[3/7] AI videolar yetersiz, stok videolar indiriliyor...")
            import re
            search_query = re.sub(r'[^\w\s]', '', topic).strip()
            video_paths = self.media_engine.download_stock_videos(
                query=search_query,
                output_dir=f"assets/temp_videos/{ts}",
                count=clip_count,
                orientation="landscape",
                category=plan.get("category", "general")
            )
        
        # Combine AI clips and stock videos
        all_video_clips = ai_video_clips + video_paths
        random.shuffle(all_video_clips)
        
        # ── 4. Seslendirme (long-form) ───────────────────────────
        print("\n[4/7] Long-form seslendirme yapılıyor...")
        audio_path = os.path.abspath(f"assets/voice_{ts}.mp3")
        voice_result = await self.media_engine.generate_voiceover(
            text=script,
            output_path=audio_path,
            voice_type='male',  # Long form için erkek ses
            rate="+0%"
        )
        word_timings = voice_result['word_timings']

        # ── 5. Video montajı (long-form, 1920x1080) ───────────────
        print("\n[5/7] Long-form video montajlanıyor (1920x1080)...")
        output_filename = f"weekly_long_{ts}.mp4"
        final_video_path = self.editor.assemble_weekly_long_video(
            video_clips=all_video_clips,
            audio_path=audio_path,
            title=title,
            target_duration=target_duration,
            output_path=output_filename
        )

        # ── Kullanılan klipleri kaydet ───────────────────────────
        if all_video_clips:
            self.media_engine.mark_clips_as_used(all_video_clips)
        print(f"[Main] 🔄 Klip geçmişi güncellendi.")

        # ── 5.5 Thumbnail oluştur ───────────────────────────────
        print("\n[5.5/7] Thumbnail oluşturuluyor...")
        from src.thumbnail_generator import ThumbnailGenerator
        thumb_gen = ThumbnailGenerator()
        thumb_path = thumb_gen.create(
            title=title,
            stat=plan.get("stat", ""),
            category=plan.get("category_id", "default")
        )

        # ── 6. YouTube'a yükle (Weekly Deep Dives playlist) ───────
        if self.uploader and os.path.exists(final_video_path):
            print("\n[6/7] YouTube'a yükleniyor (Weekly Deep Dives)...")
            
            pre_upload_delay = random.randint(5, 25)
            print(f"      Yükleme öncesi {pre_upload_delay}sn bekleniyor...")
            await asyncio.sleep(pre_upload_delay)

            try:
                video_id = self.uploader.upload_video(
                    final_video_path, title, description, tags,
                    playlist="Weekly Deep Dives",
                    category_id=28,  # Science & Technology
                    made_for_kids=False,
                    thumbnail_path=thumb_path
                )
                print(f"      ✅ Yüklendi! Video ID: {video_id}")
                print(f"      🔗 https://www.youtube.com/watch?v={video_id}")
            except Exception as e:
                print(f"      ❌ YouTube yükleme hatası: {e}")
                raise e
        else:
            print("\n[6/7] YouTube yükleme atlandı.")

        print(f"\n{'='*60}")
        print(f"  ✅ HAFTALIK UZUN VIDEO TAMAMLANDI!")
        print(f"  Video    : {final_video_path}")
        print(f"  Başlık   : {title.encode('ascii', 'ignore').decode('ascii')}")
        print(f"  Süre     : {target_duration}s")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    orchestrator = EvcarixOrchestrator()
    upload_slot = os.getenv("UPLOAD_SLOT", "evening")
    
    # Routing: Haftalık uzun video mu, günlük Short mu?
    if upload_slot == "SUNDAY_LONG":
        asyncio.run(orchestrator.run_weekly_long_video_workflow())
    else:
        asyncio.run(orchestrator.run_daily_shorts_workflow())