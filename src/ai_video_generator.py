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
        # Ücretsiz / Cömert Kaynaklar
        self.seedance_key = os.getenv("SEEDANCE_API_KEY") # 100 kredi/gün
        self.zsky_key = os.getenv("ZSKY_API_KEY")         # Günlük limit
        
        # Kredili / Ücretli Kaynaklar
        self.fal_key = os.getenv("FAL_KEY")
        self.replicate_key = os.getenv("REPLICATE_API_TOKEN") # $5 free credit
        self.kling_key = os.getenv("KLING_API_KEY")
        self.luma_key = os.getenv("LUMA_API_KEY")
        self.runway_key = os.getenv("RUNWAY_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")

    def generate_clips(self, prompts: list[str]) -> list[str]:
        """Prompts listesinden AI video klipleri üretir (Ücretsiz Kaynak Öncelikli)."""
        clips = []
        for i, prompt in enumerate(prompts):
            path = None
            logger.info(f"[AIVideo] Sahne {i+1} üretiliyor: {prompt[:50]}...")

            # ── STRATEJİ: Önce tamamen ücretsiz/cömert olanlar ──
            
            # 1. Seedance (100 kredi/gün - Çok cömert)
            if self.seedance_key:
                path = self._seedance(prompt, i)
            
            # 2. ZSky AI
            if not path and self.zsky_key:
                path = self._zsky(prompt, i)

            # 3. Fal.ai (Hızlı ve kaliteli)
            if not path and self.fal_key:
                path = self._fal_ai(prompt, i)
            
            # 4. Replicate (WAN 2.7 / Kling - $5 Bedava kredi)
            if not path and self.replicate_key:
                path = self._replicate(prompt, i)

            # 5. Kling / Luma / Runway (Günlük limitli)
            if not path and self.kling_key:
                path = self._kling(prompt, i)
            
            if not path and self.luma_key:
                path = self._luma(prompt, i)

            # 6. HuggingFace (Sınırsız ama düşük kalite)
            if not path and self.hf_token:
                path = self._huggingface(prompt, i)

            # 7. Fallback (Garantili)
            if not path:
                logger.warning(f"[AIVideo] Hiçbir API sonuç vermedi, FFmpeg fallback (Sahne {i+1})")
                path = self._ffmpeg_animated(prompt, i)

            if path:
                clips.append(path)
                logger.info(f"[AIVideo] ✅ Sahne {i+1}/6 hazır: {os.path.basename(path)}")

        return clips

    # ── Seedance AI (100 Kredi/Gün!) ────────────────────────────────────────
    def _seedance(self, prompt: str, idx: int) -> str | None:
        try:
            # Not: API dökümanına göre endpoint değişebilir, genel pattern:
            r = requests.post("https://api.seedance.tv/v1/video/generate", headers={
                "Authorization": f"Bearer {self.seedance_key}", "Content-Type": "application/json"
            }, json={"prompt": prompt, "model": "veo3", "aspect_ratio": "9:16", "duration": 5}, timeout=30)
            if r.status_code != 200: return None
            tid = r.json().get("task_id")
            for _ in range(40): # 3-4 dk bekle
                tr = requests.get(f"https://api.seedance.tv/v1/video/status/{tid}", headers={"Authorization": f"Bearer {self.seedance_key}"}, timeout=15)
                data = tr.json()
                if data.get("status") == "completed":
                    return self._download(data["video_url"], f"seedance_{idx}.mp4")
                elif data.get("status") == "failed": break
                time.sleep(10)
        except Exception as e: logger.debug(f"[Seedance] {e}")
        return None

    # ── ZSky AI ─────────────────────────────────────────────────────────────
    def _zsky(self, prompt: str, idx: int) -> str | None:
        try:
            r = requests.post("https://api.zsky.ai/v1/video/text-to-video", headers={
                "Authorization": f"Bearer {self.zsky_key}", "Content-Type": "application/json"
            }, json={"prompt": prompt, "quality": "hd", "duration": 5}, timeout=30)
            if r.status_code == 200:
                tid = r.json().get("task_id")
                for _ in range(30):
                    tr = requests.get(f"https://api.zsky.ai/v1/video/status/{tid}", headers={"Authorization": f"Bearer {self.zsky_key}"}, timeout=15)
                    if tr.json().get("status") == "succeeded":
                        return self._download(tr.json()["video_url"], f"zsky_{idx}.mp4")
                    time.sleep(10)
        except Exception as e: logger.debug(f"[ZSky] {e}")
        return None

    # ── Replicate ($5 Bedava Kredi) ─────────────────────────────────────────
    def _replicate(self, prompt: str, idx: int) -> str | None:
        try:
            import replicate
            # WAN 2.1 modelini kullanıyoruz (Hızlı ve kaliteli)
            output = replicate.run(
                "wan-video/wan-2.1-14b-t2v-turbo",
                input={"prompt": prompt, "aspect_ratio": "9:16"}
            )
            if output:
                # Output genellikle bir URL veya URL listesidir
                url = output[0] if isinstance(output, list) else output
                return self._download(url, f"replicate_{idx}.mp4")
        except Exception as e: logger.debug(f"[Replicate] {e}")
        return None

    # ── Fal.ai (Standard Kling 1.6) ─────────────────────────────────────────
    def _fal_ai(self, prompt: str, idx: int) -> str | None:
        try:
            import fal_client
            handler = fal_client.submit(
                "fal-ai/kling-video/v1.6/standard/text-to-video",
                arguments={"prompt": prompt, "duration": "5", "aspect_ratio": "9:16"}
            )
            for _ in range(30):
                status = fal_client.status("fal-ai/kling-video/v1.6/standard/text-to-video", handler.request_id, with_logs=False)
                if status.status == "COMPLETED":
                    return self._download(status.response["video"]["url"], f"fal_{idx}.mp4")
                elif status.status == "FAILED": break
                time.sleep(5)
        except Exception as e: logger.debug(f"[FalAI] {e}")
        return None

    # ── Kling AI ────────────────────────────────────────────────────────────
    def _kling(self, prompt: str, idx: int) -> str | None:
        try:
            import jwt as pyjwt
            ak, sk = self.kling_key.split(":")
            token = pyjwt.encode({"iss": ak, "exp": int(time.time()) + 1800, "nbf": int(time.time()) - 5}, sk, algorithm="HS256")
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            r = requests.post("https://api.klingai.com/v1/videos/text2video", headers=headers, json={
                "model_name": "kling-v1", "prompt": prompt, "duration": "5", "aspect_ratio": "9:16"
            }, timeout=30)
            if r.status_code != 200: return None
            tid = r.json()["data"]["task_id"]
            for _ in range(30):
                tr = requests.get(f"https://api.klingai.com/v1/videos/text2video/{tid}", headers=headers, timeout=15)
                data = tr.json().get("data", {})
                if data.get("task_status") == "succeed":
                    return self._download(data["task_result"]["videos"][0]["url"], f"kling_{idx}.mp4")
                time.sleep(5)
        except: pass
        return None

    # ── Luma / Runway / HF (Önceki versiyondan devam) ──────────────────────
    def _luma(self, prompt: str, idx: int) -> str | None:
        try:
            r = requests.post("https://api.lumalabs.ai/dream-machine/v1/generations", headers={
                "Authorization": f"Bearer {self.luma_key}"}, json={"prompt": prompt, "aspect_ratio": "9:16"}, timeout=20)
            if r.status_code in [200, 201]:
                gid = r.json().get("id")
                for _ in range(30):
                    tr = requests.get(f"https://api.lumalabs.ai/dream-machine/v1/generations/{gid}", headers={"Authorization": f"Bearer {self.luma_key}"}, timeout=15)
                    if tr.json().get("state") == "completed": return self._download(tr.json()["assets"]["video"], f"luma_{idx}.mp4")
                    time.sleep(5)
        except: pass
        return None

    def _huggingface(self, prompt: str, idx: int) -> str | None:
        try:
            r = requests.post("https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b",
                              headers={"Authorization": f"Bearer {self.hf_token}"}, json={"inputs": prompt}, timeout=120)
            if r.status_code == 200:
                path = os.path.join(OUTPUT_DIR, f"hf_{idx}.mp4")
                with open(path, "wb") as f: f.write(r.content)
                return path
        except: pass
        return None

    def _ffmpeg_animated(self, prompt: str, idx: int) -> str:
        out = os.path.join(OUTPUT_DIR, f"fallback_{idx}.mp4")
        color = "0x001833" if "blue" in prompt.lower() else "0x0A0A1E"
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:size=1080x1920:rate=30", "-t", "5", 
               "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast", "-an", out]
        subprocess.run(cmd, capture_output=True)
        return out

    def _download(self, url: str, name: str) -> str | None:
        path = os.path.join(OUTPUT_DIR, name)
        try:
            r = requests.get(url, stream=True, timeout=60)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    for chunk in r.iter_content(65536): f.write(chunk)
                return path
        except: pass
        return None
