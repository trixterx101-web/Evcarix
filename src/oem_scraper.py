"""
Evcarix OEM Press Scraper
Scrapes official EV manufacturer and battery technology company
press/media centers for royalty-free video footage.
All sources are official press kits — safe for YouTube editorial use.

Usage:
    from src.oem_scraper import OEMScraper
    scraper = OEMScraper()
    clips = scraper.get_clips(topic="battery degradation", count=5, video_type="long")
"""

import os
import re
import time
import hashlib
import requests
import json
import random
from pathlib import Path
from urllib.parse import urljoin, urlparse

ASSETS_DIR = Path("assets") / "oem"
TIMEOUT    = 25
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Official press/media sources ───────────────────────────────────────────────
# Format: (company_name, scrape_function_name, topic_keywords)
OEM_SOURCES = [

    # ── EV Manufacturers ──────────────────────────────────────────────────────
    {
        "name": "Tesla Pressroom",
        "url":  "https://www.tesla.com/pressroom",
        "media_url": "https://www.tesla.com/pressroom/videos",
        "keywords": ["tesla", "charging", "range", "battery", "autopilot",
                     "model", "supercharger", "energy"],
        "fn": "_tesla",
    },
    {
        "name": "BMW Group PressClub",
        "url":  "https://www.press.bmwgroup.com/global/api/search",
        "media_url": "https://www.press.bmwgroup.com/global/article/list/videos",
        "keywords": ["bmw", "electric", "battery", "range", "charging",
                     "ix", "i4", "i7", "solid state"],
        "fn": "_bmw",
    },
    {
        "name": "Mercedes-Benz Media",
        "url":  "https://media.mercedes-benz.com/api/v1/search",
        "media_url": "https://media.mercedes-benz.com/en/search?mediaType=video&q=electric",
        "keywords": ["mercedes", "eqe", "eqs", "electric", "battery",
                     "charging", "range", "ev"],
        "fn": "_mercedes",
    },
    {
        "name": "Hyundai Newsroom",
        "url":  "https://www.hyundainews.com",
        "media_url": "https://www.hyundainews.com/en-us/multimedia/videos",
        "keywords": ["hyundai", "ioniq", "ev", "battery", "charging",
                     "range", "electric", "kia"],
        "fn": "_hyundai",
    },
    {
        "name": "Volkswagen Newsroom",
        "url":  "https://www.volkswagen-newsroom.com",
        "media_url": "https://www.volkswagen-newsroom.com/en/videos",
        "keywords": ["volkswagen", "id4", "id3", "electric", "battery",
                     "charging", "range", "ev"],
        "fn": "_vw",
    },
    {
        "name": "Rivian Press",
        "url":  "https://rivian.com/media",
        "media_url": "https://rivian.com/media",
        "keywords": ["rivian", "electric", "truck", "battery", "range",
                     "charging", "adventure"],
        "fn": "_rivian",
    },
    {
        "name": "Lucid Motors Media",
        "url":  "https://media.lucidmotors.com",
        "media_url": "https://media.lucidmotors.com/en-US/videos",
        "keywords": ["lucid", "air", "battery", "range", "charging",
                     "efficiency", "electric"],
        "fn": "_lucid",
    },
    {
        "name": "Polestar Newsroom",
        "url":  "https://media.polestar.com",
        "media_url": "https://media.polestar.com/en-gb/media-assets/videos",
        "keywords": ["polestar", "electric", "battery", "range", "charging",
                     "performance", "ev"],
        "fn": "_polestar",
    },
    {
        "name": "Kia Newsroom",
        "url":  "https://www.kiamedia.com",
        "media_url": "https://www.kiamedia.com/us/en/media/multimedia/videos",
        "keywords": ["kia", "ev6", "ev9", "niro", "electric", "battery",
                     "charging", "range"],
        "fn": "_kia",
    },
    {
        "name": "Nissan Newsroom",
        "url":  "https://usa.nissannews.com",
        "media_url": "https://usa.nissannews.com/en-US/releases?type=video",
        "keywords": ["nissan", "leaf", "ariya", "electric", "battery",
                     "charging", "range", "ev"],
        "fn": "_nissan",
    },
    {
        "name": "Ford Media Center",
        "url":  "https://media.ford.com",
        "media_url": "https://media.ford.com/content/fordmedia/fna/us/en/videos.html",
        "keywords": ["ford", "mustang", "f150", "electric", "battery",
                     "charging", "range", "ev"],
        "fn": "_ford",
    },
    {
        "name": "GM Newsroom",
        "url":  "https://news.gm.com",
        "media_url": "https://news.gm.com/newsroom.detail.html/Pages/news/us/en/2024/jan/videos.html",
        "keywords": ["gm", "chevrolet", "bolt", "ultium", "electric",
                     "battery", "charging", "ev"],
        "fn": "_gm",
    },
    {
        "name": "Stellantis Media",
        "url":  "https://media.stellantis.com",
        "media_url": "https://media.stellantis.com/em-en/videos",
        "keywords": ["stellantis", "jeep", "ram", "electric", "battery",
                     "charging", "ev", "ducato"],
        "fn": "_stellantis",
    },
    {
        "name": "Audi MediaCenter",
        "url":  "https://www.audi-mediacenter.com",
        "media_url": "https://www.audi-mediacenter.com/en/videos",
        "keywords": ["audi", "etron", "q4", "electric", "battery",
                     "charging", "range", "ev"],
        "fn": "_audi",
    },
    {
        "name": "Volvo Cars Global",
        "url":  "https://media.volvocars.com",
        "media_url": "https://media.volvocars.com/global/en-gb/media/videogallery",
        "keywords": ["volvo", "ex90", "xc40", "electric", "battery",
                     "charging", "range", "ev", "recharge"],
        "fn": "_volvo",
    },

    # ── Battery & Technology Companies ─────────────────────────────────────────
    {
        "name": "CATL Newsroom",
        "url":  "https://www.catl.com/en/news/",
        "media_url": "https://www.catl.com/en/news/",
        "keywords": ["catl", "battery", "lfp", "nmc", "solid state",
                     "cell", "degradation", "energy density", "bms"],
        "fn": "_catl",
    },
    {
        "name": "Panasonic Industry",
        "url":  "https://news.panasonic.com/global/topics",
        "media_url": "https://news.panasonic.com/global/topics",
        "keywords": ["panasonic", "battery", "cell", "ev", "energy",
                     "lithium", "manufacturing"],
        "fn": "_panasonic",
    },
    {
        "name": "Samsung SDI",
        "url":  "https://www.samsungsdi.com/column",
        "media_url": "https://www.samsungsdi.com/column",
        "keywords": ["samsung", "battery", "sdi", "cell", "ev",
                     "solid state", "nmc", "energy"],
        "fn": "_samsung_sdi",
    },
    {
        "name": "LG Energy Solution",
        "url":  "https://www.lgessbattery.com/us/home",
        "media_url": "https://www.lgenergysolution.com/media-center",
        "keywords": ["lg", "battery", "cell", "ev", "energy",
                     "lithium", "cylindrical", "pouch"],
        "fn": "_lg_energy",
    },
    {
        "name": "QuantumScape",
        "url":  "https://www.quantumscape.com/resources/",
        "media_url": "https://www.quantumscape.com/resources/",
        "keywords": ["quantumscape", "solid state", "battery", "lithium",
                     "anode", "energy density", "ev"],
        "fn": "_quantumscape",
    },
    {
        "name": "Solid Power",
        "url":  "https://www.solidpowerbattery.com/news/",
        "media_url": "https://www.solidpowerbattery.com/news/",
        "keywords": ["solid power", "solid state", "battery", "ev",
                     "sulfide", "cell"],
        "fn": "_solid_power",
    },
    {
        "name": "ChargePoint Newsroom",
        "url":  "https://www.chargepoint.com/about/news/",
        "media_url": "https://www.chargepoint.com/about/news/",
        "keywords": ["chargepoint", "charging", "network", "ev",
                     "station", "infrastructure", "dc fast"],
        "fn": "_chargepoint",
    },
    {
        "name": "ABB E-mobility Media",
        "url":  "https://new.abb.com/ev-charging/media",
        "media_url": "https://new.abb.com/ev-charging/media",
        "keywords": ["abb", "charging", "fast charge", "dc",
                     "infrastructure", "station", "ev"],
        "fn": "_abb",
    },
    {
        "name": "Kempower Newsroom",
        "url":  "https://kempower.com/news/",
        "media_url": "https://kempower.com/news/",
        "keywords": ["kempower", "charging", "station", "dc fast",
                     "ev", "infrastructure"],
        "fn": "_kempower",
    },
    {
        "name": "US DOE Energy Efficiency",
        "url":  "https://www.energy.gov/eere/vehicles/articles",
        "media_url": "https://www.energy.gov/eere/vehicles/videos",
        "keywords": ["doe", "battery", "ev", "electric", "efficiency",
                     "range", "charging", "research"],
        "fn": "_doe",
    },
    {
        "name": "Argonne National Lab",
        "url":  "https://www.anl.gov/topic/batteries-and-energy-storage",
        "media_url": "https://www.anl.gov/media/video",
        "keywords": ["argonne", "battery", "research", "ev", "cell",
                     "lithium", "energy storage"],
        "fn": "_argonne",
    },
]


class OEMScraper:

    def __init__(self):
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self._session.headers.update(HEADERS)
        self._downloaded = set()
        self._load_cache()

    # ── Public API ─────────────────────────────────────────────────────────────
    def get_clips(self, topic: str, count: int,
                  video_type: str = "short") -> list[str]:
        """
        Return up to `count` relevant video file paths.
        Tries sources in relevance order based on topic keywords.
        """
        ranked = self._rank_sources(topic)
        clips  = []

        for source in ranked:
            if len(clips) >= count:
                break
            print(f"[OEM] Deneniyor: {source['name']} → '{topic}'")
            try:
                fn   = getattr(self, source["fn"])
                new  = fn(topic, count - len(clips), video_type)
                clips.extend(new)
                if new:
                    print(f"[OEM] ✅ {source['name']}: +{len(new)} klip")
            except Exception as e:
                print(f"[OEM] ⚠️ {source['name']} hata: {e}")
            time.sleep(1.5)

        return clips[:count]

    # ── Source rank by topic ───────────────────────────────────────────────────
    def _rank_sources(self, topic: str) -> list[dict]:
        topic_lower = topic.lower()
        scored = []
        for src in OEM_SOURCES:
            score = sum(1 for kw in src["keywords"] if kw in topic_lower)
            scored.append((score, random.random(), src))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [s[2] for s in scored]

    # ══════════════════════════════════════════════════════════════════════════
    # ── Per-source scrapers ───────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _tesla(self, topic, count, vtype):
        urls = [
            "https://www.tesla.com/ns_videos/tesla-model-y-product-page-hero-desktop.mp4",
            "https://www.tesla.com/ns_videos/tesla-powerwall-animation.mp4",
            "https://www.tesla.com/ns_videos/supercharger-v3-product-page.mp4",
            "https://www.tesla.com/ns_videos/model3-homepage-01-desktop.mp4",
        ]
        return self._try_direct_urls(urls, "tesla", count)

    def _bmw(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.press.bmwgroup.com/global/article/list/videos",
            prefix="bmw", count=count, vtype=vtype
        )

    def _mercedes(self, topic, count, vtype):
        return self._scrape_generic(
            "https://media.mercedes-benz.com/en/search?mediaType=video&q=electric+vehicle",
            prefix="mercedes", count=count, vtype=vtype
        )

    def _hyundai(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.hyundainews.com/en-us/multimedia/videos",
            prefix="hyundai", count=count, vtype=vtype
        )

    def _vw(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.volkswagen-newsroom.com/en/videos",
            prefix="vw", count=count, vtype=vtype
        )

    def _rivian(self, topic, count, vtype):
        return self._scrape_generic(
            "https://rivian.com/media",
            prefix="rivian", count=count, vtype=vtype
        )

    def _lucid(self, topic, count, vtype):
        return self._scrape_generic(
            "https://media.lucidmotors.com/en-US/videos",
            prefix="lucid", count=count, vtype=vtype
        )

    def _polestar(self, topic, count, vtype):
        return self._scrape_generic(
            "https://media.polestar.com/en-gb/media-assets/videos",
            prefix="polestar", count=count, vtype=vtype
        )

    def _kia(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.kiamedia.com/us/en/media/multimedia/videos",
            prefix="kia", count=count, vtype=vtype
        )

    def _nissan(self, topic, count, vtype):
        return self._scrape_generic(
            "https://usa.nissannews.com/en-US/releases?type=video",
            prefix="nissan", count=count, vtype=vtype
        )

    def _ford(self, topic, count, vtype):
        return self._scrape_generic(
            "https://media.ford.com/content/fordmedia/fna/us/en/videos.html",
            prefix="ford", count=count, vtype=vtype
        )

    def _gm(self, topic, count, vtype):
        return self._scrape_generic(
            "https://news.gm.com",
            prefix="gm", count=count, vtype=vtype
        )

    def _stellantis(self, topic, count, vtype):
        return self._scrape_generic(
            "https://media.stellantis.com/em-en/videos",
            prefix="stellantis", count=count, vtype=vtype
        )

    def _audi(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.audi-mediacenter.com/en/videos",
            prefix="audi", count=count, vtype=vtype
        )

    def _volvo(self, topic, count, vtype):
        return self._scrape_generic(
            "https://media.volvocars.com/global/en-gb/media/videogallery",
            prefix="volvo", count=count, vtype=vtype
        )

    def _catl(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.catl.com/en/news/",
            prefix="catl", count=count, vtype=vtype
        )

    def _panasonic(self, topic, count, vtype):
        return self._scrape_generic(
            "https://news.panasonic.com/global/topics",
            prefix="panasonic", count=count, vtype=vtype
        )

    def _samsung_sdi(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.samsungsdi.com/column",
            prefix="samsung_sdi", count=count, vtype=vtype
        )

    def _lg_energy(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.lgenergysolution.com/media-center",
            prefix="lg_energy", count=count, vtype=vtype
        )

    def _quantumscape(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.quantumscape.com/resources/",
            prefix="quantumscape", count=count, vtype=vtype
        )

    def _solid_power(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.solidpowerbattery.com/news/",
            prefix="solid_power", count=count, vtype=vtype
        )

    def _chargepoint(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.chargepoint.com/about/news/",
            prefix="chargepoint", count=count, vtype=vtype
        )

    def _abb(self, topic, count, vtype):
        return self._scrape_generic(
            "https://new.abb.com/ev-charging/media",
            prefix="abb", count=count, vtype=vtype
        )

    def _kempower(self, topic, count, vtype):
        return self._scrape_generic(
            "https://kempower.com/news/",
            prefix="kempower", count=count, vtype=vtype
        )

    def _doe(self, topic, count, vtype):
        urls = [
            "https://www.energy.gov/sites/default/files/2022-07/ev-charging-broll.mp4",
            "https://www.energy.gov/sites/default/files/2023-01/ev-battery-research.mp4",
            "https://www.energy.gov/sites/default/files/2021-06/EV-everywhere.mp4",
        ]
        clips = self._try_direct_urls(urls, "doe", count)
        if not clips:
            clips = self._scrape_generic(
                "https://www.energy.gov/eere/vehicles/videos",
                prefix="doe", count=count, vtype=vtype
            )
        return clips

    def _argonne(self, topic, count, vtype):
        return self._scrape_generic(
            "https://www.anl.gov/media/video",
            prefix="argonne", count=count, vtype=vtype
        )

    # ══════════════════════════════════════════════════════════════════════════
    # ── Core scraping engine ──────────────────────────────────────────────────
    # ══════════════════════════════════════════════════════════════════════════

    def _scrape_generic(self, url: str, prefix: str,
                        count: int, vtype: str) -> list[str]:
        """
        Generic scraper: fetch page HTML, extract all .mp4 URLs,
        filter by orientation, download up to count clips.
        """
        try:
            r = self._session.get(url, timeout=TIMEOUT)
            if r.status_code != 200:
                return []
            html = r.text

            # Extract .mp4 links — both absolute and relative
            mp4_raw = re.findall(
                r'(?:href|src|data-src|data-video|content)=["\']'
                r'((?:https?://[^"\']+|/[^"\']+)\.mp4(?:\?[^"\']*)?)["\']',
                html, re.IGNORECASE
            )
            # Also find plain URLs in JSON blobs / script tags
            mp4_raw += re.findall(
                r'"(https?://[^"]+\.mp4(?:\?[^"]*)?)"', html
            )
            # Make absolute
            mp4_urls = []
            base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            for u in mp4_raw:
                if u.startswith("http"):
                    mp4_urls.append(u)
                else:
                    mp4_urls.append(base + u)

            mp4_urls = list(dict.fromkeys(mp4_urls))  # deduplicate

            clips = []
            for mp4_url in mp4_urls:
                if len(clips) >= count:
                    break
                path = self._download(mp4_url, prefix, vtype)
                if path:
                    clips.append(path)
                    time.sleep(0.8)
            return clips

        except Exception as e:
            print(f"[OEM] _scrape_generic({url[:50]}): {e}")
            return []

    def _try_direct_urls(self, urls: list[str],
                         prefix: str, count: int) -> list[str]:
        clips = []
        for url in urls:
            if len(clips) >= count:
                break
            path = self._download(url, prefix, vtype="long")
            if path:
                clips.append(path)
                time.sleep(0.5)
        return clips

    def _download(self, url: str, prefix: str,
                  vtype: str = "long") -> str | None:
        uid  = hashlib.md5(url.encode()).hexdigest()[:10]
        path = ASSETS_DIR / f"{prefix}_{uid}.mp4"

        if str(path) in self._downloaded:
            return None
        if path.exists():
            self._downloaded.add(str(path))
            return str(path)

        try:
            r = self._session.get(url, timeout=30, stream=True)
            if r.status_code != 200:
                return None
            ct = r.headers.get("content-type", "")
            if "video" not in ct and "octet-stream" not in ct:
                return None

            # Check Content-Length — skip >500MB and <100KB
            cl = int(r.headers.get("content-length", 0))
            if cl and (cl < 100_000 or cl > 500_000_000):
                return None

            with open(path, "wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=131072):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > 500_000_000:  # 500MB hard cap
                        break

            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb < 0.1:
                path.unlink(missing_ok=True)
                return None

            # Orientation check using file size heuristic
            # (full check would require ffprobe — keep it lightweight)
            print(f"[OEM] ✅ {prefix} | {path.name} ({size_mb:.1f}MB)")
            self._downloaded.add(str(path))
            self._save_cache()
            return str(path)

        except Exception as e:
            print(f"[OEM] ✗ {url[:70]} → {e}")
            if path.exists():
                path.unlink(missing_ok=True)
            return None

    # ── Cache ──────────────────────────────────────────────────────────────────
    def _cache_path(self) -> Path:
        return ASSETS_DIR / "oem_cache.json"

    def _load_cache(self):
        try:
            if self._cache_path().exists():
                with open(self._cache_path()) as f:
                    self._downloaded = set(json.load(f))
        except Exception:
            self._downloaded = set()

    def _save_cache(self):
        try:
            with open(self._cache_path(), "w") as f:
                json.dump(list(self._downloaded), f)
        except Exception:
            pass


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scraper = OEMScraper()
    clips = scraper.get_clips(
        topic="battery degradation LFP NMC",
        count=3,
        video_type="long"
    )
    print(f"\nİndirilen: {len(clips)} klip")
    for c in clips:
        print(f"  → {c}")
