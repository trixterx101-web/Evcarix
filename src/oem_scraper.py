"""
Evcarix OEM Press Scraper
Fetches video clips ONLY from official Press/Newsroom/Media pages.
Editorial use only — never commercial product pages or ads.
Sources: Tesla, BMW, Hyundai, VW, Kia, Volvo, Polestar,
         CATL, Panasonic, DOE, Argonne, ChargePoint, ABB
"""

import os
import re
import time
import json
import hashlib
import requests
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

# ── Official Press/Newsroom pages ONLY ────────────────────────────────────────
# These are editorially open pages — no product ads, no commercials
OEM_PRESS_SOURCES = [

    # ── EV Manufacturers — Press/Newsroom only ────────────────────────────────
    {
        "name":     "Tesla Pressroom Videos",
        "url":      "https://www.tesla.com/pressroom/videos",
        "base":     "https://www.tesla.com",
        "keywords": ["tesla", "charging", "range", "battery", "model",
                     "supercharger", "energy", "ev", "electric"],
    },
    {
        "name":     "BMW Group PressClub Video",
        "url":      "https://www.press.bmwgroup.com/global/article/list/videos",
        "base":     "https://www.press.bmwgroup.com",
        "keywords": ["bmw", "electric", "battery", "range", "charging",
                     "ix", "i4", "ev", "drive"],
    },
    {
        "name":     "Hyundai Newsroom Multimedia",
        "url":      "https://www.hyundainews.com/en-us/multimedia/videos",
        "base":     "https://www.hyundainews.com",
        "keywords": ["hyundai", "ioniq", "ev", "battery", "charging",
                     "range", "electric"],
    },
    {
        "name":     "Volkswagen Newsroom Videos",
        "url":      "https://www.volkswagen-newsroom.com/en/videos-3606",
        "base":     "https://www.volkswagen-newsroom.com",
        "keywords": ["volkswagen", "vw", "id4", "id3", "electric",
                     "battery", "charging", "ev"],
    },
    {
        "name":     "Kia Media Videos",
        "url":      "https://www.kiamedia.com/us/en/media/multimedia/videos",
        "base":     "https://www.kiamedia.com",
        "keywords": ["kia", "ev6", "ev9", "niro", "electric", "battery",
                     "charging", "range"],
    },
    {
        "name":     "Volvo Cars Media Video Gallery",
        "url":      "https://media.volvocars.com/global/en-gb/media/videogallery",
        "base":     "https://media.volvocars.com",
        "keywords": ["volvo", "electric", "battery", "recharge", "charging",
                     "range", "ev", "ex"],
    },
    {
        "name":     "Polestar Media Assets",
        "url":      "https://media.polestar.com/en-gb/media-assets/videos",
        "base":     "https://media.polestar.com",
        "keywords": ["polestar", "electric", "battery", "range", "charging",
                     "ev", "performance"],
    },
    {
        "name":     "Mercedes-Benz Media Electric",
        "url":      "https://media.mercedes-benz.com/en/search?q=electric+vehicle&mediaType=video",
        "base":     "https://media.mercedes-benz.com",
        "keywords": ["mercedes", "eqs", "eqe", "electric", "battery",
                     "charging", "range"],
    },
    {
        "name":     "Audi MediaCenter Videos",
        "url":      "https://www.audi-mediacenter.com/en/videos",
        "base":     "https://www.audi-mediacenter.com",
        "keywords": ["audi", "etron", "q4", "electric", "battery",
                     "charging", "range", "ev"],
    },
    {
        "name":     "Ford Media Center EV Videos",
        "url":      "https://media.ford.com/content/fordmedia/fna/us/en/videos.html",
        "base":     "https://media.ford.com",
        "keywords": ["ford", "mustang", "lightning", "f150", "electric",
                     "battery", "charging", "ev"],
    },
    {
        "name":     "Rivian Media",
        "url":      "https://rivian.com/media",
        "base":     "https://rivian.com",
        "keywords": ["rivian", "electric", "truck", "battery", "range",
                     "charging", "r1t", "r1s"],
    },
    {
        "name":     "Lucid Motors Media Videos",
        "url":      "https://media.lucidmotors.com/en-US/videos",
        "base":     "https://media.lucidmotors.com",
        "keywords": ["lucid", "air", "battery", "range", "charging",
                     "efficiency", "electric"],
    },
    {
        "name":     "Nissan Newsroom Video",
        "url":      "https://usa.nissannews.com/en-US/releases?type=video",
        "base":     "https://usa.nissannews.com",
        "keywords": ["nissan", "ariya", "leaf", "electric", "battery",
                     "ev", "charging", "range"],
    },

    # ── Battery & Technology — Press only ─────────────────────────────────────
    {
        "name":     "CATL Official News",
        "url":      "https://www.catl.com/en/news/",
        "base":     "https://www.catl.com",
        "keywords": ["catl", "battery", "lfp", "nmc", "solid state",
                     "cell", "energy density", "ev"],
    },
    {
        "name":     "Panasonic News Energy",
        "url":      "https://news.panasonic.com/global/topics/tag/energy",
        "base":     "https://news.panasonic.com",
        "keywords": ["panasonic", "battery", "cell", "ev", "energy",
                     "lithium", "4680"],
    },
    {
        "name":     "Samsung SDI News",
        "url":      "https://www.samsungsdi.com/column/all.html",
        "base":     "https://www.samsungsdi.com",
        "keywords": ["samsung", "sdi", "battery", "cell", "ev",
                     "solid state", "nmc"],
    },
    {
        "name":     "QuantumScape Resources",
        "url":      "https://www.quantumscape.com/resources/",
        "base":     "https://www.quantumscape.com",
        "keywords": ["quantumscape", "solid state", "battery", "lithium",
                     "anode", "ev"],
    },

    # ── Charging Infrastructure — Press only ──────────────────────────────────
    {
        "name":     "ChargePoint Newsroom",
        "url":      "https://www.chargepoint.com/about/news/",
        "base":     "https://www.chargepoint.com",
        "keywords": ["chargepoint", "charging", "network", "ev",
                     "station", "dc fast", "infrastructure"],
    },
    {
        "name":     "ABB E-mobility Media",
        "url":      "https://new.abb.com/ev-charging/media",
        "base":     "https://new.abb.com",
        "keywords": ["abb", "charging", "fast charge", "dc",
                     "infrastructure", "station", "ev"],
    },

    # ── Research & Government — Public domain ─────────────────────────────────
    {
        "name":     "US DOE Vehicles Videos",
        "url":      "https://www.energy.gov/eere/vehicles/videos",
        "base":     "https://www.energy.gov",
        "keywords": ["battery", "ev", "electric", "efficiency", "range",
                     "charging", "research", "energy"],
    },
    {
        "name":     "Argonne National Lab Media",
        "url":      "https://www.anl.gov/media/video",
        "base":     "https://www.anl.gov",
        "keywords": ["argonne", "battery", "research", "ev", "cell",
                     "lithium", "energy storage"],
    },
]

# ── Relevance scoring ──────────────────────────────────────────────────────────
# Topic keywords that must appear in either filename or page context
# to be considered relevant — rejects unrelated footage
TOPIC_RELEVANCE_KEYWORDS = {
    "battery":        ["battery", "cell", "lfp", "nmc", "pack", "cathode",
                       "anode", "degradation", "bms", "solid", "lithium"],
    "range":          ["range", "mileage", "efficiency", "highway", "winter",
                       "consumption", "kwh", "driving", "road"],
    "charging":       ["charging", "charger", "plug", "connector", "dc",
                       "fast", "supercharger", "station", "cable"],
    "ownership":      ["cost", "price", "ownership", "maintenance", "value",
                       "depreciation", "insurance", "savings"],
    "comparison":     ["compare", "versus", "lineup", "test", "benchmark",
                       "segment", "class", "ranking"],
    "market":         ["sales", "market", "adoption", "growth", "global",
                       "percent", "share", "trend"],
    "infrastructure": ["infrastructure", "grid", "station", "network",
                       "installation", "apartment", "solar", "smart"],
    "education":      ["motor", "inverter", "heat pump", "thermal", "drag",
                       "aerodynamic", "regenerative", "explained"],
    "tools":          ["data", "chart", "graph", "calculator", "analysis",
                       "visualization", "dashboard", "metrics"],
}


class OEMScraper:

    def __init__(self):
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        self._session = requests.Session()
        self._session.headers.update(HEADERS)
        self._downloaded = set()
        self._load_cache()

    # ── Public API ─────────────────────────────────────────────────────────────
    def get_clips(self, topic: str, category_id: str = "",
                  count: int = 3, video_type: str = "short") -> list[str]:
        """
        Fetch up to `count` relevant press video clips.
        Only returns clips that pass topic relevance check.
        """
        ranked  = self._rank_sources(topic, category_id)
        clips   = []
        rel_kws = self._get_relevance_keywords(category_id, topic)

        for source in ranked:
            if len(clips) >= count:
                break
            print(f"[OEM] {source['name']} deneniyor...")
            try:
                new = self._scrape_press_page(
                    url       = source["url"],
                    base      = source["base"],
                    prefix    = re.sub(r"\W+", "_", source["name"])[:20],
                    count     = count - len(clips),
                    video_type= video_type,
                    rel_kws   = rel_kws,
                )
                clips.extend(new)
                if new:
                    print(f"[OEM] ✅ {source['name']}: +{len(new)} klip")
            except Exception as e:
                print(f"[OEM] ⚠️ {source['name']}: {e}")
            time.sleep(1.5)

        return clips[:count]

    # ── Source ranking ─────────────────────────────────────────────────────────
    def _rank_sources(self, topic: str, category_id: str) -> list[dict]:
        combined = (topic + " " + category_id).lower()
        scored   = []
        for src in OEM_PRESS_SOURCES:
            score = sum(1 for kw in src["keywords"] if kw in combined)
            scored.append((score, random.random(), src))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [s[2] for s in scored]

    def _get_relevance_keywords(self, category_id: str, topic: str) -> list[str]:
        base = TOPIC_RELEVANCE_KEYWORDS.get(
            category_id,
            TOPIC_RELEVANCE_KEYWORDS.get("range", [])
        )
        # Add words from topic string itself
        extra = [w for w in re.split(r"\W+", topic.lower()) if len(w) > 3]
        return list(set(base + extra))

    # ── Core press page scraper ────────────────────────────────────────────────
    def _scrape_press_page(self, url: str, base: str, prefix: str,
                           count: int, video_type: str,
                           rel_kws: list[str]) -> list[str]:
        """
        Fetch press page HTML, extract all .mp4 URLs.
        """
        try:
            # Handle SSL issues for specific domains (Samsung SDI etc.)
            verify_ssl = "samsungsdi.com" not in url
            r = self._session.get(url, timeout=TIMEOUT, allow_redirects=True, verify=verify_ssl)
            if r.status_code != 200:
                return []
            html = r.text
        except Exception:
            return []

        # Extract mp4 URLs from HTML
        patterns = [
            r'(?:href|src|data-src|data-video|content|url)[=:]\s*["\']?((?:https?://[^\s"\'<>]+|/[^\s"\'<>]+)\.mp4(?:\?[^\s"\'<>]*)?)["\']?',
            r'"(https?://[^"]+\.mp4[^"]*)"',
            r"'(https?://[^']+\.mp4[^']*)'",
        ]
        raw = []
        for p in patterns:
            raw += re.findall(p, html, re.IGNORECASE)

        # Make absolute URLs
        mp4_urls = []
        for u in raw:
            u = u.split('"')[0].split("'")[0].strip()
            if u.startswith("//"):
                mp4_urls.append("https:" + u)
            elif u.startswith("http"):
                mp4_urls.append(u)
            elif u.startswith("/"):
                mp4_urls.append(base.rstrip("/") + u)
        mp4_urls = list(dict.fromkeys(mp4_urls))

        # Filter out clearly irrelevant URLs
        mp4_urls = [
            u for u in mp4_urls
            if not any(bad in u.lower() for bad in [
                "ad_", "advertisement", "commercial", "promo_",
                "thumbnail", "poster", "preview_img", "logo",
            ])
        ]

        clips = []
        for mp4_url in mp4_urls:
            if len(clips) >= count:
                break

            # Topic relevance check on URL itself
            url_lower = mp4_url.lower()
            is_relevant = any(kw in url_lower for kw in rel_kws)
            # If URL gives no signal, allow it (page is already topic-filtered)
            if not is_relevant and len(rel_kws) > 0:
                # Check if it at least matches EV general terms
                ev_terms = ["electric", "ev", "battery", "charg",
                            "range", "motor", "vehicle"]
                is_relevant = any(t in url_lower for t in ev_terms)

            if not is_relevant:
                continue

            # Orientation check (skip tiny/non-video files at URL level)
            if any(skip in url_lower for skip in ["_thumb", "_poster",
                                                   "480p", "240p", "144p"]):
                continue

            path = self._download(mp4_url, prefix, video_type)
            if path:
                clips.append(path)
                time.sleep(1.0)

        return clips

    # ── Download ───────────────────────────────────────────────────────────────
    def _download(self, url: str, prefix: str,
                  video_type: str = "long") -> str | None:
        uid  = hashlib.md5(url.encode()).hexdigest()[:10]
        path = ASSETS_DIR / f"{prefix}_{uid}.mp4"

        if str(path) in self._downloaded:
            return None
        if path.exists() and path.stat().st_size > 100_000:
            self._downloaded.add(str(path))
            return str(path)

        try:
            r = self._session.get(url, timeout=30, stream=True)
            if r.status_code != 200:
                return None

            ct = r.headers.get("content-type", "")
            if "video" not in ct and "octet-stream" not in ct:
                return None

            cl = int(r.headers.get("content-length", 0))
            if cl and (cl < 200_000 or cl > 400_000_000):
                return None

            with open(path, "wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=131072):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > 400_000_000:
                        break

            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb < 0.2:
                path.unlink(missing_ok=True)
                return None

            print(f"[OEM] ✅ {path.name} ({size_mb:.1f}MB)")
            self._downloaded.add(str(path))
            self._save_cache()
            return str(path)

        except Exception as e:
            print(f"[OEM] ✗ {url[:70]}: {e}")
            if path.exists():
                path.unlink(missing_ok=True)
            return None

    # ── Description watermark check ────────────────────────────────────────────
    def _has_watermark_risk(self, url: str) -> bool:
        """Skip URLs that likely contain watermarked/branded content."""
        risky = ["_ad_", "commercial", "advertisement",
                 "branded", "sponsor", "promo"]
        return any(r in url.lower() for r in risky)

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
    tests = [
        ("battery degradation LFP NMC", "battery"),
        ("fast charging 800V vs 400V",  "charging"),
        ("winter range loss cold",      "range"),
    ]
    for topic, cat in tests:
        print(f"\n--- {topic} ---")
        clips = scraper.get_clips(
            topic=topic, category_id=cat, count=2, video_type="long"
        )
        for c in clips:
            print(f"  → {c}")
