"""
Evcarix AI Video Generator
Generates topic-relevant AI videos using multiple providers.
Fallback chain: fal.ai → Kling → Runway → Luma → Stability → Wan2.2 → HuggingFace (free)

Environment variables (add to GitHub Secrets):
  FAL_KEY             — fal.ai LTX-Video (https://fal.ai)  — free credits
  KLING_API_KEY       — Kling AI (https://klingai.com)
  RUNWAY_API_KEY      — Runway ML (https://runwayml.com)
  LUMA_API_KEY        — Luma Dream Machine (https://lumalabs.ai)
  STABILITY_API_KEY   — Stability AI (https://stability.ai)
  HF_TOKEN            — HuggingFace (Wan 2.1 & Wan 2.2 via Nebius) — free
"""

import os
import re
import time
import json
import hashlib
import requests
import jwt
import replicate
from pathlib import Path
from huggingface_hub import InferenceClient
from datetime import datetime

ASSETS_DIR = Path("assets") / "ai_video"
TIMEOUT    = 60
POLL_EVERY = 5    # seconds between status checks
MAX_WAIT   = 300  # max 5 min wait per generation

HEADERS_JSON = {"Content-Type": "application/json"}


# ── Topic → AI video prompt map ───────────────────────────────────────────────
PROMPT_TEMPLATES = {
    # ⚡ Elektrikli Araç (EV)
    "electric vehicle": (
        "Cinematic slow-motion shot of a futuristic electric car driving through a "
        "neon-lit smart city at night, light trails, 8K resolution, photorealistic, "
        "highly detailed, no text, no people"
    ),
    "charging": (
        "Ultra-realistic close-up of a high-tech EV charging plug connecting to a "
        "sleek electric vehicle, glowing blue energy pulses flowing through the cable, "
        "bokeh background, 4K, cinematic lighting"
    ),
    
    # 🤖 Yapay Zeka (AI)
    "artificial intelligence": (
        "Abstract visualization of a neural network firing, glowing blue and gold "
        "data nodes connecting, digital brain silhouette in the background, "
        "cyberpunk aesthetic, high-speed data flow, 4K"
    ),
    "ai": (
        "Close-up of a futuristic digital interface with floating holographic "
        "data charts and AI processing animations, sleek tech aesthetic, dark background"
    ),
    
    # 🦾 Robotik
    "robotics": (
        "Close-up of a highly advanced humanoid robot hand performing delicate movements, "
        "intricate mechanical joints, silver and white metallic finish, factory laboratory "
        "background, cinematic lighting, 8K"
    ),
    "robot": (
        "A futuristic robot walking through a high-tech facility, smooth movements, "
        "robotic laboratory atmosphere, cinematic shadows and highlights, photorealistic"
    ),
    
    # 🔋 Batarya Teknolojisi
    "battery": (
        "Macro shot of glowing solid-state battery cells, blue liquid energy flowing "
        "inside transparent containers, futuristic laboratory setting, 4K, high detail"
    ),
    "lithium": (
        "Cinematic animation of lithium ions moving through a battery structure, "
        "glowing sparks of energy, technical visualization, vibrant colors, 4K"
    ),
    
    # 🚀 Geleceğin Teknolojileri
    "future technology": (
        "Aerial view of a futuristic smart city with flying vehicles and green "
        "hanging gardens, sunset lighting, cinematic drone shot, utopian aesthetic, 8K"
    ),
    "quantum": (
        "Abstract quantum computing visualization, particles in superposition, "
        "glowing waves of probability, deep space background, cinematic, 4K"
    ),
    
    "default": (
        "Sleek futuristic technology concept, glowing blue lights, dark premium "
        "background, cinematic 4K, high detail, no text"
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
        self.kling_ak      = os.environ.get("KLING_ACCESS_KEY", "")
        self.kling_sk      = os.environ.get("KLING_SECRET_KEY", "")
        self.kling_key     = os.environ.get("KLING_API_KEY", "")  # fallback if someone has a direct token
        self.runway_key    = os.environ.get("RUNWAY_API_KEY", "")
        self.luma_key      = os.environ.get("LUMA_API_KEY", "")
        self.stability_key = os.environ.get("STABILITY_API_KEY", "")
        self.fal_key       = os.environ.get("FAL_KEY", "")
        self.replicate_key = os.environ.get("REPLICATE_API_KEY", "")
        self.geminigen_key = os.environ.get("GEMINIGEN_API_KEY", "")

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
                    print(f"[AIVideo] [OK] {provider_name}: +{len(new)} klip")
            except Exception as e:
                print(f"[AIVideo] [Error] {provider_name} hata: {e}")

        if not clips:
            print("[AIVideo] [Error] Hicbir AI provider calismadi.")
        return clips[:count]

    # ── Provider chain ─────────────────────────────────────────────────────────
    def _get_provider_chain(self) -> list:
        chain = []
        if self.geminigen_key:
            chain.append(("GeminiGen AI",      self._geminigen))
        if self.replicate_key:
            chain.append(("Replicate HD",       self._replicate))
        if self.fal_key:
            chain.append(("fal.ai LTX-Video",   self._fal_ltx))
        if self.kling_key or (self.kling_ak and self.kling_sk):
            chain.append(("Kling AI",            self._kling))
        if self.runway_key:
            chain.append(("Runway ML",           self._runway))
        if self.luma_key:
            chain.append(("Luma Dream",          self._luma))
        if self.stability_key:
            chain.append(("Stability AI",        self._stability))
        # Always available fallbacks (ücretsiz)
        chain.append(("HF InferenceClient",  self._hf_inference_client))
        chain.append(("HuggingFace Gradio",  self._huggingface_gradio))
        chain.append(("Wan 2.2 HF Router",   self._wan22))
        chain.append(("Wan 2.1 HF Router",   self._huggingface_router))
        return chain

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: GeminiGen AI (NEW) ──────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _geminigen(self, prompt: str, count: int,
                  duration: int, aspect: str) -> list[str]:
        """
        GeminiGen AI (geminigen.ai) - Powerful Google Veo 3.1 Fast Video Gen.
        Endpoint: https://api.geminigen.ai/uapi/v1/video-gen/veo
        """
        clips = []
        headers = {
            "x-api-key": self.geminigen_key,
            "Content-Type": "application/json"
        }
        
        for i in range(count):
            try:
                print(f"[GeminiGen] Generating video {i+1}/{count}...")
                r = requests.post(
                    "https://api.geminigen.ai/uapi/v1/video-gen/veo",
                    headers=headers,
                    json={
                        "prompt": prompt,
                        "model": "google/veo-3.1-fast-video-gen",
                        "aspect_ratio": aspect
                    },
                    timeout=TIMEOUT
                )
                
                if r.status_code not in (200, 201):
                    print(f"[GeminiGen] Submit hata: {r.status_code} {r.text[:100]}")
                    break
                    
                data = r.json()
                uuid = data.get("uuid")
                if not uuid:
                    print(f"[GeminiGen] UUID alınamadı: {data}")
                    break
                    
                path = self._geminigen_poll(uuid, i, headers)
                if path:
                    clips.append(path)
                time.sleep(2)
            except Exception as e:
                print(f"[GeminiGen] Hata: {e}")
                break
        return clips

    def _geminigen_poll(self, uuid: str, idx: int, headers: dict) -> str | None:
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"https://api.geminigen.ai/uapi/v1/history/{uuid}",
                    headers=headers,
                    timeout=TIMEOUT
                )
                if r.status_code != 200:
                    print(f"[GeminiGen] Poll error: {r.status_code}")
                    time.sleep(POLL_EVERY)
                    continue
                    
                data = r.json()
                # Status: 1=Processing, 2=Completed, 3=Failed
                status = data.get("status")
                
                if status == 2:
                    gen_video = data.get("generated_video", [])
                    if gen_video and len(gen_video) > 0:
                        url = gen_video[0].get("video_url")
                        if url:
                            return self._download_video(url, f"geminigen_{idx}")
                elif status == 3:
                    error = data.get("error_message", "Unknown error")
                    print(f"[GeminiGen] Task failed: {error}")
                    return None
                
                print(f"[GeminiGen] Bekleniyor... status={status}")
                time.sleep(POLL_EVERY)
            except Exception as e:
                print(f"[GeminiGen] Poll exception: {e}")
                time.sleep(POLL_EVERY)
        return None

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: fal.ai LTX-Video (PRIMARY — best free option) ───────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _fal_ltx(self, prompt: str, count: int,
                 duration: int, aspect: str) -> list[str]:
        """
        fal.ai LTX-Video — open source, fast, high quality.
        Free credits on signup. ~$0.04/sec after that.
        Sign up: https://fal.ai  then copy API key to GitHub Secret FAL_KEY
        """
        import fal_client
        os.environ["FAL_KEY"] = self.fal_key
        clips = []

        video_size = "portrait_9_16" if aspect == "9:16" else "landscape_16_9"

        for i in range(count):
            try:
                print(f"[fal.ai] Generating video {i+1}/{count}...")
                result = fal_client.run(
                    "fal-ai/ltx-video-v095",
                    arguments={
                        "prompt": prompt,
                        "negative_prompt": (
                            "watermark, logo, text, people faces, hands, "
                            "blurry, low quality, distorted"
                        ),
                        "num_inference_steps": 30,
                        "guidance_scale": 3.0,
                        "num_frames": 97,
                        "fps": 24,
                        "video_size": video_size,
                        "seed": int(time.time()) + i,
                    }
                )
                video_url = result.get("video", {}).get("url", "")
                if video_url:
                    path = self._download_video(video_url, f"fal_{i}")
                    if path:
                        clips.append(path)
                        print(f"[fal.ai] [OK] Video {i+1} hazir: {path}")
                time.sleep(2)
            except Exception as e:
                print(f"[fal.ai] Hata: {e}")
                break
        return clips

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: Kling AI ────────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _generate_kling_token(self) -> str:
        """Generate JWT token for Kling AI API."""
        if not self.kling_ak or not self.kling_sk:
            return self.kling_key # fallback to direct token
        
        payload = {
            "iss": self.kling_ak,
            "exp": int(time.time()) + 1800, # 30 min
            "nbf": int(time.time()) - 5,
        }
        token = jwt.encode(payload, self.kling_sk, algorithm="HS256")
        return token

    def _kling(self, prompt: str, count: int,
               duration: int, aspect: str) -> list[str]:
        """
        Kling AI text-to-video API (Global / Singapore).
        Docs: https://klingai.com/help/api
        """
        token = self._generate_kling_token()
        if not token:
            print("[Kling] No API credentials found.")
            return []

        clips = []
        base_url = "https://api.klingai.com" # or https://api-singapore.klingai.com
        
        for i in range(count):
            try:
                # Submit generation task
                r = requests.post(
                    f"{base_url}/v1/videos/text2video",
                    headers={
                        "Authorization": f"Bearer {token}",
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
                path = self._kling_poll(task_id, i, token, base_url)
                if path:
                    clips.append(path)
                time.sleep(2)

            except Exception as e:
                print(f"[Kling] {e}")
                break
        return clips

    def _kling_poll(self, task_id: str, idx: int, token: str, base_url: str) -> str | None:
        deadline = time.time() + MAX_WAIT
        while time.time() < deadline:
            try:
                r = requests.get(
                    f"{base_url}/v1/videos/text2video/{task_id}",
                    headers={"Authorization": f"Bearer {token}"},
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
                        print(f"[Stability] [OK] {path.name}")
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
    # ── Provider: Replicate (Ultra HD Realistic) ────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _replicate(self, prompt: str, count: int,
                  duration: int, aspect: str) -> list[str]:
        """
        Replicate — high quality models like HunyuanVideo.
        Best for ultra-realistic HD output.
        """
        if not self.replicate_key:
            return []
        
        os.environ["REPLICATE_API_TOKEN"] = self.replicate_key
        clips = []
        
        # Use HunyuanVideo (current gold standard for open-weights realism)
        # specific version slug (latest as of May 2026)
        model_id = "lucataco/hunyuanvideo:2b1add9b58a0ff73fd7ff82407246c42c603d82234917bc65a4f84b45a154f92"
        
        for i in range(count):
            try:
                print(f"[Replicate] Generating HD video {i+1}/{count}...")
                # Run the model
                output = replicate.run(
                    model_id,
                    input={
                        "prompt": prompt,
                        "video_size": "720p", 
                        "num_frames": 81,
                        "infer_steps": 30,
                    }
                )
                
                # Output can be a URL string or a list of URLs
                video_url = None
                if isinstance(output, str):
                    video_url = output
                elif isinstance(output, list) and len(output) > 0:
                    video_url = output[0]
                elif hasattr(output, 'url'):
                    video_url = output.url
                
                if video_url:
                    path = self._download_video(video_url, f"replicate_{i}")
                    if path:
                        clips.append(path)
                        print(f"[Replicate] [OK] Video {i+1} hazir: {path}")
            except Exception as e:
                print(f"[Replicate] Hata: {e}")
                break
        return clips

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: HuggingFace InferenceClient (FREE Tier) ───────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _hf_inference_client(self, prompt: str, count: int,
                              duration: int, aspect: str) -> list[str]:
        """
        Uses HuggingFace InferenceClient (Serverless).
        Best for Wan-AI models.
        """
        hf_token = os.environ.get("HF_TOKEN", "")
        if not hf_token:
            return []

        client = InferenceClient(api_key=hf_token)
        clips = []
        
        # Try different models in order
        models = [
            "Wan-AI/Wan2.1-T2V-14B",
            "Wan-AI/Wan2.1-T2V-1.3B",
            "facebook/animatediff-video-v1-5",
        ]

        for i in range(count):
            model_id = models[i % len(models)]
            try:
                print(f"[HF Client] Model: {model_id}...")
                video_bytes = client.text_to_video(
                    prompt,
                    model=model_id,
                )
                
                path = ASSETS_DIR / f"hf_client_{i}_{int(time.time())}.mp4"
                with open(path, "wb") as f:
                    f.write(video_bytes)
                
                if path.stat().st_size > 50_000:
                    print(f"[HF Client] [OK] {path.name}")
                    clips.append(str(path))
            except Exception as e:
                print(f"[HF Client] {model_id} hata: {e}")
            
            if len(clips) >= count:
                break
        return clips

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: HuggingFace Gradio API (FREE — always available) ───────────
    # ══════════════════════════════════════════════════════════════════════════
    def _huggingface_gradio(self, prompt: str, count: int,
                             duration: int, aspect: str) -> list[str]:
        """
        HuggingFace Spaces Gradio API — zeroscope Space (always free).
        Uses the Gradio queue API, not the broken Inference API.
        """
        clips = []
        # Working Spaces with Gradio API
        spaces = [
            "https://fffiloni-zeroscope.hf.space",
            "https://hysts-zeroscope-v2.hf.space",
        ]
        hf_token = os.environ.get("HF_TOKEN", "")
        headers = {}
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        for i in range(count):
            space_url = spaces[i % len(spaces)]
            try:
                # Step 1: queue join
                r = requests.post(
                    f"{space_url}/queue/join",
                    headers={**headers, "Content-Type": "application/json"},
                    json={
                        "data": [prompt, 24, 576, 320, 7.5, 50],
                        "fn_index": 0,
                        "session_hash": hashlib.md5(
                            f"{prompt}{i}".encode()
                        ).hexdigest()[:8],
                    },
                    timeout=30,
                )
                if r.status_code != 200:
                    print(f"[HF Gradio] {space_url} join hata: {r.status_code}")
                    continue

                event_id = r.json().get("event_id", "")
                if not event_id:
                    continue

                # Step 2: poll status
                deadline = time.time() + MAX_WAIT
                while time.time() < deadline:
                    status_r = requests.get(
                        f"{space_url}/queue/status",
                        timeout=20,
                    )
                    if status_r.status_code == 200:
                        data = status_r.json()
                        if data.get("status") == "complete":
                            output = data.get("output", {})
                            video_path_remote = (
                                output.get("data", [{}])[0]
                                if output.get("data") else None
                            )
                            if video_path_remote:
                                full_url = f"{space_url}/file={video_path_remote}"
                                path = self._download_video(full_url, f"hf_gradio_{i}")
                                if path:
                                    clips.append(path)
                            break
                    time.sleep(POLL_EVERY)

            except Exception as e:
                print(f"[HF Gradio] {e}")
            time.sleep(3)
        return clips

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: HuggingFace Router (FREE — requires HF_TOKEN) ──────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _huggingface_router(self, prompt: str, count: int,
                             duration: int, aspect: str) -> list[str]:
        """
        HuggingFace Inference Providers router — uses serverless providers.
        Requires HF_TOKEN with at least free tier.
        Working models as of 2025: wan-ai/Wan2.1-T2V-14B via nebius provider
        """
        hf_token = os.environ.get("HF_TOKEN", "")
        if not hf_token:
            print("[HF Router] HF_TOKEN yok, atlanıyor.")
            return []

        clips = []
        # Use the providers endpoint (replaces broken free inference API)
        endpoint = "https://router.huggingface.co/nebius/v1/video/generate"
        headers  = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type":  "application/json",
        }

        for i in range(count):
            try:
                r = requests.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model":  "Wan-AI/Wan2.1-T2V-14B",
                        "prompt": prompt,
                        "num_frames": 81,
                        "fps": 16,
                    },
                    timeout=120,
                )
                if r.status_code == 200:
                    ct = r.headers.get("content-type", "")
                    if "video" in ct or "octet-stream" in ct:
                        path = ASSETS_DIR / f"hf_router_{i}_{int(time.time())}.mp4"
                        with open(path, "wb") as f:
                            f.write(r.content)
                        if path.stat().st_size > 50_000:
                            print(f"[HF Router] [OK] {path.name}")
                            clips.append(str(path))
                else:
                    print(f"[HF Router] {r.status_code}: {r.text[:100]}")
            except Exception as e:
                print(f"[HF Router] {e}")
            time.sleep(5)
        return clips

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: Hailuo / MiniMax Video-01 ──────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _hailuo(self, prompt: str, count: int,
                duration: int, aspect: str) -> list[str]:
        """
        Hailuo AI (MiniMax Video-01) text-to-video.
        Free tier: ~200 credits/day on signup.
        Sign up: https://hailuoai.video  → API → copy key → GitHub Secret HAILUO_API_KEY
        Docs: https://www.minimaxi.chat/document/video-generation
        """
        clips  = []
        BASE   = "https://api.minimaxi.chat/v1"
        headers = {
            "Authorization": f"Bearer {self.hailuo_key}",
            "Content-Type":  "application/json",
        }

        for i in range(count):
            try:
                # ── Submit ──
                r = requests.post(
                    f"{BASE}/video_generation",
                    headers=headers,
                    json={
                        "model":   "video-01",
                        "prompt":  prompt,
                        "prompt_optimizer": True,
                    },
                    timeout=TIMEOUT,
                )
                if r.status_code not in (200, 201):
                    print(f"[Hailuo] Submit hata: {r.status_code} {r.text[:120]}")
                    break

                task_id = r.json().get("task_id", "")
                if not task_id:
                    print("[Hailuo] task_id alınamadı.")
                    break

                # ── Poll ──
                deadline = time.time() + MAX_WAIT
                while time.time() < deadline:
                    p = requests.get(
                        f"{BASE}/query/video_generation",
                        headers=headers,
                        params={"task_id": task_id},
                        timeout=TIMEOUT,
                    )
                    if p.status_code != 200:
                        time.sleep(POLL_EVERY)
                        continue
                    pdata  = p.json()
                    status = pdata.get("status", "")
                    if status == "Success":
                        url = (pdata.get("file_id") and
                               self._hailuo_download_url(pdata["file_id"],
                                                         headers, BASE))
                        if not url:
                            # try direct url field
                            url = pdata.get("video_url", "")
                        if url:
                            path = self._download_video(url, f"hailuo_{i}")
                            if path:
                                clips.append(path)
                                print(f"[Hailuo] [OK] Video {i+1} hazir: {path}")
                        break
                    elif status in ("Fail", "Failed", "error"):
                        print(f"[Hailuo] Task başarısız: {task_id}")
                        break
                    print(f"[Hailuo] Bekleniyor... status={status}")
                    time.sleep(POLL_EVERY)

            except Exception as e:
                print(f"[Hailuo] {e}")
                break
            time.sleep(3)
        return clips

    def _hailuo_download_url(self, file_id: str,
                              headers: dict, base: str) -> str:
        """Retrieve CDN download URL from a Hailuo file_id."""
        try:
            r = requests.get(
                f"{base}/files/retrieve",
                headers=headers,
                params={"file_id": file_id},
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                return r.json().get("file", {}).get("download_url", "")
        except Exception as e:
            print(f"[Hailuo] file retrieve hata: {e}")
        return ""

    # ══════════════════════════════════════════════════════════════════════════
    # ── Provider: Wan 2.2 via HuggingFace Nebius Router (FREE) ───────────────
    # ══════════════════════════════════════════════════════════════════════════
    def _wan22(self, prompt: str, count: int,
               duration: int, aspect: str) -> list[str]:
        """
        Wan 2.2 T2V-14B via HuggingFace Inference Providers (Nebius).
        Requires HF_TOKEN (free account). Significantly better than Wan 2.1.
        Model: Wan-AI/Wan2.2-T2V-14B
        """
        hf_token = os.environ.get("HF_TOKEN", "")
        if not hf_token:
            print("[Wan2.2] HF_TOKEN yok, atlanıyor.")
            return []

        clips    = []
        endpoint = "https://router.huggingface.co/nebius/v1/video/generate"
        headers  = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type":  "application/json",
        }

        for i in range(count):
            try:
                r = requests.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model":      "Wan-AI/Wan2.2-T2V-14B",
                        "prompt":     prompt,
                        "num_frames": 81,
                        "fps":        16,
                        "resolution": "480p",
                        "seed":       int(time.time()) + i,
                    },
                    timeout=180,
                )
                if r.status_code == 200:
                    ct = r.headers.get("content-type", "")
                    if "video" in ct or "octet-stream" in ct:
                        path = ASSETS_DIR / f"wan22_{i}_{int(time.time())}.mp4"
                        with open(path, "wb") as f:
                            f.write(r.content)
                        if path.stat().st_size > 50_000:
                            print(f"[Wan2.2] [OK] {path.name}")
                            clips.append(str(path))
                        else:
                            path.unlink(missing_ok=True)
                else:
                    print(f"[Wan2.2] {r.status_code}: {r.text[:120]}")
            except Exception as e:
                print(f"[Wan2.2] {e}")
            time.sleep(5)
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
