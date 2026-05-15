import os
import random
import logging
import hashlib
import requests
import json
from pathlib import Path

logger = logging.getLogger("MediaEngine")

class MediaEngine:
    def __init__(self):
        # MediaEngine initialize edildiğinde ses motorunu da yükler
        from src.voice_engine import VoiceEngine
        self.voice_engine = VoiceEngine()
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.used_hashes_path = "used_hashes.json"
        self.used_hashes = self._load_used_hashes()

    def _load_used_hashes(self):
        if os.path.exists(self.used_hashes_path):
            try:
                with open(self.used_hashes_path, "r") as f:
                    return set(json.load(f))
            except: pass
        return set()

    def _save_used_hashes(self):
        with open(self.used_hashes_path, "w") as f:
            json.dump(list(self.used_hashes), f)

    # Parametre isimlerini main.py ile %100 uyumlu hale getirdik (topic, target_clip_count, plan)
    async def download_stock_videos(self, topic: str, target_clip_count: int = 6, plan=None, **kwargs) -> list:
        """
        Main.py ile tam uyumlu metod imzası. 
        Pexels -> Pixabay -> AI Video -> FFmpeg Animation hiyerarşisini çalıştırır.
        """
        logger.info(f"[MediaEngine] '{topic}' için {target_clip_count} klip hazırlanıyor...")
        final_clips = []
        
        # 1. Pexels Denemesi
        if self.pexels_api_key:
            logger.info("[MediaEngine] Pexels stok videoları aranıyor...")
            final_clips = self._download_pexels_videos(topic, target_clip_count)
            
        # 2. Pixabay Denemesi
        if len(final_clips) < target_clip_count and self.pixabay_api_key:
            needed = target_clip_count - len(final_clips)
            logger.info(f"[MediaEngine] Pixabay deneniyor (Eksik: {needed})...")
            final_clips.extend(self._download_pixabay_videos(topic, needed))

        # 3. AI Video Denemesi
        if len(final_clips) < target_clip_count:
            needed = target_clip_count - len(final_clips)
            logger.info(f"[MediaEngine] AI Video deneniyor (Eksik: {needed})...")
            from src.ai_video_generator import AIVideoGenerator
            from src.prompt_generator import generate_scene_prompts
            ai_gen = AIVideoGenerator()
            # Script bilgisi plan içinde olabilir, yoksa topic kullan
            script = plan.get("script", "") if plan and isinstance(plan, dict) else topic
            prompts = generate_scene_prompts(topic, script, needed)
            final_clips.extend(ai_gen.generate_clips(prompts))

        # 4. Son Çare: FFmpeg Animasyon
        if len(final_clips) < target_clip_count:
            needed = target_clip_count - len(final_clips)
            logger.warning(f"[MediaEngine] 🎨 Animasyon Fallback üretiliyor (Eksik: {needed}).")
            from src.ai_video_generator import AIVideoGenerator
            ai_gen = AIVideoGenerator()
            for i in range(len(final_clips), target_clip_count):
                final_clips.append(ai_gen._ffmpeg_animated(topic, i))

        self._save_used_hashes()
        return final_clips

    def _download_pexels_videos(self, query: str, count: int) -> list:
        headers = {"Authorization": self.pexels_api_key}
        url = f"https://api.pexels.com/videos/search?query={query}&per_page={count*3}&orientation=portrait"
        clips = []
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                videos = r.json().get("videos", [])
                for v in videos:
                    if len(clips) >= count: break
                    v_url = v["video_files"][0]["link"]
                    v_hash = hashlib.md5(v_url.encode()).hexdigest()
                    if v_hash in self.used_hashes: continue
                    path = self._download(v_url, f"pexels_{v_hash[:8]}.mp4")
                    if path:
                        clips.append(path)
                        self.used_hashes.add(v_hash)
        except: pass
        return clips

    def _download_pixabay_videos(self, query: str, count: int) -> list:
        url = f"https://pixabay.com/api/videos/?key={self.pixabay_api_key}&q={query}&per_page={count*3}&orientation=vertical"
        clips = []
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                for v in r.json().get("hits", []):
                    if len(clips) >= count: break
                    v_url = v["videos"].get("medium", {}).get("url") or v["videos"].get("small", {}).get("url")
                    if not v_url: continue
                    v_hash = hashlib.md5(v_url.encode()).hexdigest()
                    if v_hash in self.used_hashes: continue
                    path = self._download(v_url, f"pixabay_{v_hash[:8]}.mp4")
                    if path:
                        clips.append(path)
                        self.used_hashes.add(v_hash)
        except: pass
        return clips

    def _download(self, url, name):
        out_dir = "assets/footage"
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, name)
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                with open(path, "wb") as f: f.write(r.content)
                return path
        except: pass
        return None
