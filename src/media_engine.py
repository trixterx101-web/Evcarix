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
        """v8.0 Pipeline: Pexels -> Pixabay -> AI -> Cache"""
        from src.pixabay_engine import search_pixabay_videos
        from src.ai_video_engine import generate_video_prompt
        
        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        needed = target_clip_count
        all_clips = []
        
        query_pool = [f"{topic_text} car", "EV driving", "car dashboard", "highway driving", "Tesla winter"]
        random.shuffle(query_pool)

        # Stage 1: Pexels
        logger.info("[MediaEngine] Stage 1: Pexels...")
        for q in query_pool[:2]:
            if len(all_clips) >= needed: break
            new = self._download_from_pexels(q, OUTPUT_DIR, needed - len(all_clips))
            all_clips.extend(new)

        # Stage 2: Pixabay
        if len(all_clips) < needed:
            logger.info("[MediaEngine] Stage 2: Pixabay...")
            for q in query_pool[:2]:
                if len(all_clips) >= needed: break
                new = search_pixabay_videos(q, max_results=needed - len(all_clips))
                all_clips.extend(new)

        # Stage 3: AI Fallback
        if len(all_clips) < needed:
            logger.info("[MediaEngine] Stage 3: AI Fallback...")
            prompt = generate_video_prompt(topic_text)
            logger.info(f"[AIVideo] Fallback prompt generated: {prompt[:50]}...")

        # Stage 4: Cache
        if len(all_clips) < needed:
            logger.info("[MediaEngine] Stage 4: Cache...")
            cached = [str(f) for f in Path(CACHE_DIR).glob("*.mp4")]
            if cached:
                random.shuffle(cached)
                all_clips.extend(cached[:needed - len(all_clips)])

        # Final Processing & Hashing
        unique = []
        hashes = set()
        for c in all_clips:
            if not os.path.exists(c): continue
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

    def _download_from_pexels(self, query, output_dir, count):
        if not self.pexels_api_key: return []
        paths = []
        try:
            url = f"https://api.pexels.com/videos/search?query={query}&per_page={count}&orientation=portrait"
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
