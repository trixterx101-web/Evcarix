"""
Evcarix AI Video Generator
Generates topic-relevant AI videos using multiple providers.
Fallback chain: Kling → Runway → Luma → Stability → HuggingFace (free)

Environment variables (add to GitHub Secrets):
  KLING_API_KEY       — Kling AI (https://klingai.com)
  RUNWAY_API_KEY      — Runway ML (https://runwayml.com)
  LUMA_API_KEY        — Luma Dream Machine (https://lumalabs.ai)
  STABILITY_API_KEY   — Stability AI (https://stability.ai)
  (HuggingFace: free, no key needed)
"""

import os
import re
import time
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime

ASSETS_DIR = Path("assets") / "ai_video"
TIMEOUT    = 60
POLL_EVERY = 5    # seconds between status checks
MAX_WAIT   = 300  # max 5 min wait per generation

HEADERS_JSON = {"Content-Type": "application/json"}


# ── Topic → AI video prompt map ───────────────────────────────────────────────
PROMPT_TEMPLATES = {
    "battery": (
        "Close-up cinematic shot of glowing lithium battery cells arranged "
        "in a grid, blue energy pulses flowing through circuit patterns, "
        "dark background, 4K, photorealistic, no text, no people"
    ),
    "range": (
        "Aerial drone shot of a sleek white electric car driving on an empty "
        "highway at sunset, motion blur on wheels, golden hour lighting, "
        "cinematic, no text, no logos"
    ),
    "charging": (
        "Cinematic close-up of an electric vehicle charging connector "
        "plugging into a modern EV port, blue electricity sparks, "
        "dark background, 4K slow motion, no text, no people"
    ),
    "ownership": (
        "Split screen animation showing coins stacking vs fuel pump, "
        "then electric charging icon, clean minimal style, "
        "dark background, smooth motion, no text"
    ),
    "comparison": (
        "Two sleek electric cars side by side on a dark showroom floor, "
        "rotating slowly, dramatic blue lighting, 4K cinematic, "
        "no text, no logos, no people"
    ),
    "market": (
        "Animated world map with glowing blue dots spreading across "
        "continents representing EV adoption, dark background, "
        "cinematic data visualization, no text"
    ),
    "infrastructure": (
        "Aerial view of a modern EV charging station with multiple cars "
        "charging simultaneously, sunset lighting, cinematic drone shot, "
        "no text, no logos"
    ),
    "education": (
        "Animated cross-section of an electric motor spinning, "
        "glowing coils and magnets, blue energy flow, dark background, "
        "technical visualization, 4K, no text"
    ),
    "tools": (
        "Futuristic digital dashboard with animated EV data charts, "
        "glowing graphs updating in real-time, dark UI, "
        "cinematic tech aesthetic, no text readable, no people"
    ),
    "default": (
        "Sleek electric car driving through a modern city at night, "
        "light trails, cinematic, 4K, no text, no logos, no people"
    ),
}


def get_prompt(topic: str, category_id: str = "") -> str:
    """Return best AI video prompt for the given topic."""
    combined = (topic + " " + category_id).lower()
    for key in PROMPT_TEMPLATES:
        if key in combined:
            return PROMPT_TEMPLATES[key]
    # keyword scan
    if any(w in combined for w in ["battery", "pil", "lfp", "nmc", "degradasyon"]):
        return PROMPT_TEMPLATES["battery"]
    if any(w in combined for w in ["range", "menzil", "winter", "kış", "efficiency"]):
        return PROMPT_TEMPLATES["range"]
    if any(w in combined for w in ["charging", "şarj", "800v", "fast charge"]):
        return PROMPT_TEMPLATES["charging"]
    if any(w in combined for w in ["cost", "maliyet", "fiyat", "ownership"]):
        return PROMPT_TEMPLATES["ownership"]
    if any(w in combined for w in ["comparison", "karşılaştırma", "vs", "ranking"]):
        return PROMPT_TEMPLATES["comparison"]
    if any(w in combined for w in ["market", "pazar", "sales", "satış", "china"]):
        return PROMPT_TEMPLATES["market"]
    if any(w in combined for w in ["infrastructure", "altyapı", "grid", "şebeke"]):
        return PROMPT_TEMPLATES["infrastructure"]
    return PROMPT_TEMPLATES["default"]


class AIVideoGenerator:

    def __init__(self):
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self.kling_key     = os.environ.get("KLING_API_KEY", "")
        self.runway_key    = os.environ.get("RUNWAY_API_KEY", "")
        self.luma_key      = os.environ.get("LUMA_API_KEY", "")
        self.stability_key = os.environ.get("STABILITY_API_KEY", "")

    # ── Public API ─────────────────────────────────────────────────────────────
    def generate(self, topic: str, category_id: str = "",
                 count: int = 3, duration: int = 6,
                 video_type: str = "short") -> list[str]:
        """
        Generate `count` AI videos for the topic.
        Returns list of local file paths.
        """
        prompt = get_prompt(topic, category_id)
        aspect = "9:16" if video_type == "short" else "16:9"
        print(f"[AIVideo] Prompt: {prompt[:80]}...")
        print(f"[AIVideo] Format: {aspect} | Count: {count}")

        clips = []
        providers = self._get_provider_chain()

        for provider_name, provider_fn in providers:
            if len(clips) >= count:
                break
            needed = count - len(clips)
            print(f"[AIVideo] Provider: {provider_name} ({needed} klip)")
            try:
                new = provider_fn(
                    prompt=prompt,
                    count=needed,
                    duration=duration,
                    aspect=aspect,
                )
                clips.extend(new)
                if new:
                    print(f"[AIVideo] ✅ {provider_name}: +{len(new)} klip")
            except Exception as e:
                print(f"[AIVideo] ⚠️ {provider_name} hata: {e}")

        if not clips:
            print("[AIVideo] ⚠️ Hiçbir AI provider çalışmadı.")
        return clips[:count]

    # ── Provider chain ─────────────────────────────────────────────────────────
    def _get_provider_chain(self) -> list:
        chain = []
        if self.kling_key:
            chain.append(("Kling AI",      self._kling))
        if self.runway_key:
            chain.append(("Runway ML",     self._runway))
        if self.luma_key:
            chain.append(("Luma Dream",    self._luma))
        if self.stability_key:
            chain.append(("Stability AI",  self._stability))
        # HuggingFace is always available (free, no key)
        chain.append(("HuggingFace",   self._huggingface))
        return chain

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: Kling AI ────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _kling(self, prompt: str, count: int,
               duration: int, aspect: str) -> list[str]:
        """
        Kling AI text-to-video API.
        Docs: https://docs.klingai.com/en/video-generation/text-to-video
        """
        clips = []
        for i in range(count):
            try:
                # Submit generation task
                r = requests.post(
                    "https://api.klingai.com/v1/videos/text2video",
                    headers={
                        "Authorization": f"Bearer {self.kling_key}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "model_name":    "kling-v1",
                        "prompt":        prompt,
                        "negative_prompt": "text, watermark, logo, people faces, hands",
                        "cfg_scale":     0.5,
                        "mode":          "std",
                        "duration":      str(min(duration, 10)),
                        "aspect_ratio":  aspect,
                    },
                    timeout=TIMEOUT,
                )
                if r.status_code not in (200, 201):
                    print(f"[Kling] Submit hata: {r.status_code} {r.text[:100]}")
                    break

                data    = r.json()
                task_id = (data.get("data", {}).get("task_id") or
                           data.get("task_id", ""))
                if not task_id:
                    break

                # Poll for completion
                path = self._kling_poll(task_id, i)
                if path:
                    clips.append(path)
                time.sleep(2)

            except Exception as e:
                print(f"[Kling] {e}")
                break
        return clips

    def _kling_poll(self, task_id: str, idx: int) -> str | None:
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"https://api.klingai.com/v1/videos/text2video/{task_id}",
                    headers={"Authorization": f"Bearer {self.kling_key}"},
                    timeout=TIMEOUT,
                )
                data   = r.json()
                status = (data.get("data", {}).get("task_status") or
                          data.get("status", ""))
                if status in ("succeed", "completed", "done"):
                    videos = (data.get("data", {}).get("task_result", {})
                                  .get("videos", []))
                    if videos:
                        url = videos[0].get("url", "")
                        if url:
                            return self._download_video(url, f"kling_{idx}")
                elif status in ("failed", "error"):
                    print(f"[Kling] Task failed: {task_id}")
                    return None
                print(f"[Kling] Bekleniyor... status={status}")
                time.sleep(POLL_EVERY)
            except Exception as e:
                print(f"[Kling] Poll hata: {e}")
                time.sleep(POLL_EVERY)
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: Runway ML ───────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _runway(self, prompt: str, count: int,
                duration: int, aspect: str) -> list[str]:
        """
        Runway Gen-3 Alpha text-to-video.
        Docs: https://docs.dev.runwayml.com
        """
        clips = []
        ratio = "720:1280" if aspect == "9:16" else "1280:720"
        for i in range(count):
            try:
                r = requests.post(
                    "https://api.dev.runwayml.com/v1/image_to_video",
                    headers={
                        "Authorization": f"Bearer {self.runway_key}",
                        "Content-Type":  "application/json",
                        "X-Runway-Version": "2024-11-06",
                    },
                    json={
                        "model":         "gen3a_turbo",
                        "promptText":    prompt,
                        "duration":      min(duration, 10),
                        "ratio":         ratio,
                        "seed":          int(time.time()) + i,
                    },
                    timeout=TIMEOUT,
                )
                if r.status_code not in (200, 201):
                    print(f"[Runway] Submit hata: {r.status_code}")
                    break

                data    = r.json()
                task_id = data.get("id", "")
                if not task_id:
                    break

                path = self._runway_poll(task_id, i)
                if path:
                    clips.append(path)
                time.sleep(2)

            except Exception as e:
                print(f"[Runway] {e}")
                break
        return clips

    def _runway_poll(self, task_id: str, idx: int) -> str | None:
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                    headers={
                        "Authorization": f"Bearer {self.runway_key}",
                        "X-Runway-Version": "2024-11-06",
                    },
                    timeout=TIMEOUT,
                )
                data   = r.json()
                status = data.get("status", "")
                if status == "SUCCEEDED":
                    output = data.get("output", [])
                    if output:
                        return self._download_video(output[0], f"runway_{idx}")
                elif status == "FAILED":
                    print(f"[Runway] Task failed: {task_id}")
                    return None
                print(f"[Runway] Bekleniyor... status={status}")
                time.sleep(POLL_EVERY)
            except Exception as e:
                print(f"[Runway] Poll hata: {e}")
                time.sleep(POLL_EVERY)
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: Luma Dream Machine ──────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _luma(self, prompt: str, count: int,
              duration: int, aspect: str) -> list[str]:
        """
        Luma AI Dream Machine text-to-video.
        Docs: https://lumalabs.ai/dream-machine/api
        """
        clips = []
        for i in range(count):
            try:
                r = requests.post(
                    "https://api.lumalabs.ai/dream-machine/v1/generations",
                    headers={
                        "Authorization": f"Bearer {self.luma_key}",
                        "Content-Type":  "application/json",
                    },
                    json={
                        "prompt":       prompt,
                        "aspect_ratio": aspect,
                        "loop":         False,
                    },
                    timeout=TIMEOUT,
                )
                if r.status_code not in (200, 201):
                    print(f"[Luma] Submit hata: {r.status_code}")
                    break

                data    = r.json()
                task_id = data.get("id", "")
                if not task_id:
                    break

                path = self._luma_poll(task_id, i)
                if path:
                    clips.append(path)
                time.sleep(2)

            except Exception as e:
                print(f"[Luma] {e}")
                break
        return clips

    def _luma_poll(self, task_id: str, idx: int) -> str | None:
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"https://api.lumalabs.ai/dream-machine/v1/generations/{task_id}",
                    headers={"Authorization": f"Bearer {self.luma_key}"},
                    timeout=TIMEOUT,
                )
                data   = r.json()
                status = data.get("state", "")
                if status == "completed":
                    url = data.get("video", {}).get("url", "")
                    if url:
                        return self._download_video(url, f"luma_{idx}")
                elif status == "failed":
                    print(f"[Luma] Task failed: {task_id}")
                    return None
                print(f"[Luma] Bekleniyor... status={status}")
                time.sleep(POLL_EVERY)
            except Exception as e:
                print(f"[Luma] Poll hata: {e}")
                time.sleep(POLL_EVERY)
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: Stability AI ────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _stability(self, prompt: str, count: int,
                   duration: int, aspect: str) -> list[str]:
        """
        Stability AI Stable Video Diffusion.
        Docs: https://platform.stability.ai/docs/api-reference#tag/Video
        """
        clips = []
        for i in range(count):
            try:
                r = requests.post(
                    "https://api.stability.ai/v2beta/image-to-video",
                    headers={"Authorization": f"Bearer {self.stability_key}"},
                    files={"none": ""},
                    data={
                        "seed":           str(int(time.time()) + i),
                        "cfg_scale":      "1.8",
                        "motion_bucket_id": "127",
                    },
                    timeout=TIMEOUT,
                )
                if r.status_code not in (200, 202):
                    print(f"[Stability] Submit hata: {r.status_code}")
                    break

                gen_id = r.json().get("id", "")
                if not gen_id:
                    break

                path = self._stability_poll(gen_id, i)
                if path:
                    clips.append(path)
                time.sleep(2)

            except Exception as e:
                print(f"[Stability] {e}")
                break
        return clips

    def _stability_poll(self, gen_id: str, idx: int) -> str | None:
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"https://api.stability.ai/v2beta/image-to-video/result/{gen_id}",
                    headers={
                        "Authorization": f"Bearer {self.stability_key}",
                        "Accept": "video/*",
                    },
                    timeout=TIMEOUT,
                )
                if r.status_code == 200:
                    path = ASSETS_DIR / f"stability_{idx}_{gen_id[:8]}.mp4"
                    with open(path, "wb") as f:
                        f.write(r.content)
                    if path.stat().st_size > 100_000:
                        print(f"[Stability] ✅ {path.name}")
                        return str(path)
                elif r.status_code == 202:
                    print("[Stability] Bekleniyor...")
                    time.sleep(POLL_EVERY)
                else:
                    print(f"[Stability] Poll hata: {r.status_code}")
                    return None
            except Exception as e:
                print(f"[Stability] Poll hata: {e}")
                time.sleep(POLL_EVERY)
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: HuggingFace (FREE — no API key) ─────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _huggingface(self, prompt: str, count: int,
                     duration: int, aspect: str) -> list[str]:
        """
        HuggingFace free Inference API — zeroscope_v2_576w model.
        No API key required. Rate limited but always available.
        """
        clips = []
        hf_token = os.environ.get("HF_TOKEN", "")  # optional, increases rate limit
        headers  = {"Content-Type": "application/json"}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        models = [
            "cerspense/zeroscope_v2_576w",
            "damo-vilab/text-to-video-ms-1.7b",
        ]

        for i in range(count):
            model = models[i % len(models)]
            try:
                print(f"[HuggingFace] Model: {model}")
                r = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=headers,
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "num_frames":          16,
                            "num_inference_steps": 25,
                            "guidance_scale":      7.5,
                        }
                    },
                    timeout=120,
                )
                if r.status_code == 200:
                    ct = r.headers.get("content-type", "")
                    if "video" in ct or "octet-stream" in ct:
                        path = ASSETS_DIR / f"hf_{i}_{int(time.time())}.mp4"
                        with open(path, "wb") as f:
                            f.write(r.content)
                        if path.stat().st_size > 50_000:
                            print(f"[HuggingFace] ✅ {path.name}")
                            clips.append(str(path))
                elif r.status_code == 503:
                    print(f"[HuggingFace] Model yükleniyor, bekleniyor...")
                    time.sleep(20)
                else:
                    print(f"[HuggingFace] {r.status_code}: {r.text[:80]}")
            except Exception as e:
                print(f"[HuggingFace] {e}")
            time.sleep(3)
        return clips

    # ── Download helper ────────────────────────────────────────────────────────
    def _download_video(self, url: str, prefix: str) -> str | None:
        uid  = hashlib.md5(url.encode()).hexdigest()[:8]
        path = ASSETS_DIR / f"{prefix}_{uid}.mp4"
        if path.exists() and path.stat().st_size > 100_000:
            return str(path)
        try:
            r = requests.get(url, timeout=60, stream=True)
            if r.status_code != 200:
                return None
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=131072):
                    f.write(chunk)
            if path.stat().st_size < 50_000:
                path.unlink(missing_ok=True)
                return None
            return str(path)
        except Exception as e:
            print(f"[AIVideo] Download hata: {e}")
            if path.exists():
                path.unlink(missing_ok=True)
            return None


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    gen = AIVideoGenerator()
    clips = gen.generate(
        topic       = "BYD Seagull battery efficiency",
        category_id = "market",
        count       = 2,
        duration    = 6,
        video_type  = "short",
    )
    print(f"\nÜretilen: {len(clips)} klip")
    for c in clips:
        print(f"  → {c}")
