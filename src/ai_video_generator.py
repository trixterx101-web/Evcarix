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
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.seedance_key = os.getenv("SEEDANCE_API_KEY")
        self.pixverse_key = os.getenv("PIXVERSE_API_KEY")
        self.vidu_key = os.getenv("VIDU_API_KEY")
        self.muapi_key = os.getenv("MUAPI_KEY")
        self.videogen_key = os.getenv("VIDEOGEN_API_KEY")
        self.zsky_key = os.getenv("ZSKY_API_KEY")
        self.fal_key = os.getenv("FAL_KEY")
        self.replicate_key = os.getenv("REPLICATE_API_TOKEN")
        self.kling_key = os.getenv("KLING_API_KEY")
        self.luma_key = os.getenv("LUMA_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")

    def generate_clips(self, prompts: list[str]) -> list[str]:
        if not prompts: return []
        clips = []
        for i, prompt in enumerate(prompts):
            path = None
            logger.info(f"[AIVideo] Sahne {i+1} üretiliyor...")
            
            # Öncelikli kaynakları sırayla dene
            for method in [self._google_veo, self._seedance, self._pixverse, self._vidu, 
                           self._muapi, self._fal_ai, self._replicate, self._kling]:
                path = method(prompt, i)
                if path: break
            
            if not path:
                logger.warning(f"[AIVideo] Fallback üretiliyor (Sahne {i+1})")
                path = self._ffmpeg_animated(prompt, i)
            
            if path: clips.append(path)
        return clips

    def _google_veo(self, prompt, idx):
        if not self.gemini_key: return None
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            for m in ["veo-3-1", "gemini-1.5-flash"]:
                try:
                    model = genai.GenerativeModel(m)
                    res = model.generate_content(prompt)
                    if res and hasattr(res, 'data'):
                        p = os.path.join(OUTPUT_DIR, f"veo_{idx}.mp4")
                        with open(p, "wb") as f: f.write(res.data)
                        return p
                except: continue
        except: pass
        return None

    def _seedance(self, prompt, idx):
        if not self.seedance_key: return None
        try:
            r = requests.post("https://api.seedance.tv/v1/video/generate", headers={"Authorization": f"Bearer {self.seedance_key}"}, 
                              json={"prompt": prompt, "aspect_ratio": "9:16"}, timeout=10)
            if r.status_code == 200:
                tid = r.json().get("task_id")
                for _ in range(30):
                    tr = requests.get(f"https://api.seedance.tv/v1/video/status/{tid}", headers={"Authorization": f"Bearer {self.seedance_key}"})
                    if tr.json().get("status") == "completed": return self._download(tr.json()["video_url"], f"seed_{idx}.mp4")
                    time.sleep(10)
        except: pass
        return None

    def _pixverse(self, prompt, idx):
        if not self.pixverse_key: return None
        try:
            r = requests.post("https://api.pixverse.ai/v1/video/generate", headers={"Authorization": f"Bearer {self.pixverse_key}"}, 
                              json={"prompt": prompt, "ratio": "9:16"}, timeout=10)
            if r.status_code == 200:
                tid = r.json().get("task_id")
                for _ in range(30):
                    tr = requests.get(f"https://api.pixverse.ai/v1/video/status/{tid}", headers={"Authorization": f"Bearer {self.pixverse_key}"})
                    if tr.json().get("status") == "completed": return self._download(tr.json()["video_url"], f"pix_{idx}.mp4")
                    time.sleep(10)
        except: pass
        return None

    def _vidu(self, prompt, idx):
        if not self.vidu_key: return None
        try:
            r = requests.post("https://api.vidu.studio/v1/generations", headers={"Authorization": f"Bearer {self.vidu_key}"}, 
                              json={"prompt": prompt, "aspect_ratio": "9:16"}, timeout=10)
            if r.status_code == 200:
                gid = r.json().get("id")
                for _ in range(30):
                    tr = requests.get(f"https://api.vidu.studio/v1/generations/{gid}", headers={"Authorization": f"Bearer {self.vidu_key}"})
                    if tr.json().get("state") == "completed": return self._download(tr.json()["video_url"], f"vidu_{idx}.mp4")
                    time.sleep(5)
        except: pass
        return None

    def _muapi(self, prompt, idx):
        if not self.muapi_key: return None
        try:
            r = requests.post("https://api.muapi.ai/v1/video/generate", headers={"Authorization": f"Bearer {self.muapi_key}"}, 
                              json={"model": "kling-v1.6", "prompt": prompt, "aspect_ratio": "9:16"}, timeout=10)
            if r.status_code == 200:
                tid = r.json().get("task_id")
                for _ in range(30):
                    tr = requests.get(f"https://api.muapi.ai/v1/video/status/{tid}", headers={"Authorization": f"Bearer {self.muapi_key}"})
                    if tr.json().get("status") == "succeeded": return self._download(tr.json()["video_url"], f"mu_{idx}.mp4")
                    time.sleep(10)
        except: pass
        return None

    def _fal_ai(self, prompt, idx):
        if not self.fal_key: return None
        try:
            import fal_client
            h = fal_client.submit("fal-ai/kling-video/v1.6/standard/text-to-video", arguments={"prompt": prompt, "aspect_ratio": "9:16"})
            for _ in range(30):
                s = fal_client.status("fal-ai/kling-video/v1.6/standard/text-to-video", h.request_id)
                if s.status == "COMPLETED": return self._download(s.response["video"]["url"], f"fal_{idx}.mp4")
                time.sleep(10)
        except: pass
        return None

    def _replicate(self, prompt, idx):
        if not self.replicate_key: return None
        try:
            import replicate
            out = replicate.run("wan-video/wan-2.1-14b-t2v-turbo", input={"prompt": prompt, "aspect_ratio": "9:16"})
            if out: return self._download(out[0] if isinstance(out, list) else out, f"rep_{idx}.mp4")
        except: pass
        return None

    def _kling(self, prompt, idx):
        if not self.kling_key: return None
        # ... (Basitleştirilmiş Kling) ...
        return None

    def _ffmpeg_animated(self, prompt, idx):
        out = os.path.join(OUTPUT_DIR, f"fb_{idx}.mp4")
        cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x0A0A1E:s=1080x1920:r=30", "-t", "5", "-c:v", "libx264", "-pix_fmt", "yuv420p", out]
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
