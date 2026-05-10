import os
import random
import re
import requests
import hashlib
import time
import logging
from pathlib import Path
from .voice_engine import VoiceEngine

print("=== NEW MEDIA ENGINE LOADED ===", flush=True)
logger = logging.getLogger("MediaEngine")

# v8.0 Configuration
OUTPUT_DIR = "assets/temp_videos"
CACHE_DIR = "assets/cache/videos"

class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.voice_engine = VoiceEngine()
        
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, file_path):
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except: return str(time.time())

    async def download_stock_videos(self, plan=None, target_clip_count=6, topic=None):
        """v8.5 Pipeline: Balanced Acquisition (FF + Pexels + Pixabay + AI)"""
        from src.pixabay_engine import search_pixabay_videos
        from src.ai_video_engine import generate_video_prompt, generate_ai_video
        
        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        video_type = plan.get("video_type", "short") if plan else "short"
        needed = target_clip_count
        all_clips = []
        
        # Hedeflenen kaynak dağılımı (Çeşitlilik için)
        # 1/3 FreeFootage, 1/3 Pexels, 1/3 Pixabay + AI Fallback
        ff_target = max(1, needed // 3)
        px_target = max(1, needed // 3)
        pb_target = needed - (ff_target + px_target)
        
        query_pool = [f"{topic_text} car", "EV driving", "car dashboard", "highway driving", "future mobility"]
        random.shuffle(query_pool)

        # Stage 1: Free Footage (OEM, Archive...)
        try:
            from src.free_footage import FreeFootageEngine
            logger.info(f"[MediaEngine] Stage 1: Free Footage ({video_type}) - Target: {ff_target}")
            ff_engine = FreeFootageEngine()
            ff_clips = ff_engine.get_clips(topic_text, count=ff_target, video_type=video_type)
            all_clips.extend(ff_clips)
        except Exception as e:
            logger.error(f"[MediaEngine] Free Footage hatası: {e}")

        # Stage 2: Pexels
        needed_px = px_target + (ff_target - len(all_clips))
        if needed_px > 0:
            logger.info(f"[MediaEngine] Stage 2: Pexels ({video_type}) - Target: {needed_px}")
            for q in query_pool:
                if len(all_clips) >= (ff_target + px_target): break
                new = self._download_from_pexels(q, OUTPUT_DIR, needed_px, video_type=video_type)
                all_clips.extend(new)

        # Stage 3: Pixabay
        needed_pb = needed - len(all_clips)
        if needed_pb > 0:
            logger.info(f"[MediaEngine] Stage 3: Pixabay ({video_type}) - Target: {needed_pb}")
            orientation = "horizontal" if video_type == "long" else "vertical"
            for q in query_pool:
                if len(all_clips) >= needed: break
                new = search_pixabay_videos(q, max_results=needed_pb, orientation=orientation)
                all_clips.extend(new)

        # Stage 4: AI Video (Özellikle çeşitlilik için 1-2 tane her zaman ekle)
        if len(all_clips) < needed or random.random() > 0.5:
            logger.info("[MediaEngine] Stage 4: AI Video Generation...")
            try:
                ai_prompt = generate_video_prompt(topic_text)
                ai_clip = await generate_ai_video(ai_prompt, video_type=video_type)
                if ai_clip:
                    all_clips.append(ai_clip)
            except Exception as e:
                logger.error(f"[MediaEngine] AI Video hatası: {e}")

        # Stage 5: Cache Fallback (Hala eksik varsa)
        if len(all_clips) < needed:
            logger.info("[MediaEngine] Stage 5: Cache Fallback...")
            cached = [str(f) for f in Path(CACHE_DIR).glob("*.mp4")]
            if cached:
                random.shuffle(cached)
                all_clips.extend(cached[:needed - len(all_clips)])

        # Karıştır (Videonun başı hep aynı kaynaktan olmasın)
        random.shuffle(all_clips)
        
        # Final Processing & Hashing
        unique = []
        hashes = set()
        for c in all_clips:
            if not c or not os.path.exists(c): continue
            h = self._get_file_hash(c)
            if h not in hashes:
                hashes.add(h)
                unique.append(c)
                # Ensure in cache
                cache_dest = os.path.join(CACHE_DIR, os.path.basename(c))
                if not os.path.exists(cache_dest):
                    import shutil
                    try: shutil.copy(c, cache_dest)
                    except: pass
        
        return unique[:needed]

    def _download_from_pexels(self, query, output_dir, count, video_type="short"):
        if not self.pexels_api_key: return []
        paths = []
        orientation = "landscape" if video_type == "long" else "portrait"
        try:
            url = f"https://api.pexels.com/videos/search?query={query}&per_page={count}&orientation={orientation}"
            r = requests.get(url, headers={"Authorization": self.pexels_api_key}, timeout=15)
            vids = r.json().get("videos", [])
            for v in vids:
                link = v.get("video_files", [{}])[0].get("link")
                if link:
                    out = os.path.join(output_dir, f"pexels_{v['id']}.mp4")
                    if not os.path.exists(out):
                        dl = requests.get(link, stream=True, timeout=60)
                        with open(out, "wb") as f:
                            for chunk in dl.iter_content(1024*1024): f.write(chunk)
                    paths.append(out)
        except: pass
        return paths
