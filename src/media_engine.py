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

    def prepare_media(self, topic: str, script: str, count: int = 6) -> list:
        """
        Gerçek stok videoları (Pexels/Pixabay) indirir. 
        Bulamazsa AI Video üretimine (veya fallback'e) devredilir.
        """
        logger.info(f"[MediaEngine] '{topic}' için medya hazırlanıyor...")
        final_clips = []
        
        # 1. Pexels Denemesi
        if self.pexels_api_key:
            logger.info("[MediaEngine] Pexels stok videoları aranıyor...")
            final_clips = self._download_pexels_videos(topic, count)
            
        # 2. Pixabay Denemesi (Pexels yetersizse)
        if len(final_clips) < count and self.pixabay_api_key:
            logger.info("[MediaEngine] Pixabay stok videoları aranıyor...")
            needed = count - len(final_clips)
            pix_clips = self._download_pixabay_videos(topic, needed)
            final_clips.extend(pix_clips)

        # 3. AI Video Fallback (Hala eksik varsa)
        if len(final_clips) < count:
            logger.warning(f"[MediaEngine] {count - len(final_clips)} klip eksik, AI Video Generator devreye giriyor.")
            from src.ai_video_generator import AIVideoGenerator
            ai_gen = AIVideoGenerator()
            # Kalan miktar kadar prompt üret ve AI ile tamamla
            needed = count - len(final_clips)
            from src.prompt_generator import generate_scene_prompts
            prompts = generate_scene_prompts(topic, script, needed)
            ai_clips = ai_gen.generate_clips(prompts)
            final_clips.extend(ai_clips)

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
        except Exception as e: logger.error(f"[Pexels] Hata: {e}")
        return clips

    def _download_pixabay_videos(self, query: str, count: int) -> list:
        url = f"https://pixabay.com/api/videos/?key={self.pixabay_api_key}&q={query}&per_page={count*3}&orientation=vertical"
        clips = []
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                videos = r.json().get("hits", [])
                for v in videos:
                    if len(clips) >= count: break
                    # Pixabay'de 'large' veya 'medium' seç
                    v_url = v["videos"].get("medium", {}).get("url") or v["videos"].get("small", {}).get("url")
                    if not v_url: continue
                    v_hash = hashlib.md5(v_url.encode()).hexdigest()
                    if v_hash in self.used_hashes: continue
                    
                    path = self._download(v_url, f"pixabay_{v_hash[:8]}.mp4")
                    if path:
                        clips.append(path)
                        self.used_hashes.add(v_hash)
        except Exception as e: logger.error(f"[Pixabay] Hata: {e}")
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
