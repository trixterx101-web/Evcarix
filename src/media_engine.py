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

    async def download_stock_videos(self, topic: str, target_clip_count: int = 6, plan=None, **kwargs) -> list:
        logger.info(f"[MediaEngine] '{topic}' için hibrit (Gerçek + Animasyon) medya stratejisi uygulanıyor...")
        
        real_clips = []
        anim_clips = []
        
        # 1. Arama Terimleri
        queries = self._generate_search_queries(topic)
        
        # 2. Gerçek Videoları Topla (Hedefin yarısı kadar)
        target_real = (target_clip_count + 1) // 2
        for query in queries:
            if len(real_clips) >= target_real: break
            if self.pexels_api_key:
                real_clips.extend(self._download_pexels_videos(query, target_real - len(real_clips)))
            if len(real_clips) < target_real and self.pixabay_api_key:
                real_clips.extend(self._download_pixabay_videos(query, target_real - len(real_clips)))
        
        # 3. Animasyonları Üret (Hedefin kalanı kadar)
        target_anim = target_clip_count - len(real_clips)
        from src.ai_video_generator import AIVideoGenerator
        ai_gen = AIVideoGenerator()
        
        # Animasyon konuları için script'ten veya topic'ten ilham al
        anim_prompts = [
            f"{topic} battery charging technology",
            f"{topic} energy flow pulse",
            f"{topic} data analysis statistics",
            f"{topic} futuristic electric grid"
        ]
        
        for i in range(target_anim):
            prompt = anim_prompts[i % len(anim_prompts)]
            path = ai_gen._ffmpeg_animated(prompt, i)
            if path: anim_clips.append(path)

        # 4. Harmanla (Interleave)
        # Sahne 1: Gerçek, Sahne 2: Animasyon, Sahne 3: Gerçek...
        final_clips = []
        for i in range(target_clip_count):
            if i % 2 == 0 and real_clips:
                final_clips.append(real_clips.pop(0))
            elif anim_clips:
                final_clips.append(anim_clips.pop(0))
            elif real_clips: # Fallback if anims failed
                final_clips.append(real_clips.pop(0))
        
        # Eğer hala eksik varsa fallback
        if len(final_clips) < target_clip_count:
            needed = target_clip_count - len(final_clips)
            for i in range(needed):
                final_clips.append(ai_gen._ffmpeg_animated(f"{topic} fallback", 100+i))

        self._save_used_hashes()
        return final_clips

    def _generate_search_queries(self, topic: str) -> list:
        """Konuyu görsel terimlere dönüştürür."""
        # Basit ama etkili fallback terimleri (Elektrikli araç odaklı)
        base = [topic, f"electric car {topic}", "EV technology", "futuristic transportation"]
        # Eğer konu batarya ile ilgiliyse özel terimler ekle
        if "battery" in topic.lower():
            base = ["EV battery factory", "electric car charging", "lithium battery tech", "battery cell"]
        elif "cost" in topic.lower() or "price" in topic.lower():
            base = ["car payment", "saving money car", "electric vehicle charging station", "EV luxury interior"]
        
        return list(set(base))[:4]

    def _download_pexels_videos(self, query: str, count: int) -> list:
        headers = {"Authorization": self.pexels_api_key}
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation=portrait"
        clips = []
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                for v in r.json().get("videos", []):
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
        url = f"https://pixabay.com/api/videos/?key={self.pixabay_api_key}&q={query}&per_page=5&orientation=vertical"
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
