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
        self.fal_key = os.getenv("FAL_KEY")
        self.kling_key = os.getenv("KLING_API_KEY")
        self.luma_key = os.getenv("LUMA_API_KEY")
        self.runway_key = os.getenv("RUNWAY_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")

    def generate_clips(self, prompts: list[str]) -> list[str]:
        """Prompts listesinden AI video klipleri üretir."""
        clips = []
        for i, prompt in enumerate(prompts):
            path = None
            logger.info(f"[AIVideo] Sahne {i+1} üretiliyor: {prompt[:50]}...")

            # Öncelik Sırası: Fal -> Kling -> Luma -> Runway -> HF -> FFmpeg
            if self.fal_key:
                path = self._fal_ai(prompt, i)
            
            if not path and self.kling_key:
                path = self._kling(prompt, i)
            
            if not path and self.luma_key:
                path = self._luma(prompt, i)
                
            if not path and self.runway_key:
                path = self._runway(prompt, i)

            if not path and self.hf_token:
                path = self._huggingface(prompt, i)

            if not path:
                logger.warning(f"[AIVideo] Tüm API'lar başarısız, FFmpeg fallback kullanılıyor (Sahne {i+1})")
                path = self._ffmpeg_animated(prompt, i)

            if path:
                clips.append(path)
                logger.info(f"[AIVideo] ✅ Sahne {i+1}/6 hazır: {os.path.basename(path)}")

        return clips

    # ── Fal.ai (Hızlı ve Kaliteli) ──────────────────────────────────────────
    def _fal_ai(self, prompt: str, idx: int) -> str | None:
        try:
            import fal_client
            handler = fal_client.submit(
                "fal-ai/kling-video/v1.6/standard/text-to-video",
                arguments={"prompt": prompt, "duration": "5", "aspect_ratio": "9:16"}
            )
            for _ in range(30): # 2.5 dk limit
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
                elif data.get("task_status") == "failed": break
                time.sleep(5)
        except Exception as e: logger.debug(f"[Kling] {e}")
        return None

    # ── Luma Dream Machine ──────────────────────────────────────────────────
    def _luma(self, prompt: str, idx: int) -> str | None:
        try:
            r = requests.post("https://api.lumalabs.ai/dream-machine/v1/generations", headers={
                "Authorization": f"Bearer {self.luma_key}", "Content-Type": "application/json"
            }, json={"prompt": prompt, "aspect_ratio": "9:16"}, timeout=30)
            if r.status_code not in [200, 201]: return None
            gid = r.json().get("id")
            for _ in range(30):
                tr = requests.get(f"https://api.lumalabs.ai/dream-machine/v1/generations/{gid}", 
                                  headers={"Authorization": f"Bearer {self.luma_key}"}, timeout=15)
                data = tr.json()
                if data.get("state") == "completed":
                    return self._download(data["assets"]["video"], f"luma_{idx}.mp4")
                elif data.get("state") == "failed": break
                time.sleep(5)
        except Exception as e: logger.debug(f"[Luma] {e}")
        return None

    # ── Runway ML ───────────────────────────────────────────────────────────
    def _runway(self, prompt: str, idx: int) -> str | None:
        try:
            r = requests.post("https://api.dev.runwayml.com/v1/image_to_video", headers={
                "Authorization": f"Bearer {self.runway_key}", "Content-Type": "application/json", "X-Runway-Version": "2024-11-06"
            }, json={"promptText": prompt, "model": "gen3a_turbo", "duration": 5, "ratio": "768:1280"}, timeout=30)
            if r.status_code not in [200, 201]: return None
            tid = r.json().get("id")
            for _ in range(30):
                tr = requests.get(f"https://api.dev.runwayml.com/v1/tasks/{tid}", 
                                  headers={"Authorization": f"Bearer {self.runway_key}"}, timeout=15)
                data = tr.json()
                if data.get("status") == "SUCCEEDED":
                    return self._download(data["output"][0], f"runway_{idx}.mp4")
                elif data.get("status") == "FAILED": break
                time.sleep(5)
        except Exception as e: logger.debug(f"[Runway] {e}")
        return None

    # ── HuggingFace (Sınırsız Fallback) ─────────────────────────────────────
    def _huggingface(self, prompt: str, idx: int) -> str | None:
        try:
            r = requests.post("https://api-inference.huggingface.co/models/damo-vilab/text-to-video-ms-1.7b",
                              headers={"Authorization": f"Bearer {self.hf_token}"}, json={"inputs": prompt}, timeout=120)
            if r.status_code == 200:
                path = os.path.join(OUTPUT_DIR, f"hf_{idx}.mp4")
                with open(path, "wb") as f: f.write(r.content)
                return path
        except Exception as e: logger.debug(f"[HF] {e}")
        return None

    # ── FFmpeg Fallback ─────────────────────────────────────────────────────
    def _ffmpeg_animated(self, prompt: str, idx: int) -> str:
        out = os.path.join(OUTPUT_DIR, f"fallback_{idx}.mp4")
        color = "0x001833" if "blue" in prompt.lower() or "electric" in prompt.lower() else "0x0A0A1E"
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
