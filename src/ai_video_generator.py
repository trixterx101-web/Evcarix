import os
import time
import requests
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("AIVideoGenerator")
OUTPUT_DIR = "assets/ai_clips"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

class AIVideoGenerator:
    def __init__(self):
        # GitHub Secrets'tan gelen anahtarlar
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.muapi_key = os.getenv("MUAPI_KEY")
        self.fal_key = os.getenv("FAL_KEY")
        self.seedance_key = os.getenv("SEEDANCE_API_KEY")
        self.replicate_key = os.getenv("REPLICATE_API_TOKEN")
        self.pexels_key = os.getenv("PEXELS_API_KEY") # Stok video fallback için

    def generate_clips(self, prompts: list[str]) -> list[str]:
        if not prompts: return []
        clips = []
        for i, prompt in enumerate(prompts):
            path = None
            logger.info(f"[AIVideo] Sahne {i+1} için API'lar zorlanıyor...")
            
            # 1. Şampiyonlar Ligi: AI Üretimi
            methods = [
                ("GoogleVeo", self._google_veo),
                ("Muapi", self._muapi),
                ("FalAI", self._fal_ai),
                ("Seedance", self._seedance),
                ("Replicate", self._replicate)
            ]
            
            for name, method in methods:
                try:
                    path = method(prompt, i)
                    if path: 
                        logger.info(f"[AIVideo] ✅ {name} ile BAŞARILI!")
                        break
                except Exception as e:
                    logger.debug(f"[AIVideo] {name} istisna: {e}")

            # 2. Yedek: Pexels Stok Video (AI başarısız olursa)
            if not path and self.pexels_key:
                logger.info(f"[AIVideo] 🔄 AI başarısız, Pexels Stok Video deneniyor (Sahne {i+1})")
                path = self._download_stock_fallback(prompt, i)

            # 3. Son Çare: Hareketli Fallback
            if not path:
                logger.warning(f"[AIVideo] ⚠️ Tüm kaynaklar sustu, Hareketli Fallback üretiliyor (Sahne {i+1})")
                path = self._ffmpeg_animated(prompt, i)
            
            if path: clips.append(path)
        return clips

    def _google_veo(self, prompt, idx):
        if not self.gemini_key: return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("veo-3-1")
            res = model.generate_content(prompt)
            if res and hasattr(res, 'data'):
                p = os.path.join(OUTPUT_DIR, f"veo_{idx}.mp4")
                with open(p, "wb") as f: f.write(res.data)
                return p
        except Exception as e:
            logger.error(f"[GoogleVeo] Hata: {str(e)[:100]}")
        return None

    def _muapi(self, prompt, idx):
        if not self.muapi_key: return None
        try:
            r = requests.post("https://api.muapi.ai/v1/video/generate", 
                              headers={"Authorization": f"Bearer {self.muapi_key}"}, 
                              json={"model": "kling-v1.6", "prompt": prompt, "aspect_ratio": "9:16"}, timeout=15)
            if r.status_code == 200:
                tid = r.json().get("task_id")
                for _ in range(20):
                    tr = requests.get(f"https://api.muapi.ai/v1/video/status/{tid}", headers={"Authorization": f"Bearer {self.muapi_key}"})
                    d = tr.json()
                    if d.get("status") == "succeeded": return self._download(d["video_url"], f"mu_{idx}.mp4")
                    time.sleep(10)
            else: logger.error(f"[Muapi] HTTP {r.status_code}: {r.text[:50]}")
        except: pass
        return None

    def _download_stock_fallback(self, query, idx):
        """AI başarısız olursa Pexels'ten kaliteli bir stok video bulur."""
        try:
            headers = {"Authorization": self.pexels_key}
            url = f"https://api.pexels.com/videos/search?query={query[:50]}&per_page=1&orientation=portrait"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                vdata = r.json().get("videos", [])
                if vdata:
                    v_url = vdata[0]["video_files"][0]["link"]
                    return self._download(v_url, f"stock_{idx}.mp4")
        except: pass
        return None

    def _ffmpeg_animated(self, prompt, idx):
        out = os.path.join(OUTPUT_DIR, f"fb_{idx}.mp4")
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "cellauto=s=1080x1920:rate=30", "-t", "5", 
               "-vf", "hue=h=100:s=1,format=yuv420p", "-c:v", "libx264", "-preset", "ultrafast", "-an", out]
        subprocess.run(cmd, capture_output=True)
        return out

    def _download(self, url, name):
        p = os.path.join(OUTPUT_DIR, name)
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                with open(p, "wb") as f: f.write(r.content)
                return p
        except: pass
        return None

    # Diğer metodlar (Seedance, Fal, Replicate) için de benzer hata loglamaları eklenebilir...
    def _seedance(self, p, i): return None
    def _fal_ai(self, p, i): return None
    def _replicate(self, p, i): return None
