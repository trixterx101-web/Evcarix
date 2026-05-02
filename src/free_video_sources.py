"""
Evcarix Free Video Sources — no API key required
All sources are copyright-free / CC0 / public domain.
Downloads landscape (16:9) HD video clips relevant to EV topics.
"""

import os
import re
import time
import random
import hashlib
import requests
from pathlib import Path

ASSETS_DIR = Path("assets")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Evcarix/1.0)"}
TIMEOUT = 20

# ── EV-related search terms per category ──────────────────────────────────────
EV_SEARCH_TERMS = [
    "electric car", "electric vehicle charging", "battery technology",
    "solar energy", "wind turbine energy", "highway driving",
    "city traffic", "dashboard display", "technology data",
    "factory automation", "circuit board", "power grid",
    "road driving", "car interior", "speedometer gauge",
]


class FreeVideoSources:

    def __init__(self):
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self._used = set()

    def download_clips(self, query: str, count: int, video_type: str = "short") -> list[str]:
        """
        Try all free sources in order until enough clips are collected.
        Returns list of downloaded file paths.
        """
        clips = []
        sources = [
            self._coverr,
            self._videvo,
            self._mixkit,
            self._videezy_free,
            self._ignitemotion,
            self._dareful,
        ]
        random.shuffle(sources)

        for source_fn in sources:
            if len(clips) >= count:
                break
            try:
                new = source_fn(query, count - len(clips), video_type)
                clips.extend(new)
                print(f"[FreeVideo] {source_fn.__name__}: +{len(new)} klip")
            except Exception as e:
                print(f"[FreeVideo] {source_fn.__name__} hata: {e}")

        return clips[:count]

    # ── Source 1: Coverr.co (CC0, no key) ────────────────────────────────────
    def _coverr(self, query: str, count: int, video_type: str) -> list[str]:
        paths = []
        terms = query.replace(" ", "+")
        url = f"https://coverr.co/api/videos/search?query={terms}&page=1&per_page=20"
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        data = r.json()
        videos = data.get("hits", data.get("videos", []))
        for v in videos:
            if len(paths) >= count:
                break
            # try mp4 url fields
            mp4_url = (
                v.get("urls", {}).get("mp4") or
                v.get("mp4_url") or
                v.get("download_url") or ""
            )
            if not mp4_url:
                continue
            # check orientation
            w = v.get("width", 1920)
            h = v.get("height", 1080)
            if not self._orientation_ok(w, h, video_type):
                continue
            path = self._download_file(mp4_url, f"coverr_{self._slug(query)}")
            if path:
                paths.append(path)
                time.sleep(0.5)
        return paths

    # ── Source 2: Videvo (free tier, no key for CC0) ──────────────────────────
    def _videvo(self, query: str, count: int, video_type: str) -> list[str]:
        paths = []
        terms = query.replace(" ", "%20")
        url = (
            f"https://www.videvo.net/api/search-videos/"
            f"?search_query={terms}&licence=cc0&content_type=footage&per_page=20"
        )
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        data = r.json()
        for v in data.get("results", []):
            if len(paths) >= count:
                break
            mp4_url = v.get("preview_url", "") or v.get("clip_url", "")
            if not mp4_url or not mp4_url.endswith(".mp4"):
                continue
            w = v.get("width", 1920)
            h = v.get("height", 1080)
            if not self._orientation_ok(w, h, video_type):
                continue
            path = self._download_file(mp4_url, f"videvo_{self._slug(query)}")
            if path:
                paths.append(path)
                time.sleep(0.5)
        return paths

    # ── Source 3: Mixkit (free, no key) ──────────────────────────────────────
    def _mixkit(self, query: str, count: int, video_type: str) -> list[str]:
        """
        Mixkit free assets — scrape the public JSON feed.
        URL pattern: https://mixkit.co/free-stock-video/<term>/
        """
        paths = []
        terms = query.replace(" ", "-").lower()
        url = f"https://mixkit.co/free-stock-video/{terms}/"
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        # find JSON-LD or video src tags
        mp4_urls = re.findall(r'https://[^"]+\.mp4[^"]*', r.text)
        mp4_urls = list(dict.fromkeys(mp4_urls))  # deduplicate
        for mp4_url in mp4_urls:
            if len(paths) >= count:
                break
            if "preview" not in mp4_url and "download" not in mp4_url:
                continue
            path = self._download_file(mp4_url, f"mixkit_{self._slug(query)}")
            if path:
                paths.append(path)
                time.sleep(0.5)
        return paths

    # ── Source 4: Videezy free tier (no key for free clips) ──────────────────
    def _videezy_free(self, query: str, count: int, video_type: str) -> list[str]:
        paths = []
        terms = query.replace(" ", "+")
        url = f"https://www.videezy.com/free-video/{terms}?filters=free"
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        mp4_urls = re.findall(r'https://[^"]+\.mp4[^"]*', r.text)
        mp4_urls = [u for u in dict.fromkeys(mp4_urls) if "free" in u.lower() or "preview" in u.lower()]
        for mp4_url in mp4_urls[:count * 3]:
            if len(paths) >= count:
                break
            path = self._download_file(mp4_url, f"videezy_{self._slug(query)}")
            if path:
                paths.append(path)
                time.sleep(0.5)
        return paths

    # ── Source 5: IgniteMotion (free motion backgrounds, CC0) ────────────────
    def _ignitemotion(self, query: str, count: int, video_type: str) -> list[str]:
        """
        IgniteMotion free motion backgrounds — technology/data/abstract.
        Good for EV data visualization overlays.
        Direct mp4 links, no auth needed.
        """
        paths = []
        base = "https://www.ignitemotion.com"
        url  = f"{base}/free-motion-backgrounds/"
        r    = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        mp4_urls = re.findall(r'href="(/[^"]+\.mp4)"', r.text)
        for rel in mp4_urls[:count * 2]:
            if len(paths) >= count:
                break
            full = base + rel
            path = self._download_file(full, f"ignitemotion_{self._slug(query)}")
            if path:
                paths.append(path)
                time.sleep(0.3)
        return paths

    # ── Source 6: Dareful (4K CC0 videos) ────────────────────────────────────
    def _dareful(self, query: str, count: int, video_type: str) -> list[str]:
        """
        Dareful.com — free 4K CC0 videos, no registration needed.
        """
        paths = []
        terms = query.replace(" ", "+")
        url   = f"https://www.dareful.com/?s={terms}"
        r     = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return []
        mp4_urls = re.findall(r'https://[^"]+\.mp4[^"]*', r.text)
        mp4_urls = list(dict.fromkeys(mp4_urls))
        for mp4_url in mp4_urls:
            if len(paths) >= count:
                break
            path = self._download_file(mp4_url, f"dareful_{self._slug(query)}")
            if path:
                paths.append(path)
                time.sleep(0.5)
        return paths

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _orientation_ok(self, w: int, h: int, video_type: str) -> bool:
        if video_type == "long":
            return w >= h        # landscape OK
        else:
            return h > w         # portrait OK

    def _slug(self, query: str) -> str:
        return re.sub(r"[^\w]", "_", query[:30])

    def _download_file(self, url: str, prefix: str) -> str | None:
        uid  = hashlib.md5(url.encode()).hexdigest()[:8]
        path = ASSETS_DIR / f"{prefix}_{uid}.mp4"
        if path.exists():
            return str(path)
        try:
            r = requests.get(url, headers=HEADERS, timeout=30, stream=True)
            if r.status_code != 200:
                return None
            content_type = r.headers.get("content-type", "")
            if "video" not in content_type and "octet" not in content_type:
                return None
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb < 0.2:   # skip tiny/corrupt files
                path.unlink()
                return None
            print(f"[FreeVideo] ✅ {path.name} ({size_mb:.1f}MB)")
            return str(path)
        except Exception as e:
            print(f"[FreeVideo] ✗ {url[:60]} → {e}")
            if path.exists():
                path.unlink()
            return None
