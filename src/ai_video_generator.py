import os
import json
import time
import requests
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("AIVideoGenerator")
OUTPUT_DIR = "assets/ai_clips"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Görsel Temalar ───────────────────────────────────────────
THEMES = {
    "electric": {"bg": "#001833", "acc": "#00D4FF"},
    "green":    {"bg": "#001A00", "acc": "#00FF88"},
    "purple":   {"bg": "#0D001A", "acc": "#CC44FF"},
    "orange":   {"bg": "#1A0800", "acc": "#FF6B00"},
    "gold":     {"bg": "#1A1400", "acc": "#FFD700"},
    "red":      {"bg": "#1A0000", "acc": "#FF3300"},
}

KEYWORD_MAP = {
    "electric": ["blue","electric","battery","energy","charge","ev","volt","lfp","lithium"],
    "green":    ["green","robot","factory","eco","sustainable","plant","clean"],
    "purple":   ["purple","ai","neural","data","tech","future","digital","analysis"],
    "orange":   ["orange","mining","desert","solar","warm","heat"],
    "gold":     ["gold","luxury","premium","speed","performance","race","fast"],
    "red":      ["red","power","engine","fire","fast","turbo","sport","danger"],
}

TITLE_MAP = {
    "speed":    ("SPEED VS",   "RANGE"),
    "range":    ("RANGE",      "ANALYSIS"),
    "battery":  ("BATTERY",    "CAPACITY"),
    "charge":   ("TURBO",      "CHARGE"),
    "electric": ("ELECTRIC",   "VEHICLE"),
    "lithium":  ("LITHIUM",    "ENERGY"),
    "default":  ("AI VIDEO",   "CONTENT"),
}

def _pick_theme(prompt: str) -> dict:
    pl = prompt.lower()
    for name, kws in KEYWORD_MAP.items():
        if any(k in pl for k in kws): return THEMES[name]
    return THEMES["electric"]

def _pick_titles(prompt: str) -> tuple[str, str]:
    pl = prompt.lower()
    for key, pair in TITLE_MAP.items():
        if key in pl: return pair
    words = [w.upper() for w in prompt.split()[:4]]
    t1 = " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else "EVCARIX")
    t2 = " ".join(words[2:]) if len(words) > 2 else "AUTO-STUDIO"
    return t1, t2

def _build_vf(title1: str, title2: str, sub: str, bg: str, acc: str) -> str:
    """Garantili ve estetik FFmpeg video filtresi."""
    line_ys  = [280, 580, 880, 1180, 1480, 1760]
    line_ops = [0.25, 0.12, 0.20, 0.12, 0.20, 0.12]
    parts = [f"drawbox=x=0:y=0:w=iw:h=ih:color={bg}@1.0:t=fill"]
    for y, op in zip(line_ys, line_ops):
        parts.append(f"drawbox=x=0:y={y}:w=iw:h=3:color={acc}@{op:.2f}:t=fill")
    parts += [
        f"drawtext=text='{title1}':fontsize=120:fontcolor={acc}:x=(w-tw)/2:y=(h-th)/2-160:shadowcolor=black@0.9:shadowx=5:shadowy=5",
        f"drawtext=text='{title2}':fontsize=120:fontcolor={acc}:x=(w-tw)/2:y=(h-th)/2:shadowcolor=black@0.9:shadowx=5:shadowy=5",
        f"drawtext=text='{sub}':fontsize=48:fontcolor=white@0.75:x=(w-tw)/2:y=(h-th)/2+160",
        f"drawtext=text='EVCARIX':fontsize=36:fontcolor={acc}@0.50:x=(w-tw)/2:y=(h-th)/2+250"
    ]
    return ",".join(parts)

class AIVideoGenerator:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.muapi_key  = os.getenv("MUAPI_KEY")
        self.fal_key    = os.getenv("FAL_KEY")
        self.kling_key  = os.getenv("KLING_API_KEY")
        self.luma_key   = os.getenv("LUMA_API_KEY")
        self.hf_token   = os.getenv("HF_TOKEN")

    def generate_clips(self, prompts: list[str]) -> list[str]:
        clips = []
        for i, prompt in enumerate(prompts):
            path = None
            logger.info(f"[AIVideo] Sahne {i+1} üretiliyor...")
            
            # 1. AI Kaynakları (Sırayla)
            methods = [
                ("Veo", self._google_veo),
                ("Muapi", self._muapi),
                ("FalAI", self._fal_ai),
                ("Kling", self._kling),
                ("Luma", self._luma),
                ("HF", self._huggingface)
            ]
            
            for name, method in methods:
                try:
                    path = method(prompt, i)
                    if path and self._validate(path):
                        logger.info(f"[AIVideo] ✅ {name} Başarılı!")
                        break
                except: pass
            
            # 2. AI Başarısız bildirimi (Artık fallback burada üretilmiyor, Pexels'e şans veriliyor)
            if not path:
                logger.warning(f"[AIVideo] ⚠️ Sahne {i+1} için AI başarısız, Pexels/Pixabay devreye girecek.")
            
            if path: clips.append(path)
        return clips

    def _google_veo(self, prompt, idx):
        if not self.gemini_key: return None
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.gemini_key)
            logger.info(f"[GoogleVeo] Veo 2.0 ile video üretimi başlatılıyor (Sahne {idx+1})")
            
            operation = client.models.generate_videos(
                model="veo-2.0-generate-001",
                prompt=prompt,
                config=types.GenerateVideosConfig(
                    aspect_ratio="9:16",
                    duration_seconds=5,
                    number_of_videos=1,
                )
            )

            # Üretim tamamlanana kadar bekle (max 3 dakika)
            for _ in range(36):
                if operation.done:
                    break
                time.sleep(5)
                operation = client.operations.get(operation)

            if operation.done and operation.response.generated_videos:
                video = operation.response.generated_videos[0]
                p = os.path.join(OUTPUT_DIR, f"veo_{idx}.mp4")
                # Videoyu indir
                client.files.download(file=video.video, download_path=p)
                return p if os.path.exists(p) else None

        except Exception as e:
            logger.debug(f"[GoogleVeo] Hata: {e}")
        return None

    def _muapi(self, prompt, idx):
        if not self.muapi_key: return None
        r = requests.post("https://api.muapi.ai/v1/video/generate", headers={"Authorization": f"Bearer {self.muapi_key}"}, 
                          json={"model": "kling-v1.6", "prompt": prompt, "aspect_ratio": "9:16"}, timeout=10)
        if r.status_code == 200:
            tid = r.json().get("task_id")
            for _ in range(20):
                tr = requests.get(f"https://api.muapi.ai/v1/video/status/{tid}", headers={"Authorization": f"Bearer {self.muapi_key}"})
                d = tr.json()
                if d.get("status") == "succeeded": return self._download(d["video_url"], f"mu_{idx}.mp4")
                time.sleep(10)
        return None

    def _fal_ai(self, prompt, idx):
        if not self.fal_key: return None
        import fal_client
        h = fal_client.submit("fal-ai/kling-video/v1.6/standard/text-to-video", arguments={"prompt": prompt, "aspect_ratio": "9:16"})
        for _ in range(30):
            s = fal_client.status("fal-ai/kling-video/v1.6/standard/text-to-video", h.request_id)
            if s.status == "COMPLETED": return self._download(s.response["video"]["url"], f"fal_{idx}.mp4")
            time.sleep(10)
        return None

    def _ffmpeg_animated(self, prompt: str, idx: int) -> str:
        out = os.path.join(OUTPUT_DIR, f"ffmpeg_{idx}.mp4")
        theme = _pick_theme(prompt)
        bg, acc = theme["bg"], theme["acc"]
        t1, t2 = _pick_titles(prompt)
        sub = " ".join(w.upper() for w in prompt.split()[4:8]) if len(prompt.split()) > 4 else "AI ANALYSIS"
        
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-r", "30",
            "-i", f"color=c={bg}:size=1080x1920:rate=30",
            "-vf", _build_vf(t1, t2, sub, bg, acc),
            "-t", "5", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", "30", "-an", out
        ]
        subprocess.run(cmd, capture_output=True)
        return out

    def _validate(self, path: str) -> bool:
        if not path or not os.path.exists(path): return False
        if os.path.getsize(path) < 5000: return False
        return True

    def _download(self, url, name):
        p = os.path.join(OUTPUT_DIR, name)
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                with open(p, "wb") as f: f.write(r.content)
                return p
        except: pass
        return None

    def _kling(self, p, i): return None
    def _luma(self, p, i): return None
    def _huggingface(self, p, i): return None
