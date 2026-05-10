import os
import json
import random
import re
import requests
import hashlib
import time
import logging
from pathlib import Path
from .voice_engine import VoiceEngine

logger = logging.getLogger("MediaEngine")

# v8.5 Configuration
OUTPUT_DIR = "assets/temp_videos"
CACHE_DIR = "assets/cache/videos"
USED_VIDEOS_FILE = "used_videos.json"
REPETITION_LIMIT = 300 # Son 300 klip hafızada tutulur

class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.voice_engine = VoiceEngine()
        
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        self.used_hashes = self._load_used_hashes()

    def _load_used_hashes(self):
        if os.path.exists(USED_VIDEOS_FILE):
            try:
                with open(USED_VIDEOS_FILE, "r") as f:
                    return set(json.load(f))
            except: return set()
        return set()

    def _save_used_hashes(self, new_hashes):
        history = list(self.used_hashes.union(new_hashes))
        if len(history) > REPETITION_LIMIT:
            history = history[-REPETITION_LIMIT:]
        with open(USED_VIDEOS_FILE, "w") as f:
            json.dump(history, f)

    def _get_file_hash(self, file_path):
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except: return str(time.time())

    async def download_stock_videos(self, plan=None, target_clip_count=6, topic=None):
        """v8.6 Pipeline: Zero-Repetition Acquisition"""
        from src.pixabay_engine import search_pixabay_videos
        from src.ai_video_engine import generate_video_prompt, generate_ai_video
        
        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        video_type = plan.get("video_type", "short") if plan else "short"
        needed = target_clip_count
        all_clips = []
        
        # Daha fazla çeşitlilik için genişletilmiş sorgu havuzu
        query_pool = [
            f"{topic_text} 4k", f"{topic_text} technology", "EV driving cinematic", 
            "future car interior", "electric motor technical", "charging station 4k",
            "highway driving sunset", "modern automotive design", "digital dashboard car"
        ]
        random.shuffle(query_pool)

        # Stage 1-3: Balanced Sources
        ff_target = max(2, needed // 3)
        px_target = max(2, needed // 3)
        
        # 1. Free Footage
        try:
            from src.free_footage import FreeFootageEngine
            ff_engine = FreeFootageEngine()
            ff_clips = ff_engine.get_clips(topic_text, count=ff_target * 2, video_type=video_type)
            all_clips.extend(ff_clips)
        except Exception as e: logger.error(f"[MediaEngine] FF hatası: {e}")

        # 2. Pexels
        for q in query_pool:
            if len(all_clips) >= (ff_target + px_target) * 2: break
            new = self._download_from_pexels(q, OUTPUT_DIR, px_target, video_type=video_type)
            all_clips.extend(new)

        # 3. Pixabay
        orientation = "horizontal" if video_type == "long" else "vertical"
        for q in query_pool:
            if len(all_clips) >= needed * 3: break
            new = search_pixabay_videos(q, max_results=px_target, orientation=orientation)
            all_clips.extend(new)

        # 4. AI Video (Her zaman 1 tane yeni üretmeye çalış)
        try:
            ai_prompt = generate_video_prompt(topic_text)
            ai_clip = await generate_ai_video(ai_prompt, video_type=video_type)
            if ai_clip: all_clips.append(ai_clip)
        except: pass

        # --- REPETITION FILTERING ---
        unique_and_fresh = []
        current_session_hashes = set()
        
        # Önce klipleri karıştır ki hep aynıları ilk gelmesin
        random.shuffle(all_clips)

        for c in all_clips:
            if not c or not os.path.exists(c): continue
            f_hash = self._get_file_hash(c)
            
            # Eğer bu klip son videolarda kullanıldıysa ATLA
            if f_hash in self.used_hashes:
                logger.info(f"[MediaEngine] ♻️ Tekrar eden klip atlandı: {os.path.basename(c)}")
                continue
            
            if f_hash not in current_session_hashes:
                current_session_hashes.add(f_hash)
                unique_and_fresh.append(c)
                if len(unique_and_fresh) >= needed: break

        # Eğer hala eksik varsa (çok nadir), cache'den HİÇ kullanılmamış olanları çek
        if len(unique_and_fresh) < needed:
            logger.info("[MediaEngine] ⚠️ Yetersiz yeni klip, temiz cache taranıyor...")
            cached_files = list(Path(CACHE_DIR).glob("*.mp4"))
            random.shuffle(cached_files)
            for f in cached_files:
                f_hash = self._get_file_hash(str(f))
                if f_hash not in self.used_hashes and f_hash not in current_session_hashes:
                    unique_and_fresh.append(str(f))
                    current_session_hashes.add(f_hash)
                    if len(unique_and_fresh) >= needed: break

        # Kullanılanları kaydet
        self._save_used_hashes(current_session_hashes)
        
        # Son bir karıştırma (akış için)
        random.shuffle(unique_and_fresh)
        return unique_and_fresh[:needed]

    def _download_from_pexels(self, query, dest_dir, count, video_type="short"):
        """v8.6: Optimized Pexels acquisition with native API orientation."""
        if not self.pexels_api_key: return []
        
        orientation = "landscape" if video_type == "long" else "portrait"
        url = f"https://api.pexels.com/videos/search?query={query}&per_page={count*2}&orientation={orientation}"
        headers = {"Authorization": self.pexels_api_key}
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200: return []
            
            data = r.json()
            paths = []
            for v in data.get("videos", []):
                # Birincil tercih HD kalite
                v_url = None
                for f in v.get("video_files", []):
                    if f.get("quality") == "hd":
                        v_url = f.get("link")
                        break
                if not v_url: v_url = v.get("video_files", [{}])[0].get("link")
                
                if v_url:
                    fname = f"pexels_{v.get('id')}.mp4"
                    fpath = os.path.join(dest_dir, fname)
                    if not os.path.exists(fpath):
                        # Chunked download for reliability
                        dl = requests.get(v_url, stream=True, timeout=60)
                        with open(fpath, "wb") as f:
                            for chunk in dl.iter_content(1024*1024): 
                                if chunk: f.write(chunk)
                    paths.append(fpath)
                
                if len(paths) >= count: break
            return paths
        except Exception as e:
            logger.error(f"[MediaEngine] Pexels hatası: {e}")
            return []
