"""
Evcarix MediaEngine — Tam Yeniden Yazım
Video Öncelik Sırası:
1. YouTube Creative Commons (yt-dlp + YouTube Data API v3)
2. OEM Marka Basın Kiti (Tesla, BYD, Hyundai, BMW, Kia, VW, Mercedes, Rivian, Lucid, Polestar, NIO, Ford, GM)
3. Pexels HD (CC0)
4. Pixabay HD (CC0)
5. fal.ai AI Video
6. HuggingFace AI Video
7. Runway ML AI Video
8. Luma Dream Machine AI Video
9. Kling AI Video
10. Stability AI Video
11. Replicate AI Video
12. Pollinations.ai AI Görüntü (key gerektirmez)
"""

import os
import re
import json
import time
import random
import subprocess
import requests
import urllib.parse
from pathlib import Path
from PIL import Image
from src.voice_engine import VoiceEngine
from src.visual_engine import VisualEngine
from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════════════════
#  OEM MARKA BASИН KİTİ
#  Konuya göre doğru marka seçilir — HD, telifsiz
# ═══════════════════════════════════════════════════════════════════
OEM_BRAND_VIDEOS = {
    "tesla": {
        "keywords": ["tesla", "model 3", "model y", "model s", "model x",
                     "cybertruck", "supercharger", "autopilot", "fsd", "powerwall"],
        "videos": [
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-Y-Desktop-NA.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Model-Y-Homepage-Desktop.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Model-3-Homepage-Desktop.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Cybertruck-Homepage-Desktop-01.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Energy-Megapack-Desktop.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Model-S-Homepage-Desktop-LHD-01.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-3-Desktop-NA.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Megapack-Homepage-Desktop.mp4",
        ],
        "priority": 1,
    },
    "byd": {
        "keywords": ["byd", "byd seal", "byd atto", "byd han", "byd tang",
                     "byd dolphin", "byd seagull", "byd electric", "blade battery"],
        "videos": [
            "https://www.byd.com/content/dam/byd-site/eu/videos/seal/BYD-Seal-Exterior.mp4",
            "https://www.byd.com/content/dam/byd-site/eu/videos/atto3/BYD-Atto3-Driving.mp4",
            "https://www.byd.com/content/dam/byd-site/eu/videos/han/BYD-Han-Exterior.mp4",
            "https://www.byd.com/content/dam/byd-site/eu/videos/dolphin/BYD-Dolphin-Exterior.mp4",
        ],
        "priority": 1,
    },
    "hyundai": {
        "keywords": ["hyundai", "ioniq", "ioniq 5", "ioniq 6", "ioniq 9",
                     "kona electric", "nexo"],
        "videos": [
            "https://www.hyundai.com/content/dam/hyundai/ww/en/videos/ioniq6/ioniq6-exterior-driving.mp4",
            "https://www.hyundai.com/content/dam/hyundai/ww/en/videos/ioniq5/ioniq5-driving-exterior.mp4",
            "https://www.hyundai.com/content/dam/hyundai/master/en/images/find-a-car/ioniq5/highlights/hyundai-ioniq5-highlights-design-720.mp4",
            "https://www.hyundai.com/content/dam/hyundai/ww/en/videos/ioniq6/ioniq6-design-720.mp4",
        ],
        "priority": 2,
    },
    "kia": {
        "keywords": ["kia", "ev6", "ev9", "ev3", "niro ev", "kia electric"],
        "videos": [
            "https://www.kia.com/content/dam/kwcms/kme/global/en/videos/ev6/kia-ev6-exterior-driving.mp4",
            "https://www.kia.com/content/dam/kwcms/kme/global/en/videos/ev9/kia-ev9-exterior.mp4",
            "https://www.kia.com/content/dam/kwcms/kme/global/en/videos/ev6/kia-ev6-design.mp4",
        ],
        "priority": 2,
    },
    "bmw": {
        "keywords": ["bmw", "bmw i4", "bmw ix", "bmw i5", "bmw i7",
                     "bmw i3", "bmw electric"],
        "videos": [
            "https://www.bmw.com/content/dam/bmw/common/all-models/i-series/i4/2021/OnePager/bmw-i4-design-stage.mp4",
            "https://www.bmw.com/content/dam/bmw/common/all-models/i-series/ix/2021/highlights/bmw-ix-stage.mp4",
            "https://www.bmw.com/content/dam/bmw/common/all-models/i-series/i5/2023/bmw-i5-driving.mp4",
        ],
        "priority": 2,
    },
    "volkswagen": {
        "keywords": ["volkswagen", "vw", "id.4", "id.3", "id.7", "id.buzz",
                     "id4", "id3", "id7"],
        "videos": [
            "https://media.vw.com/content/dam/vw/videos/id4/vw-id4-exterior-driving-2023.mp4",
            "https://media.vw.com/content/dam/vw/videos/idbuzz/vw-id-buzz-reveal.mp4",
            "https://media.vw.com/content/dam/vw/videos/id3/vw-id3-exterior.mp4",
        ],
        "priority": 2,
    },
    "mercedes": {
        "keywords": ["mercedes", "eqs", "eqe", "eqb", "eqa", "eqc",
                     "mercedes electric", "amg eq", "eqs suv"],
        "videos": [
            "https://media.mercedes-benz.com/content/dam/mb-web/pressdossier/model-series/eqs/eqs-driving-exterior.mp4",
            "https://media.mercedes-benz.com/content/dam/mb-web/pressdossier/model-series/eqe/eqe-exterior.mp4",
        ],
        "priority": 2,
    },
    "rivian": {
        "keywords": ["rivian", "r1t", "r1s", "rivian truck", "rivian electric"],
        "videos": [
            "https://rivian.com/videos/r1t-offroad-adventure.mp4",
            "https://rivian.com/videos/r1s-driving-exterior.mp4",
            "https://rivian.com/videos/r1t-driving-highway.mp4",
        ],
        "priority": 2,
    },
    "lucid": {
        "keywords": ["lucid", "lucid air", "lucid gravity", "lucid motors",
                     "lucid pure", "lucid touring"],
        "videos": [
            "https://www.lucidmotors.com/media/video/lucid-air-exterior.mp4",
            "https://www.lucidmotors.com/media/video/lucid-air-driving.mp4",
            "https://www.lucidmotors.com/media/video/lucid-air-interior.mp4",
        ],
        "priority": 2,
    },
    "polestar": {
        "keywords": ["polestar", "polestar 2", "polestar 3", "polestar 4"],
        "videos": [
            "https://www.polestar.com/media/polestar2-driving-exterior-hd.mp4",
            "https://www.polestar.com/media/polestar3-exterior-reveal.mp4",
        ],
        "priority": 3,
    },
    "nio": {
        "keywords": ["nio", "nio et5", "nio et7", "nio es6", "nio es8",
                     "nio el6", "nio electric"],
        "videos": [
            "https://cdn.nio.com/videos/et5-exterior-driving.mp4",
            "https://cdn.nio.com/videos/et7-night-exterior.mp4",
        ],
        "priority": 3,
    },
    "ford": {
        "keywords": ["ford", "mustang mach-e", "f-150 lightning", "ford electric",
                     "mach-e", "f150 lightning"],
        "videos": [
            "https://media.ford.com/content/fordmedia/fna/us/en/media/videos/2023/mache/mache-driving.mp4",
            "https://media.ford.com/content/fordmedia/fna/us/en/media/videos/2022/f150lightning/f150-lightning-exterior.mp4",
        ],
        "priority": 3,
    },
    "gm": {
        "keywords": ["chevrolet", "chevy", "silverado ev", "blazer ev",
                     "equinox ev", "cadillac lyriq", "gm electric"],
        "videos": [
            "https://media.gm.com/content/dam/Media/gmcom/vehicle/2024/silverado-ev/silverado-ev-driving.mp4",
            "https://media.gm.com/content/dam/Media/gmcom/vehicle/2024/blazer-ev/blazer-ev-exterior.mp4",
        ],
        "priority": 3,
    },
}

# Kategori bazlı OEM öncelikleri
CATEGORY_OEM_PRIORITY = {
    "battery_science":  ["tesla", "byd", "bmw", "volkswagen"],
    "range_tests":      ["tesla", "hyundai", "lucid", "byd", "kia"],
    "charging":         ["tesla", "bmw", "volkswagen", "hyundai", "kia"],
    "comparisons":      ["tesla", "byd", "hyundai", "kia", "bmw", "volkswagen"],
    "cost_ownership":   ["tesla", "volkswagen", "hyundai", "kia", "ford"],
    "market_data":      ["byd", "tesla", "volkswagen", "nio", "gm"],
    "infrastructure":   ["tesla", "volkswagen", "bmw", "hyundai"],
    "education":        ["tesla", "bmw", "hyundai", "volkswagen"],
    "trend":            ["tesla", "byd", "hyundai", "rivian", "lucid", "polestar"],
}

# YouTube CC arama terimleri — konuya göre (Genişletilmiş: Tüm araçlar + Batarya)
YTCC_QUERIES = {
    "battery_science": [
        "EV battery technology manufacturing b-roll",
        "lithium ion battery production line footage",
        "battery cell assembly factory cc",
        "solid state battery research laboratory b-roll",
        "battery degradation testing footage creative commons",
        "electric car battery pack interior deep dive cc",
    ],
    "range_tests": [
        "car driving highway footage creative commons",
        "sports car acceleration b-roll cc",
        "luxury sedan interior driving footage cc",
        "electric vehicle winter range test b-roll",
        "vehicle speedometer 70mph highway driving cc",
    ],
    "charging": [
        "EV charging station footage creative commons",
        "electric car charger b-roll cc",
        "fast charging technology explanation footage",
        "charging network infrastructure b-roll",
        "home EV charger installation footage cc",
    ],
    "comparisons": [
        "modern cars side by side b-roll cc",
        "luxury vehicle comparison footage creative commons",
        "car dealership showroom b-roll cc",
        "supercar vs electric car race b-roll cc",
    ],
    "market_data": [
        "car factory automation robots b-roll cc",
        "automotive shipping port global logistics cc",
        "car sales dealership busy showroom b-roll",
        "autonomous driving technology test b-roll cc",
    ],
    "education": [
        "automotive engineering engine battery explained cc",
        "car aerodynamics wind tunnel testing b-roll",
        "regenerative braking technology visual cc",
        "electric motor vs ice engine animation cc",
    ],
}
YTCC_DEFAULT_QUERIES = [
    "modern car driving b-roll footage creative commons",
    "luxury vehicle exterior driving cc by",
    "sports car highway speed footage creative commons",
    "automotive technology innovation b-roll cc",
    "battery energy storage technology footage",
    "classic car restoration footage creative commons",
]


class MediaEngine:
    def __init__(self):
        # Stok video API'leri
        self.pexels_api_key  = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")

        # AI video servisleri
        self.fal_key         = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
        self.hf_token        = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        self.runway_key      = os.getenv("RUNWAY_API_KEY")
        self.luma_key        = os.getenv("LUMA_API_KEY")
        self.kling_key       = os.getenv("KLING_API_KEY") or os.getenv("KLING_ACCESS_KEY")
        self.stability_key   = os.getenv("STABILITY_API_KEY")
        self.replicate_key   = os.getenv("REPLICATE_API_KEY")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")

        # Geriye dönük uyum için alias'lar
        self.stability_api_key = self.stability_key
        self.replicate_api_key = self.replicate_key
        self.kling_access_key  = self.kling_key
        self.kling_secret_key  = os.getenv("KLING_SECRET_KEY")

        # Ses ve Görsel Motorları
        self.voice_engine = VoiceEngine()
        self.visual_engine = VisualEngine()

        # Kullanılan klip takip sistemi
        self.used_clips_file = "used_clips.json"
        self._load_used_clips()

        # yt-dlp kurulu mu?
        try:
            subprocess.run(["yt-dlp", "--version"],
                           capture_output=True, check=True, timeout=10)
            self.ytdlp_available = True
        except Exception:
            self.ytdlp_available = False

    # ── Ses Üretimi ────────────────────────────────────────────────
    async def generate_voiceover(self, text, output_path,
                                 voice_type="female", rate="+10%"):
        return await self.voice_engine.generate_voice(
            text, output_path, voice_type=voice_type, rate=rate)

    # ══════════════════════════════════════════════════════════════
    #  KULLANILAN KLİP TAKİP SİSTEMİ
    # ══════════════════════════════════════════════════════════════
    def _load_used_clips(self):
        if os.path.exists(self.used_clips_file):
            try:
                with open(self.used_clips_file, "r") as f:
                    self._used_clips = set(json.load(f))
            except Exception:
                self._used_clips = set()
        else:
            self._used_clips = set()
        print(f"[MediaEngine] 📋 Daha önce kullanılan klip sayısı: {len(self._used_clips)}")

    def _save_used_clips(self):
        clip_list = list(self._used_clips)[-500:]
        with open(self.used_clips_file, "w") as f:
            json.dump(clip_list, f)

    def _get_clip_hash(self, file_path: str) -> str:
        try:
            size = os.path.getsize(file_path)
            return f"{os.path.basename(file_path)}_{size}"
        except Exception:
            return os.path.basename(file_path)

    def _filter_used_clips(self, paths: list) -> list:
        fresh, skipped = [], 0
        for p in paths:
            if not p or not os.path.exists(p):
                continue
            if self._get_clip_hash(p) not in self._used_clips:
                fresh.append(p)
            else:
                skipped += 1
        if skipped:
            print(f"[MediaEngine] 🔄 {skipped} daha önce kullanılan klip atlandı.")
        return fresh

    def mark_clips_as_used(self, paths: list):
        count = 0
        for p in paths:
            if p and os.path.exists(p):
                self._used_clips.add(self._get_clip_hash(p))
                count += 1
        self._save_used_clips()
        print(f"[MediaEngine] ✅ {count} klip 'kullanıldı' olarak kaydedildi.")


    # ══════════════════════════════════════════════════════════════
    #  YÖNTEM 2: OEM MARKA BASИН KİTİ
    #  Tesla, BYD, Hyundai vb. resmi basın kitleri — HD, telifsiz
    # ══════════════════════════════════════════════════════════════
    def _detect_brands_in_topic(self, topic: str, category: str = None) -> list:
        topic_lower = topic.lower()
        matched = []
        for brand, data in OEM_BRAND_VIDEOS.items():
            for kw in data["keywords"]:
                if kw in topic_lower:
                    matched.append(brand)
                    break

        cat_priority = CATEGORY_OEM_PRIORITY.get(category, [])
        if not matched and cat_priority:
            matched = cat_priority[:3]

        if not matched:
            matched = ["tesla", "byd", "hyundai", "bmw"]

        matched.sort(key=lambda b: OEM_BRAND_VIDEOS.get(b, {}).get("priority", 99))
        return matched

    def _download_from_oem(self, topic: str, output_dir: str,
                            count: int, category: str = None) -> list:
        """
        OEM marka basın kitlerinden HD video indirir.
        HEAD kontrolü ile 404 / GIF / HTML tuzaklarını önler.
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        brands = self._detect_brands_in_topic(topic, category)
        print(f"[OEM] Tespit edilen markalar: {brands[:4]}")

        for brand in brands:
            if len(paths) >= count:
                break
            brand_data = OEM_BRAND_VIDEOS.get(brand, {})
            video_urls = list(brand_data.get("videos", []))
            random.shuffle(video_urls)

            for url in video_urls:
                if len(paths) >= count:
                    break
                fname = f"oem_{brand}_{Path(url).stem[:35]}.mp4"
                out   = os.path.join(output_dir, fname)

                # Önbellekten al
                if os.path.exists(out) and os.path.getsize(out) > 500_000:
                    clip_hash = self._get_clip_hash(out)
                    if clip_hash not in self._used_clips:
                        paths.append(out)
                        print(f"[OEM] ♻️  Önbellekten: {fname}")
                        continue

                try:
                    # HEAD isteği ile URL geçerliliğini kontrol et
                    head = requests.head(
                        url, timeout=10, allow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; Evcarix/2.0)"}
                    )
                    ct = head.headers.get("content-type", "")
                    cl = int(head.headers.get("content-length", 0))

                    if "image/gif" in ct or "text/html" in ct or "text/plain" in ct:
                        print(f"[OEM] ⛔ Geçersiz içerik ({ct}): {brand}")
                        continue
                    if head.status_code not in (200, 206):
                        print(f"[OEM] HTTP {head.status_code}: {brand}")
                        continue
                    if 0 < cl < 500_000:
                        print(f"[OEM] ⚠️  Çok küçük ({cl} byte): {brand}")
                        continue

                    print(f"[OEM] {brand.upper()} HD video indiriliyor: {fname}")
                    r = requests.get(
                        url, stream=True, timeout=90,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; Evcarix/2.0)"}
                    )
                    if r.status_code == 200:
                        with open(out, "wb") as f:
                            for chunk in r.iter_content(1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        size = os.path.getsize(out)
                        if size > 500_000:
                            paths.append(out)
                            print(f"[OEM] ✅ {fname} ({size // 1024 // 1024}MB)")
                        else:
                            os.remove(out)
                            print(f"[OEM] ⚠️  Dosya çok küçük ({size} byte): {brand}")
                    else:
                        print(f"[OEM] HTTP {r.status_code}: {brand}")

                except requests.exceptions.Timeout:
                    print(f"[OEM] ⏱️ Zaman aşımı: {brand}")
                except requests.exceptions.ConnectionError:
                    print(f"[OEM] 🔌 Bağlantı hatası: {brand}")
                except Exception as e:
                    print(f"[OEM] {brand} hata: {type(e).__name__}: {e}")

        print(f"[OEM] {len(paths)} HD marka videosu hazır")
        return paths

    # ══════════════════════════════════════════════════════════════
    #  YÖNTEM 3: PEXELS HD — CC0
    # ══════════════════════════════════════════════════════════════
    _IRRELEVANT_TAGS = {
        "fireplace", "fire", "flame", "christmas", "xmas", "flower", "flowers",
        "nature", "forest", "mountain", "beach", "ocean", "sea", "cooking",
        "food", "kitchen", "coffee", "cat", "dog", "animal", "baby", "wedding",
        "yoga", "meditation", "fitness", "gym", "rain", "snow", "storm",
        "abstract", "background", "texture", "pattern", "paint", "art",
        "waterfall", "sunrise", "timelapse", "stars", "space", "sky",
    }
    _RELEVANT_TAGS = {
        "electric", "ev", "tesla", "battery", "charging", "car", "vehicle",
        "automobile", "auto", "automotive", "transport", "technology", "drive",
        "highway", "road", "traffic", "city", "urban", "motor", "energy",
        "green", "eco", "future", "innovation", "speed", "dashboard",
    }

    def _is_ev_related(self, video_data):
        tags = video_data.get("tags", []) or []
        tag_set = {t.lower() for t in tags if isinstance(t, str)}
        if tag_set & self._IRRELEVANT_TAGS:
            return False
        if tag_set & self._RELEVANT_TAGS:
            return True
        return True

    def _get_professional_query(self, topic, category=None):
        category_strategies = {
            "battery_science": [
                "lithium battery cell technology laboratory close up 4k",
                "EV battery pack assembly manufacturing HD",
                "solid state battery futuristic technology",
                "battery research scientist laboratory blue light",
                "battery management system circuit board close up",
            ],
            "range_tests": [
                "electric car driving highway aerial view 4k",
                "EV dashboard speedometer range display",
                "Tesla Model 3 driving road cinematic 4k",
                "electric vehicle winter snow driving HD",
                "car driving city night lights 4k cinematic",
            ],
            "charging": [
                "electric car charging station night 4k",
                "EV fast charging plug cable close up HD",
                "Tesla supercharger station multiple cars charging",
                "charging station technology futuristic blue light",
                "electric vehicle charging port detail close up",
            ],
            "cost_ownership": [
                "electric car showroom dealership modern interior",
                "money savings finance calculator digital",
                "family buying car dealer handshake",
                "car insurance documents business finance",
                "electric vehicle price comparison screen",
            ],
            "comparisons": [
                "two electric cars side by side showroom 4k",
                "electric vehicles lineup multiple cars parked HD",
                "car comparison test track aerial drone",
                "EV specifications display screen technology",
                "electric cars row modern parking 4k",
            ],
            "market_data": [
                "global business data analytics screen 4k",
                "electric vehicle factory production line aerial",
                "world map digital connections network technology",
                "stock market chart graph rising technology",
                "factory production line modern manufacturing HD",
            ],
            "infrastructure": [
                "electric car charging network city night 4k",
                "power grid electricity transmission tower HD",
                "solar panels renewable energy field aerial",
                "smart city technology traffic electric",
                "charging station modern design exterior night",
            ],
            "education": [
                "electric motor engine technology close up 4k",
                "heat pump HVAC system technology explainer",
                "car aerodynamics wind tunnel test HD",
                "thermal imaging heat visualization technology",
                "engineering blueprint technical design modern",
            ],
            "trend": [
                "futuristic electric car driving cinematic 4k",
                "new electric vehicle launch reveal HD",
                "modern EV exterior driving sunset golden hour",
                "electric car technology innovation 4k aerial",
                "luxury electric vehicle modern design 4k",
            ],
        }
        if category and category in category_strategies:
            return random.choice(category_strategies[category])

        clean = topic.split(":")[0].split("?")[0].strip()
        clean = clean.replace("electric", "").replace("car", "").strip()
        fallback = [
            f"{clean} EV driving 4k cinematic",
            "electric car charging station 4k HD",
            "Tesla Model Y driving highway",
            "EV battery technology close up",
            "electric vehicle modern exterior",
        ]
        return random.choice(fallback)

    def _download_from_pexels(self, query, output_dir, count,
                               orientation="portrait", category=None):
        if not self.pexels_api_key:
            return []
        
        # Ensure temp directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        q = self._get_professional_query(query, category)
        headers = {"Authorization": self.pexels_api_key}
        page = random.randint(1, 8)
        url = (
            f"https://api.pexels.com/videos/search"
            f"?query={urllib.parse.quote(q)}"
            f"&per_page={count + 5}&page={page}"
            f"&orientation={orientation}&size=large"
        )
        paths = []
        try:
            print(f"[Pexels] '{q}' (sayfa {page}, {orientation}) aranıyor...")
            r = requests.get(url, headers=headers, timeout=15)
            videos = r.json().get("videos", []) if r.status_code == 200 else []
            if not videos:
                r2 = requests.get(
                    url.replace(f"page={page}", "page=1"),
                    headers=headers, timeout=15
                )
                videos = r2.json().get("videos", []) if r2.status_code == 200 else []
            random.shuffle(videos)
            for i, vd in enumerate(videos):
                if len(paths) >= count:
                    break
                if not self._is_ev_related(vd):
                    continue
                files = sorted(vd.get("video_files", []),
                               key=lambda x: x.get("width", 0), reverse=True)
                # HD tercih: en az 1280px
                hd = [f for f in files if f.get("width", 0) >= 1280]
                chosen = hd[0] if hd else (files[0] if files else None)
                if not chosen:
                    continue
                q_clean = re.sub(r'[^\w]', '_', q)[:25]
                fname = f"pexels_{q_clean}_{page}_{i}.mp4"
                out = os.path.join(output_dir, fname)
                dl = requests.get(chosen["link"], stream=True, timeout=60)
                if dl.status_code == 200:
                    with open(out, "wb") as f:
                        for chunk in dl.iter_content(1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(out) > 100_000:
                        paths.append(out)
                        w = chosen.get("width", "?")
                        h = chosen.get("height", "?")
                        print(f"[Pexels] ✅ {fname} ({w}x{h})")
        except Exception as e:
            print(f"[Pexels] Hata: {e}")
        return paths

    # ══════════════════════════════════════════════════════════════
    #  YÖNTEM 4: PIXABAY HD — CC0
    # ══════════════════════════════════════════════════════════════
    def _download_from_pixabay(self, query, output_dir, count,
                                orientation="horizontal", category=None):
        if not self.pixabay_api_key:
            return []
        
        # Ensure temp directory exists
        os.makedirs(output_dir, exist_ok=True)
        cat_q = {
            "battery_science":  ["lithium battery cell", "battery technology laboratory", "battery factory"],
            "range_tests":      ["electric car highway driving", "dashboard speedometer", "winter road driving"],
            "charging":         ["EV charging station", "electric car charging", "fast charging technology"],
            "comparisons":      ["electric vehicles showroom", "car comparison", "cars parked modern"],
            "cost_ownership":   ["car dealership", "money finance business", "electric car purchase"],
            "market_data":      ["factory production line", "business analytics", "global network"],
            "infrastructure":   ["solar panels energy", "power grid", "smart city charging"],
            "education":        ["electric motor technology", "engineering laboratory", "heat pump technology"],
            "trend":            ["electric car futuristic", "new EV exterior", "modern electric vehicle"],
        }
        q = random.choice(cat_q.get(category, [
            "electric car", "EV charging", "electric vehicle technology",
            "EV battery", "electric car driving 4k"
        ]))
        pix_or = "vertical" if orientation == "portrait" else "horizontal"
        page = random.randint(1, 5)
        params = {
            "key": self.pixabay_api_key, "q": q,
            "video_type": "film", "orientation": pix_or,
            "order": "popular", "per_page": count + 5,
            "page": page, "safesearch": "true",
        }
        paths = []
        try:
            print(f"[Pixabay] '{q}' (sayfa {page}) aranıyor...")
            r = requests.get("https://pixabay.com/api/videos/",
                             params=params, timeout=15)
            hits = r.json().get("hits", []) if r.status_code == 200 else []
            if not hits:
                params["page"] = 1
                r2 = requests.get("https://pixabay.com/api/videos/",
                                  params=params, timeout=30)
                hits = r2.json().get("hits", []) if r2.status_code == 200 else []
            random.shuffle(hits)
            for i, hit in enumerate(hits[:count + 2]):
                if len(paths) >= count:
                    break
                vids = hit.get("videos", {})
                chosen = None
                # HD kalite önceliği
                for qual in ["large", "medium", "small"]:
                    v = vids.get(qual, {})
                    if v.get("url") and v.get("width", 0) >= 1280:
                        chosen = v
                        break
                if not chosen:
                    for qual in ["large", "medium", "small"]:
                        v = vids.get(qual, {})
                        if v.get("url"):
                            chosen = v
                            break
                if not chosen:
                    continue
                q_clean = re.sub(r'[^\w]', '_', q)[:25]
                fname = f"pixabay_{q_clean}_{page}_{i}.mp4"
                out = os.path.join(output_dir, fname)
                dl = requests.get(chosen["url"], stream=True, timeout=60)
                if dl.status_code == 200:
                    with open(out, "wb") as f:
                        for chunk in dl.iter_content(1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(out) > 100_000:
                        paths.append(out)
                        w = chosen.get("width", "?")
                        h = chosen.get("height", "?")
                        print(f"[Pixabay] ✅ {fname} ({w}x{h})")
        except Exception as e:
            print(f"[Pixabay] Hata: {e}")
        return paths

    # ══════════════════════════════════════════════════════════════
    #  YÖNTEM 5: YOUTUBE CREATIVE COMMONS
    # ══════════════════════════════════════════════════════════════
    def _download_youtube_cc(self, query, output_dir, count, video_type="short"):
        if not self.youtube_api_key:
            print("[YouTubeCC] API anahtarı eksik, atlanıyor.")
            return []
        
        paths = []
        try:
            print(f"[YouTubeCC] '{query}' aranıyor (CC)...")
            search_url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoLicense": "creativeCommon",
                "videoCaption": "any",
                "maxResults": 15,
                "key": self.youtube_api_key
            }
            r = requests.get(search_url, params=params, timeout=15)
            items = r.json().get("items", [])
            random.shuffle(items)

            for item in items:
                if len(paths) >= count:
                    break
                video_id = item["id"]["videoId"]
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Dosya ismi
                q_clean = re.sub(r'[^\w]', '_', query)[:20]
                fname = f"ytcc_{q_clean}_{video_id}.mp4"
                out_path = os.path.join(output_dir, fname)

                # İndirme (yt-dlp)
                # Not: YouTube CC videoları genellikle yüksek kalitelidir, 
                # ancak boyutu sınırlandırmak için 720p/1080p sınırı koyuyoruz
                format_str = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"
                cmd = [
                    "yt-dlp",
                    "-f", format_str,
                    "--merge-output-format", "mp4",
                    "-o", out_path,
                    "--max-filesize", "150M",
                    "--no-playlist",
                    video_url
                ]
                
                try:
                    res = subprocess.run(cmd, capture_output=True, timeout=120)
                    if res.returncode == 0 and os.path.exists(out_path):
                        if os.path.getsize(out_path) > 500_000:
                            paths.append(out_path)
                            print(f"[YouTubeCC] ✅ İndirildi: {fname}")
                except Exception as e:
                    print(f"[YouTubeCC] İndirme hatası ({video_id}): {e}")

        except Exception as e:
            print(f"[YouTubeCC] Arama hatası: {e}")
        
        return paths

    # ══════════════════════════════════════════════════════════════
    #  ANA İNDİRME — TÜM KAYNAKLAR BİRLEŞİK
    # ══════════════════════════════════════════════════════════════
    def download_stock_videos(self, plan=None, target_clip_count=6,
                              query=None, count=None,
                              orientation=None, category=None):
        """
        Download stock videos using a multi-stage fallback strategy.
        Supports both:
          - New style: download_stock_videos(plan=dict, target_clip_count=N)
          - Legacy:    download_stock_videos(query=str, count=N, orientation=str, category=str)
        """
        from src.free_footage import FreeFootageEngine
        from src.ai_video_generator import AIVideoGenerator
        from src.query_builder import get_queries_for_script

        # ── Geriye dönük uyum: eski parametrelerden plan oluştur ──
        if plan is None or not isinstance(plan, dict):
            plan = {
                "topic":       query or "",
                "category_id": category or "",
                "script":      "",
            }
        if count is not None:
            target_clip_count = count

        video_type  = os.environ.get("VIDEO_TYPE", "short")
        if orientation == "landscape":
            video_type = "long"
        elif orientation == "portrait":
            video_type = "short"

        topic_text  = plan.get("topic", "") or (query or "")
        category_id = plan.get("category_id", "") or (category or "")
        script_text = plan.get("script", "") or ""
        queries     = get_queries_for_script(script_text, topic_text, category_id)
        needed      = target_clip_count
        all_clips   = []

        # Stage 1 — YouTube Creative Commons (En kaliteli ve spesifik içerik)
        print("[MediaEngine] Stage 1: YouTube CC...")
        yt_queries = YTCC_QUERIES.get(category_id, YTCC_DEFAULT_QUERIES)
        random.shuffle(yt_queries)
        for q in yt_queries[:2]:
            if len(all_clips) >= needed:
                break
            new = self._download_youtube_cc(q, "assets/temp_videos", needed - len(all_clips), video_type)
            all_clips.extend(new)
        
        # Eğer hala eksikse konunun kendisiyle ara
        if len(all_clips) < needed:
            new = self._download_youtube_cc(f"{topic_text} footage b-roll cc", "assets/temp_videos", needed - len(all_clips), video_type)
            all_clips.extend(new)
        print(f"[MediaEngine] YouTube CC: {len(all_clips)} klip")

        # Stage 2 — Pexels (fast, reliable CC0)
        if len(all_clips) < needed:
            print("[MediaEngine] Stage 2: Pexels...")
            for q in queries[:3]:
                if len(all_clips) >= needed:
                    break
                new = self._download_from_pexels(q, "assets/temp_videos", needed - len(all_clips), "portrait" if video_type=="short" else "landscape", category_id)
                all_clips.extend(new)
            print(f"[MediaEngine] Pexels: {len(all_clips)} klip")

        # Stage 2 — Pixabay (CC0)
        if len(all_clips) < needed:
            print("[MediaEngine] Stage 2: Pixabay...")
            for q in queries[:2]:
                if len(all_clips) >= needed:
                    break
                new = self._download_from_pixabay(q, "assets/temp_videos", needed - len(all_clips), "portrait" if video_type=="short" else "landscape", category_id)
                all_clips.extend(new)
            print(f"[MediaEngine] Pixabay: {len(all_clips)} klip")

        # Stage 3 — Free Footage Engine (Archive.org + NASA + Wikimedia + OEM diverse)
        if len(all_clips) < needed:
            print("[MediaEngine] Stage 3: Free Footage Engine...")
            try:
                ffe   = FreeFootageEngine()
                new   = ffe.get_clips(
                    topic       = topic_text,
                    category_id = category_id,
                    count       = needed - len(all_clips),
                    video_type  = video_type,
                )
                all_clips.extend(new)
                print(f"[MediaEngine] FreeFootage: +{len(new)} klip")
            except Exception as e:
                print(f"[MediaEngine] FreeFootage hata: {e}")

        # Stage 4 — AI Video (fal.ai → Kling → Replicate)
        if len(all_clips) < needed:
            print("[MediaEngine] Stage 4: AI video...")
            try:
                ai  = AIVideoGenerator()
                new = ai.generate(
                    topic       = topic_text,
                    category_id = category_id,
                    count       = needed - len(all_clips),
                    duration    = 6,
                    video_type  = video_type,
                )
                all_clips.extend(new)
            except Exception as e:
                print(f"[MediaEngine] AI video hata: {e}")

        if not all_clips:
            print("[MediaEngine] ❌ Hiç klip bulunamadı!")
        else:
            print(f"[MediaEngine] ✅ Toplam {len(all_clips)} klip hazır")
        
        return all_clips

    # ══════════════════════════════════════════════════════════════
    #  AI VIDEO ÜRETİMİ — 7 Servis Sıralı Fallback
    # ══════════════════════════════════════════════════════════════
    def _get_ai_prompts(self, topic, category=None):
        cat_prompts = {
            "battery_science": [
                "lithium battery cells glowing blue in laboratory, macro close up, 4k cinematic, no text",
                "EV battery pack assembly manufacturing line high tech factory, 4k, no text",
                "solid state battery technology futuristic blue energy glow, 4k, no text",
                "battery management system circuit board LED lights, 4k macro, no text",
            ],
            "range_tests": [
                "electric car driving on empty highway at sunset, aerial drone shot, 4k cinematic, no text",
                "Tesla Model 3 interior dashboard showing range display night driving, 4k, no text",
                "EV driving through winter snow landscape dramatic lighting, 4k cinematic, no text",
                "electric vehicle speedometer dashboard close up night neon lights, 4k, no text",
            ],
            "charging": [
                "Tesla supercharger station at night multiple EVs charging, neon lights, 4k cinematic, no text",
                "EV charging cable plugging into electric car port close up macro, 4k, no text",
                "fast charging station futuristic design electric sparks energy, 4k, no text",
            ],
            "comparisons": [
                "multiple luxury electric cars parked modern showroom, 4k cinematic, no text",
                "two electric vehicles side by side on race track aerial view, 4k, no text",
            ],
            "market_data": [
                "electric vehicle factory production line aerial view modern industrial, 4k, no text",
                "BYD Tesla factory interior robots assembling EVs high tech, 4k, no text",
            ],
            "education": [
                "electric motor cross section animation spinning magnets blue energy, 4k, no text",
                "car aerodynamics wind tunnel test streamlines visible, 4k cinematic, no text",
            ],
        }
        base = [
            f"futuristic electric car driving on highway at sunset, cinematic 4k, no text, {topic}",
            "EV battery technology close up, laboratory blue glow, 4k cinematic, no text",
            "electric vehicle charging station at night, city lights reflections, 4k, no text",
            "modern EV exterior driving through city golden hour, cinematic 4k, no text",
            "aerial drone shot electric car on winding mountain road, 4k, no text",
            "electric motor engine technology heat visualization blue glow, macro 4k, no text",
        ]
        return cat_prompts.get(category, base)

    # ── İNFOGRAFİK ÜRETİMİ ──────────────────────────────────────────
    def generate_data_card_video(self, topic, script_text, orientation="portrait"):
        """
        Script içinden önemli verileri çekip otomatik infografik kartı üretir.
        """
        print(f"[MediaEngine] İnfografik veri kartı hazırlanıyor: {topic}")
        
        # Gemini'den kısa veri çekelim (basit prompt)
        try:
            from src.creative_writer import CreativeWriter
            writer = CreativeWriter()
            prompt = f"Aşağıdaki metinden {topic} hakkında 3 tane kısa istatistiksel veri çıkar (Örn: Menzil, Fiyat, Hız). Sadece 'Etiket: Değer' formatında 3 satır yaz:\n\n{script_text}"
            raw_data = writer.generate_text(prompt)
            
            points = []
            for line in raw_data.split("\n"):
                if ":" in line:
                    parts = line.split(":", 1)
                    points.append((parts[0].strip(), parts[1].strip()))
            
            if not points:
                points = [("Topic", topic), ("Category", "Electric Vehicle"), ("Source", "Evcarix News")]
                
            # Kartı oluştur
            out_img = os.path.join("assets/visuals", f"card_{int(time.time())}.png")
            self.visual_engine.create_data_card(topic, points, out_img)
            
            # Videoya çevir
            out_vid = os.path.join("assets/visuals", f"card_vid_{int(time.time())}.mp4")
            vid = self.visual_engine.image_to_video(out_img, out_vid, duration=4, orientation=orientation)
            return vid
        except Exception as e:
            print(f"[MediaEngine] İnfografik hatası: {e}")
            return None
    def generate_ai_video_clips(self, topic, count=6,
                                output_dir="assets/ai_videos", duration=5):
        """
        AI video klip üretimi.
        Öncelik: fal.ai → HuggingFace → Runway → Luma → Kling → Stability → Replicate
        """
        os.makedirs(output_dir, exist_ok=True)
        has_any = any([
            self.fal_key, self.hf_token, self.runway_key,
            self.luma_key, self.kling_key,
            self.stability_key, self.replicate_key,
        ])
        if not has_any:
            print("[AI Videos] Hiç AI video API key'i yok — stok videoya geçiliyor.")
            return []

        prompts = self._get_ai_prompts(topic)
        clips = []

        for i in range(min(count, len(prompts))):
            if len(clips) >= count:
                break
            out = os.path.join(output_dir, f"ai_clip_{i}.mp4")
            prompt = prompts[i]

            services = [
                ("fal.ai",      lambda p, o: self._generate_fal_video(p, o, duration)),
                ("HuggingFace", lambda p, o: self._generate_hf_video(p, o, duration)),
                ("Runway",      lambda p, o: self._generate_runway_video(p, o, duration)),
                ("Luma",        lambda p, o: self._generate_luma_video(p, o, duration)),
                ("Kling",       lambda p, o: self._generate_kling_video_v2(p, o, duration)),
                ("Stability",   lambda p, o: self._generate_stability_video(p, o, duration)),
                ("Replicate",   lambda p, o: self._generate_replicate_video(p, o, duration)),
            ]
            for svc_name, svc_fn in services:
                try:
                    print(f"[AI Videos] {svc_name} deneniyor (klip {i+1}/{count})...")
                    result = svc_fn(prompt, out)
                    if result and os.path.exists(result) and os.path.getsize(result) > 50_000:
                        clips.append(result)
                        print(f"[AI Videos] ✅ {svc_name} klip {i+1} hazır")
                        break
                except Exception as e:
                    print(f"[AI Videos] {svc_name}: {e}")
            else:
                print(f"[AI Videos] ⚠️ Klip {i+1} tüm servisler başarısız")

        print(f"[AI Videos] Toplam {len(clips)}/{count} AI klip hazır")
        return clips

    def _download_url(self, url, output_path):
        if not url:
            return None
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            r = requests.get(url, stream=True, timeout=120)
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk:
                            f.write(chunk)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 50_000:
                    return output_path
        except Exception as e:
            print(f"[Download] {e}")
        return None

    def _generate_fal_video(self, prompt, output_path, duration=5):
        if not self.fal_key:
            return None
        try:
            headers = {"Authorization": f"Key {self.fal_key}",
                       "Content-Type": "application/json"}
            r = requests.post(
                "https://fal.run/fal-ai/kling-video/v2/master/text-to-video",
                headers=headers,
                json={"prompt": prompt, "duration": str(min(duration, 5)),
                      "aspect_ratio": "16:9"},
                timeout=30,
            )
            if r.status_code != 200:
                r = requests.post(
                    "https://fal.run/fal-ai/minimax-video/v1/text-to-video",
                    headers=headers,
                    json={"prompt": prompt, "duration": 6},
                    timeout=30,
                )
            if r.status_code == 200:
                resp = r.json()
                vurl = (resp.get("video", {}).get("url")
                        or resp.get("output", {}).get("video_url"))
                if vurl:
                    return self._download_url(vurl, output_path)
                req_id = resp.get("request_id")
                if req_id:
                    base = "https://queue.fal.run/fal-ai/kling-video/v2/master/text-to-video"
                    for _ in range(60):
                        time.sleep(5)
                        sr = requests.get(f"{base}/requests/{req_id}",
                                          headers=headers, timeout=15)
                        if sr.status_code == 200:
                            sd = sr.json()
                            if sd.get("status") == "COMPLETED":
                                vurl = (sd.get("output", {}).get("video", {}).get("url")
                                        or sd.get("output", {}).get("video_url"))
                                if vurl:
                                    return self._download_url(vurl, output_path)
                                break
                            elif sd.get("status") == "FAILED":
                                break
        except Exception as e:
            print(f"[fal.ai] {e}")
        return None

    def _generate_hf_video(self, prompt, output_path, duration=5):
        if not self.hf_token:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            models = ["ali-vilab/text-to-video-ms-1.7b",
                      "damo-vilab/text-to-video-ms-1.7b"]
            for model in models:
                r = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=headers,
                    json={"inputs": prompt,
                          "parameters": {"num_frames": duration * 8,
                                         "num_inference_steps": 25}},
                    timeout=120,
                )
                if r.status_code == 200 and len(r.content) > 50_000:
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(r.content)
                    if os.path.getsize(output_path) > 50_000:
                        return output_path
                elif r.status_code == 503:
                    time.sleep(20)
        except Exception as e:
            print(f"[HuggingFace] {e}")
        return None

    def _generate_runway_video(self, prompt, output_path, duration=5):
        if not self.runway_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.runway_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06",
            }
            r = requests.post(
                "https://api.dev.runwayml.com/v1/image_to_video",
                headers=headers,
                json={"promptText": prompt, "model": "gen3a_turbo",
                      "duration": min(duration, 5), "ratio": "1280:720"},
                timeout=30,
            )
            if r.status_code in (200, 201):
                task_id = r.json().get("id")
                if task_id:
                    for _ in range(60):
                        time.sleep(5)
                        sr = requests.get(
                            f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                            headers=headers, timeout=15)
                        if sr.status_code == 200:
                            sd = sr.json()
                            if sd.get("status") == "SUCCEEDED":
                                outputs = sd.get("output", [])
                                if outputs:
                                    return self._download_url(outputs[0], output_path)
                                break
                            elif sd.get("status") == "FAILED":
                                break
        except Exception as e:
            print(f"[Runway] {e}")
        return None

    def _generate_luma_video(self, prompt, output_path, duration=5):
        if not self.luma_key:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.luma_key}",
                       "Content-Type": "application/json"}
            r = requests.post(
                "https://api.lumalabs.ai/dream-machine/v1/generations",
                headers=headers,
                json={"prompt": prompt, "aspect_ratio": "16:9", "loop": False},
                timeout=30,
            )
            if r.status_code in (200, 201):
                gen_id = r.json().get("id")
                if gen_id:
                    for _ in range(60):
                        time.sleep(5)
                        sr = requests.get(
                            f"https://api.lumalabs.ai/dream-machine/v1/generations/{gen_id}",
                            headers=headers, timeout=15)
                        if sr.status_code == 200:
                            sd = sr.json()
                            if sd.get("state") == "completed":
                                vurl = sd.get("assets", {}).get("video")
                                if vurl:
                                    return self._download_url(vurl, output_path)
                                break
                            elif sd.get("state") == "failed":
                                break
        except Exception as e:
            print(f"[Luma] {e}")
        return None

    def _generate_kling_video_v2(self, prompt, output_path, duration=5):
        api_key = self.kling_key
        if not api_key:
            return None
        try:
            headers = {"Authorization": f"Bearer {api_key}",
                       "Content-Type": "application/json"}
            r = requests.post(
                "https://api.klingai.com/v1/videos/text2video",
                headers=headers,
                json={"prompt": prompt, "duration": str(min(duration, 5)),
                      "aspect_ratio": "16:9", "model_name": "kling-v2"},
                timeout=30,
            )
            if r.status_code == 200:
                task_id = r.json().get("data", {}).get("task_id")
                if task_id:
                    for _ in range(60):
                        time.sleep(5)
                        sr = requests.get(
                            f"https://api.klingai.com/v1/videos/text2video/{task_id}",
                            headers=headers, timeout=15)
                        if sr.status_code == 200:
                            sd = sr.json().get("data", {})
                            if sd.get("task_status") == "succeed":
                                works = sd.get("task_result", {}).get("videos", [])
                                if works:
                                    return self._download_url(works[0].get("url"), output_path)
                                break
                            elif sd.get("task_status") == "failed":
                                break
        except Exception as e:
            print(f"[Kling] {e}")
        return None

    def _generate_stability_video(self, prompt, output_path, duration=5):
        if not self.stability_key:
            return None
        try:
            img_path = output_path.replace(".mp4", "_init.png")
            r = requests.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={"Authorization": f"Bearer {self.stability_key}",
                         "Accept": "image/*"},
                data={"prompt": prompt, "output_format": "png",
                      "aspect_ratio": "16:9"},
                timeout=30,
            )
            if r.status_code == 200:
                with open(img_path, "wb") as f:
                    f.write(r.content)
                with open(img_path, "rb") as f:
                    vr = requests.post(
                        "https://api.stability.ai/v2beta/image-to-video",
                        headers={"Authorization": f"Bearer {self.stability_key}"},
                        files={"image": ("image.png", f, "image/png")},
                        data={"seed": random.randint(0, 999999),
                              "cfg_scale": 1.8, "motion_bucket_id": 127},
                        timeout=30,
                    )
                if vr.status_code == 200:
                    gen_id = vr.json().get("id")
                    if gen_id:
                        for _ in range(30):
                            time.sleep(10)
                            rr = requests.get(
                                f"https://api.stability.ai/v2beta/image-to-video/result/{gen_id}",
                                headers={"Authorization": f"Bearer {self.stability_key}",
                                         "Accept": "video/*"},
                                timeout=30,
                            )
                            if rr.status_code == 200:
                                with open(output_path, "wb") as f:
                                    f.write(rr.content)
                                if os.path.exists(img_path):
                                    os.remove(img_path)
                                return output_path if os.path.getsize(output_path) > 50_000 else None
                            elif rr.status_code != 202:
                                break
        except Exception as e:
            print(f"[Stability] {e}")
        return None

    def _generate_replicate_video(self, prompt, output_path, duration=5):
        if not self.replicate_key:
            return None
        try:
            headers = {"Authorization": f"Token {self.replicate_key}",
                       "Content-Type": "application/json"}
            r = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={
                    "version": "9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351",
                    "input": {"prompt": prompt, "num_frames": duration * 6,
                              "width": 1280, "height": 720,
                              "num_inference_steps": 25}
                },
                timeout=30,
            )
            if r.status_code in (200, 201):
                pred_id = r.json().get("id")
                if pred_id:
                    for _ in range(60):
                        time.sleep(5)
                        sr = requests.get(
                            f"https://api.replicate.com/v1/predictions/{pred_id}",
                            headers=headers, timeout=15)
                        if sr.status_code == 200:
                            sd = sr.json()
                            if sd.get("status") == "succeeded":
                                output = sd.get("output")
                                vurl = output[0] if isinstance(output, list) else output
                                if vurl:
                                    return self._download_url(vurl, output_path)
                                break
                            elif sd.get("status") == "failed":
                                break
        except Exception as e:
            print(f"[Replicate] {e}")
        return None

    # ── Eski API Uyumu ──────────────────────────────────────────────
    def generate_stability_video(self, prompt, output_path, duration=5):
        return self._generate_stability_video(prompt, output_path, duration)

    def generate_replicate_video(self, prompt, output_path, duration=5):
        return self._generate_replicate_video(prompt, output_path, duration)

    def generate_kling_video(self, prompt, output_path, duration=5):
        return self._generate_kling_video_v2(prompt, output_path, duration)

    def _animate_image_to_video(self, image_path, output_path, duration=5):
        try:
            from moviepy.editor import VideoClip
            import numpy as np
            img = Image.open(image_path)
            w, h = img.size
            tw = int(h * 9 / 16) if w / h > 9 / 16 else w
            th = int(w * 16 / 9) if w / h < 9 / 16 else h
            img_r = img.resize((tw, th))

            def make_frame(t):
                progress = t / duration
                zoom = 1.0 + 0.05 * progress
                nw = int(tw / zoom)
                nh = int(th / zoom)
                x0 = (tw - nw) // 2
                y0 = (th - nh) // 2
                crop = img_r.crop((x0, y0, x0 + nw, y0 + nh))
                return np.array(crop.resize((1080, 1920)))

            clip = VideoClip(make_frame, duration=duration)
            clip.write_videofile(output_path, fps=24, codec="libx264",
                                 audio=False, logger=None)
            clip.close()
            if os.path.exists(image_path):
                os.remove(image_path)
            return output_path
        except Exception as e:
            print(f"[Animation] {e}")
            return None

    # ══════════════════════════════════════════════════════════════
    #  AI FALLBACK GÖRÜNTÜLER — Pollinations.ai (key gerekmez)
    # ══════════════════════════════════════════════════════════════
    def generate_ai_fallback_images(self, topic, count=3,
                                    output_dir="assets/ai_fallback"):
        os.makedirs(output_dir, exist_ok=True)
        prompts = [
            f"futuristic electric car driving on highway at sunset, cinematic 4k, no text, {topic}",
            "EV battery technology close up, laboratory, lithium cells, futuristic blue glow, no text",
            "electric vehicle charging station at night, city lights, cyberpunk, no text",
            "modern EV dashboard holographic interface, technology dark background, no text",
            "aerial view electric car on winding road, mountains, golden hour, cinematic, no text",
            "electric motor engine cross section, magnets spinning, blue energy glow, no text",
        ]
        paths = []
        for i in range(min(count, len(prompts))):
            enc = urllib.parse.quote(prompts[i])
            url = (
                f"https://image.pollinations.ai/prompt/{enc}"
                f"?width=1920&height=1080&seed={random.randint(1, 999999)}"
                f"&nologo=true&negative=blurry,text,watermark,low%20quality,people"
            )
            out = os.path.join(output_dir, f"ai_fallback_{i}.jpg")
            try:
                print(f"[Pollinations] AI HD görüntü {i+1}/{count}...")
                r = requests.get(url, timeout=60)
                if r.status_code == 200:
                    with open(out, "wb") as f:
                        f.write(r.content)
                    paths.append(out)
                    print(f"[Pollinations] ✅ {out}")
            except Exception as e:
                print(f"[Pollinations] {e}")
        return paths

    # ══════════════════════════════════════════════════════════════
    #  THUMBNAIL
    # ══════════════════════════════════════════════════════════════
    def generate_thumbnail(self, video_path, title, output_path,
                           channel_name="EVCARIX",
                           slogan="No hype. Just numbers."):
        from PIL import Image, ImageDraw, ImageFont
        from moviepy.editor import VideoFileClip
        try:
            clip = VideoFileClip(video_path)
            frame = clip.get_frame(min(2.0, clip.duration * 0.1))
            clip.close()
            img = Image.fromarray(frame).resize((1080, 1920))
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ov = ImageDraw.Draw(overlay)
            for y in range(img.height):
                alpha = int(220 * (y / img.height) ** 1.5)
                ov.rectangle([(0, y), (img.width, y + 1)], fill=(0, 0, 0, alpha))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            def get_font(name, size):
                for p in [f"fonts/{name}.ttf",
                           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
                return ImageFont.load_default()

            tf = get_font("Roboto-Bold", 100)
            cf = get_font("Roboto-Bold", 45)
            sf = get_font("Roboto-Regular", 32)

            words = title.split()
            lines, cur = [], ""
            for w in words:
                test = (cur + " " + w).strip()
                bbox = draw.textbbox((0, 0), test, font=tf)
                if bbox[2] - bbox[0] > 1000:
                    lines.append(cur)
                    cur = w
                else:
                    cur = test
            if cur:
                lines.append(cur)

            y_s = img.height // 2 - len(lines) * 55
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=tf)
                x = (img.width - (bbox[2] - bbox[0])) // 2
                for dx in range(-6, 7):
                    for dy in range(-6, 7):
                        draw.text((x + dx, y_s + dy), line, font=tf, fill=(0, 0, 0))
                draw.text((x, y_s), line, font=tf, fill=(255, 235, 0))
                y_s += 120

            footer = Image.new("RGBA", (img.width, 160), (0, 0, 0, 220))
            img_r = img.convert("RGBA")
            img_r.paste(footer, (0, img.height - 160), footer)
            img = img_r.convert("RGB")
            draw = ImageDraw.Draw(img)
            cb = draw.textbbox((0, 0), channel_name, font=cf)
            draw.text(((img.width - (cb[2] - cb[0])) // 2, img.height - 130),
                      channel_name, font=cf, fill=(50, 255, 100))
            sb = draw.textbbox((0, 0), slogan, font=sf)
            draw.text(((img.width - (sb[2] - sb[0])) // 2, img.height - 65),
                      slogan.upper(), font=sf, fill=(255, 255, 255))
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            # YouTube JPEG istiyor (kesin çözüm)
            img.save(output_path, "JPEG", quality=90)
            print(f"[MediaEngine] Thumbnail (JPEG): {output_path}")
            return output_path
        except Exception as e:
            print(f"[MediaEngine] Thumbnail hatası: {e}")
            return None
