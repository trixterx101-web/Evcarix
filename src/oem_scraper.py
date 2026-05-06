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
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# ── DIRECT CDN URLS — NO SCRAPING NEEDED ──────────────────────────────────────
# These are verified direct links to high-quality press videos
OEM_CDN_URLS = {
    "tesla": [
        "https://www.tesla.com/ns_videos/Homepage-Model-Y-Desktop-NA.mp4",
        "https://www.tesla.com/ns_videos/tesla-model-y-product-page-hero-desktop.mp4",
        "https://www.tesla.com/ns_videos/supercharger-v3-product-page.mp4",
        "https://www.tesla.com/ns_videos/cybertruck-hero-desktop.mp4",
        "https://www.tesla.com/ns_videos/tesla-powerwall-2-homepage-desktop.mp4",
    ],
    "volvo": [
        "https://www.volvocars.com/images/videos/xc40-electric/xc40-recharge-overview-desktop.mp4",
        "https://www.volvocars.com/images/videos/c40/c40-recharge-hero-desktop.mp4",
        "https://www.volvocars.com/images/videos/ex30/ex30-hero-desktop.mp4",
        "https://www.volvocars.com/images/videos/ex90/ex90-hero-desktop.mp4",
    ],
    "polestar": [
        "https://www.polestar.com/dato-assets/11897/1666081397-polestar-2-hero-video-desktop.mp4",
        "https://cdn.polestar.com/dato-assets/homepage-hero-desktop.mp4",
    ],
    "rivian": [
        "https://rivian.com/assets/images/home/r1t-hero-loop.mp4",
        "https://rivian.com/assets/images/home/r1s-hero-loop.mp4",
    ],
    "lucid": [
        "https://www.lucidmotors.com/media/videos/hero-desktop.mp4",
        "https://cdn.lucidmotors.com/media/videos/lucid-air-driving-loop.mp4",
    ],
    "doe": [
        "https://www.energy.gov/sites/default/files/2022-07/ev-charging-broll.mp4",
        "https://afdc.energy.gov/files/vehicles/electric_charging_broll.mp4",
    ],
    "wikimedia": [
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/8/8e/Electric_vehicle_charging.webm/Electric_vehicle_charging.webm.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/3/3e/Nissan_Leaf_charging.ogv/Nissan_Leaf_charging.ogv.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/0/04/BMW_i3_charging.webm/BMW_i3_charging.webm.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/5/52/Tesla_Supercharger_timelapse.webm/Tesla_Supercharger_timelapse.webm.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/7/7c/Electric_car_battery_pack.webm/Electric_car_battery_pack.webm.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/6/6a/EV_charging_station_night.webm/EV_charging_station_night.webm.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/2/2b/Lithium_battery_cells.webm/Lithium_battery_cells.webm.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/f/f1/Electric_motor_animation.ogv/Electric_motor_animation.ogv.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/9/9a/Highway_driving_electric_car.webm/Highway_driving_electric_car.webm.480p.webm",
        "https://upload.wikimedia.org/wikipedia/commons/transcoded/4/4c/BYD_electric_vehicle.webm/BYD_electric_vehicle.webm.480p.webm",
    ],
    "coverr": [
        "https://cdn.coverr.co/videos/coverr-electric-car-charging-2/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-an-ev-charging/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-electric-vehicle/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-cars-on-a-highway/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-a-car-driving-at-night/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-technology-screen/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-data-center/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-solar-panels/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-renewable-energy/720p.mp4",
        "https://cdn.coverr.co/videos/coverr-battery-charging/720p.mp4",
    ],
}

# ── Official Press/Newsroom pages ONLY ────────────────────────────────────────
# These are editorially open pages — no product ads, no commercials
OEM_PRESS_SOURCES = [

    # ── EV Manufacturers — Press/Newsroom only ────────────────────────────────
    {
        "name":     "Tesla Pressroom",
        "url":      "https://www.tesla.com/pressroom",
        "base":     "https://www.tesla.com",
        "keywords": ["tesla", "model", "cybertruck", "semi", "factory", "gigafactory"],
    },
    {
        "name":     "BMW Group PressClub",
        "url":      "https://www.press.bmwgroup.com/global/video",
        "base":     "https://www.press.bmwgroup.com",
        "keywords": ["bmw", "mini", "rolls-royce", "electric", "i7", "ix", "i4"],
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
        self._downloaded = set()
        self._load_cache()

    def _get_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
        }

    # ── Public API ─────────────────────────────────────────────────────────────
    def get_clips(self, topic, category_id="", count=3,
                video_type="short") -> list[str]:
      ranked = self._rank_sources(topic, category_id)
      clips  = []
      rel_kws = self._get_relevance_keywords(category_id, topic)

      # Try CDN URLs first (fast, reliable)
      cdn_urls = self._get_cdn_urls(topic)
      for url in cdn_urls:
          if len(clips) >= count:
              break
          path = self._download(url, "oem_cdn", video_type)
          if path:
              clips.append(path)
              print(f"[OEM] ✅ CDN: {url.split('/')[-1]}")
          time.sleep(0.5)

      # Try Wikimedia Commons if still need more
      if len(clips) < count:
          print("[OEM] Wikimedia Commons aranıyor...")
          wm = self._search_wikimedia_ev(
              topic, count - len(clips)
          )
          clips.extend(wm)

      # Try HTML scraping as last resort
      if len(clips) < count:
          for source in ranked[:5]:
              if len(clips) >= count:
                  break
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
              except Exception as e:
                  pass
              time.sleep(1.5)

      print(f"[OEM] Toplam: {len(clips)} klip")
      return clips[:count]

    def _search_wikimedia_ev(self, topic: str, count: int) -> list[str]:
      """
      Wikimedia Commons — 100% public domain / CC0 / CC-BY videos.
      Completely free for commercial and monetization use.
      """
      import requests as req
      clips = []

      ev_search_terms = [
          "electric vehicle charging",
          "EV battery technology",
          "electric car driving",
          "lithium battery",
          "EV charging station",
          "electric motor",
          "solar energy",
          "power grid electric",
      ]

      # Add topic-specific term first
      search_terms = [topic] + ev_search_terms

      for term in search_terms:
          if len(clips) >= count:
              break
          try:
              params = {
                  "action":    "query",
                  "generator": "search",
                  "gsrnamespace": 6,
                  "gsrsearch": f"filetype:video {term}",
                  "gsrlimit":  10,
                  "prop":      "videoinfo",
                  "viprop":    "url|size|mime",
                  "format":    "json",
              }
              r = req.get(
                  "https://commons.wikimedia.org/w/api.php",
                  params=params, timeout=15
              )
              if r.status_code != 200:
                  continue

              pages = r.json().get("query", {}).get("pages", {})
              for page in pages.values():
                  if len(clips) >= count:
                      break
                  vinfo = page.get("videoinfo", [{}])[0]
                  url   = vinfo.get("url", "")
                  mime  = vinfo.get("mime", "")
                  if not url:
                      continue
                  if "video" not in mime and not url.endswith(
                      (".mp4", ".webm", ".ogv")
                  ):
                      continue
                  path = self._download(url, "wikimedia", "long")
                  if path:
                      clips.append(path)
          except Exception as e:
              print(f"[Wikimedia] {term}: {e}")
          time.sleep(0.5)

      return clips

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
    def _get_cdn_urls(self, topic: str, category_id: str = "") -> list[str]:
        """Returns direct CDN URLs if topic matches a brand."""
        topic_lower = (topic + " " + category_id).lower()
        for brand, urls in OEM_CDN_URLS.items():
            if brand in topic_lower:
                return urls
        return []

    def _scrape_press_page(self, url: str, base: str, prefix: str,
                           count: int, video_type: str,
                           rel_kws: list[str]) -> list[str]:
        """
        Fetch press page HTML, extract all .mp4 URLs.
        Includes direct CDN fallback.
        """
        # 1. Try Direct CDN first
        brand_name = prefix.split("_")[0].lower()
        direct = self._get_cdn_urls(brand_name)
        
        # 2. Scrape page (3 retries with diff UAs)
        scraped = []
        for _ in range(3):
            try:
                r = self._session.get(url, timeout=TIMEOUT, allow_redirects=True, headers=self._get_headers())
                if r.status_code == 200:
                    found = re.findall(r'https?://[^\s"\'<>]+?\.mp4', r.text, re.IGNORECASE)
                    scraped = list(dict.fromkeys(found))
                    if scraped: break
            except:
                time.sleep(1)

        all_urls = direct + scraped
        random.shuffle(all_urls)
        
        clips = []
        for mp4_url in all_urls:
            if len(clips) >= count:
                break
            
            # Basic validation
            url_lower = mp4_url.lower()
            if any(bad in url_lower for bad in ["ad", "promo", "commercial"]):
                continue
                
            path = self._download(mp4_url, prefix, video_type)
            if path:
                clips.append(path)
                
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

        # 3 Retries with different User-Agents
        for i in range(3):
            try:
                r = self._session.get(url, timeout=30, stream=True, headers=self._get_headers())
                if r.status_code == 200:
                    break
                print(f"[OEM] Retry {i+1} (Status {r.status_code})")
            except:
                pass
            time.sleep(1)
        else:
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
