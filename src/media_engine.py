"""
Evcarix MediaEngine
HD Video Öncelik: Tesla CDN → Marka Bazlı Pexels → Pixabay → FreeVideo → AI → Pollinations

Global Marka Kapsamı: Tesla, BYD, Hyundai, Kia, BMW, Mercedes, Audi, VW, Volvo, Polestar,
Rivian, Lucid, NIO, Xpeng, Li Auto, Ford, GM, Stellantis, Nissan, Honda, Toyota, Subaru,
Mazda, Mitsubishi, Renault, Peugeot, Citroën, Opel, Fiat, Alfa Romeo, Jaguar, Land Rover,
Porsche, Ferrari, Lamborghini, Maserati, Genesis, Vinfast, SAIC, Geely, Great Wall, Leapmotor,
Zeekr, Avatr, BYD Yangwang, ChargePoint, ABB, Tritium, CATL, Panasonic, QuantumScape + daha fazlası
"""
import os
import re
import json
import time
import random
import requests
import urllib.parse
from pathlib import Path
from PIL import Image
from src.voice_engine import VoiceEngine
from dotenv import load_dotenv

load_dotenv()


# ═══════════════════════════════════════════════════════════════════
#  GLOBAL MARKA VERİTABANI — 50+ Marka
#  cdn_videos: Doğrulanmış çalışan doğrudan CDN URL'leri (Tesla only)
#  pexels_queries: Marka adını içeren Pexels arama sorguları
# ═══════════════════════════════════════════════════════════════════
GLOBAL_BRAND_DB = {

    # ── AMERİKAN MARKALAR ────────────────────────────────────────────
    "nrel": {
        "keywords": ["nrel", "battery lab", "renewable energy laboratory", "clean energy lab"],
        "cdn_videos": [
            "https://www.nrel.gov/news/video/assets/videos/battery-testing.mp4",
            "https://www.nrel.gov/news/video/assets/videos/wind-energy.mp4",
            "https://www.nrel.gov/news/video/assets/videos/solar-research.mp4",
        ],
        "pexels_queries": ["battery laboratory research 4k", "renewable energy tech"],
        "priority": 1,
    },
    "catl": {
        "keywords": ["catl", "battery cell", "ev battery manufacturing"],
        "cdn_videos": [],
        "pexels_queries": ["battery factory automation 4k", "lithium battery production"],
        "priority": 2,
    },
    "nrel": {
        "keywords": ["nrel", "battery lab", "renewable energy laboratory", "clean energy lab"],
        "cdn_videos": [
            "https://www.nrel.gov/news/video/assets/videos/battery-testing.mp4",
            "https://www.nrel.gov/news/video/assets/videos/wind-energy.mp4",
            "https://www.nrel.gov/news/video/assets/videos/solar-research.mp4",
        ],
        "pexels_queries": ["battery laboratory research 4k", "renewable energy tech"],
        "priority": 1,
    },
    "catl": {
        "keywords": ["catl", "battery cell", "ev battery manufacturing"],
        "cdn_videos": [],
        "pexels_queries": ["battery factory automation 4k", "lithium battery production"],
        "priority": 2,
    },
    "tesla": {
        "keywords": ["tesla", "model 3", "model y", "model s", "model x",
                     "cybertruck", "supercharger", "autopilot", "fsd", "megapack"],
        "cdn_videos": [
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-Y-Desktop-NA.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-3-Desktop-NA.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Model-S-Homepage-Desktop-LHD-01.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Megapack-Homepage-Desktop.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-X-Desktop.mp4",
        ],
        "pexels_queries": [
            "Tesla Model Y electric car driving highway 4k",
            "Tesla Model 3 exterior cinematic HD",
            "Tesla supercharger station night 4k",
            "Tesla electric vehicle interior dashboard",
            "Tesla cybertruck futuristic exterior",
        ],
        "priority": 1,
    },
    "rivian": {
        "keywords": ["rivian", "r1t", "r1s", "r2", "rivian truck", "rivian suv"],
        "cdn_videos": [],
        "pexels_queries": [
            "Rivian R1T electric truck adventure outdoor 4k",
            "Rivian electric pickup truck off road HD",
            "electric truck adventure outdoor 4k",
        ],
        "priority": 2,
    },
    "lucid": {
        "keywords": ["lucid", "lucid air", "lucid gravity", "lucid motors"],
        "cdn_videos": [],
        "pexels_queries": [
            "Lucid Air luxury electric sedan exterior 4k",
            "luxury electric car silver exterior driving HD",
            "premium electric vehicle aerodynamic design",
        ],
        "priority": 2,
    },
    "ford": {
        "keywords": ["ford", "mustang mach-e", "mach-e", "f-150 lightning",
                     "f150 lightning", "ford electric", "ford ev"],
        "cdn_videos": [],
        "pexels_queries": [
            "Ford Mustang Mach-E electric SUV exterior 4k",
            "Ford F-150 Lightning electric truck HD",
            "Ford electric vehicle modern design",
        ],
        "priority": 2,
    },
    "gm_chevrolet": {
        "keywords": ["chevrolet", "chevy", "silverado ev", "blazer ev",
                     "equinox ev", "gm electric", "general motors"],
        "cdn_videos": [],
        "pexels_queries": [
            "Chevrolet Silverado EV electric truck exterior",
            "GM electric vehicle Blazer EV exterior HD",
            "Chevrolet electric car modern 4k",
        ],
        "priority": 3,
    },
    "cadillac": {
        "keywords": ["cadillac", "lyriq", "celestiq", "cadillac ev"],
        "cdn_videos": [],
        "pexels_queries": [
            "Cadillac Lyriq luxury electric SUV 4k",
            "luxury electric SUV dark exterior night",
        ],
        "priority": 3,
    },
    "stellantis_jeep": {
        "keywords": ["jeep", "wrangler 4xe", "jeep electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Jeep Wrangler 4xe plug-in hybrid off road",
            "Jeep electric off-road adventure 4k",
        ],
        "priority": 3,
    },

    # ── KORECE MARKALAR ──────────────────────────────────────────────
    "hyundai": {
        "keywords": ["hyundai", "ioniq", "ioniq 5", "ioniq 6", "ioniq 9",
                     "nexo", "kona electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Hyundai IONIQ 5 electric car exterior driving 4k",
            "Hyundai IONIQ 6 sedan electric HD",
            "Hyundai electric vehicle modern design cinematic",
            "IONIQ 5 charging station night",
        ],
        "priority": 1,
    },
    "kia": {
        "keywords": ["kia", "ev6", "ev9", "ev3", "niro ev", "soul ev", "kia electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Kia EV6 electric car exterior driving 4k",
            "Kia EV9 SUV electric cinematic HD",
            "Kia electric vehicle futuristic design",
        ],
        "priority": 1,
    },
    "genesis": {
        "keywords": ["genesis", "gv60", "gv70e", "g80e", "genesis electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Genesis GV60 luxury electric SUV 4k",
            "Genesis electric vehicle premium exterior",
        ],
        "priority": 3,
    },

    # ── ALMAN MARKALAR ───────────────────────────────────────────────
    "bmw": {
        "keywords": ["bmw", "bmw i4", "bmw ix", "bmw i5", "bmw i7",
                     "bmw i3", "bmw electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "BMW iX electric SUV exterior driving 4k",
            "BMW i4 electric sedan cinematic HD",
            "BMW electric car luxury modern design",
            "BMW i7 limousine electric exterior night",
        ],
        "priority": 1,
    },
    "mercedes": {
        "keywords": ["mercedes", "eqs", "eqe", "eqb", "eqa", "eqc",
                     "eqs suv", "mercedes electric", "amg eq"],
        "cdn_videos": [],
        "pexels_queries": [
            "Mercedes EQS electric luxury sedan exterior 4k",
            "Mercedes EQE electric car driving HD",
            "Mercedes Benz electric vehicle modern cinematic",
            "Mercedes AMG EQ performance electric",
        ],
        "priority": 1,
    },
    "audi": {
        "keywords": ["audi", "e-tron", "etron", "q4 etron", "q6 etron",
                     "audi electric", "rs etron gt"],
        "cdn_videos": [],
        "pexels_queries": [
            "Audi e-tron electric SUV exterior driving 4k",
            "Audi Q4 e-tron electric cinematic HD",
            "Audi electric vehicle luxury design",
            "Audi RS e-tron GT performance electric",
        ],
        "priority": 1,
    },
    "volkswagen": {
        "keywords": ["volkswagen", "vw", "id.4", "id.3", "id.7", "id.buzz",
                     "id4", "id3", "id7"],
        "cdn_videos": [],
        "pexels_queries": [
            "Volkswagen ID.4 electric SUV exterior 4k",
            "VW ID.3 electric hatchback driving HD",
            "Volkswagen ID Buzz electric van retro",
            "VW electric vehicle family modern design",
        ],
        "priority": 1,
    },
    "porsche": {
        "keywords": ["porsche", "taycan", "macan electric", "porsche electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Porsche Taycan electric sports car driving 4k",
            "Porsche electric car performance cinematic HD",
            "Porsche Taycan turbo exterior night",
        ],
        "priority": 2,
    },

    # ── İSKANDİNAV MARKALAR ─────────────────────────────────────────
    "volvo": {
        "keywords": ["volvo", "volvo ex30", "volvo ex40", "volvo ec40",
                     "volvo ex90", "volvo electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Volvo EX90 electric SUV exterior Scandinavian 4k",
            "Volvo electric car safety modern design HD",
            "Volvo EX30 compact electric urban driving",
        ],
        "priority": 2,
    },
    "polestar": {
        "keywords": ["polestar", "polestar 2", "polestar 3", "polestar 4",
                     "polestar electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Polestar 2 electric sedan exterior cinematic 4k",
            "Polestar 3 electric SUV Scandinavian design HD",
            "Polestar electric vehicle minimalist design",
        ],
        "priority": 2,
    },

    # ── ÇİN MARKALARI ───────────────────────────────────────────────
    "byd": {
        "keywords": ["byd", "byd seal", "byd atto", "byd han", "byd tang",
                     "byd dolphin", "byd seagull", "byd electric", "yangwang"],
        "cdn_videos": [],
        "pexels_queries": [
            "BYD Seal electric sedan exterior driving 4k",
            "BYD Atto 3 electric SUV modern HD",
            "BYD electric vehicle China modern design",
            "BYD Han electric luxury sedan",
        ],
        "priority": 1,
    },
    "nio": {
        "keywords": ["nio", "nio et5", "nio et7", "nio es6", "nio es8",
                     "nio el6", "nio electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "NIO ET5 electric sedan exterior 4k",
            "NIO electric car China premium design HD",
            "NIO battery swap station technology",
        ],
        "priority": 2,
    },
    "xpeng": {
        "keywords": ["xpeng", "xpeng p7", "xpeng g9", "xpeng g6",
                     "xpeng electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Xpeng P7 electric sedan autonomous driving 4k",
            "Xpeng electric vehicle China tech HD",
        ],
        "priority": 3,
    },
    "li_auto": {
        "keywords": ["li auto", "li one", "li l9", "li l7", "lixiang"],
        "cdn_videos": [],
        "pexels_queries": [
            "Li Auto L9 electric hybrid SUV China 4k",
            "Li Auto extended range electric vehicle HD",
        ],
        "priority": 3,
    },
    "zeekr": {
        "keywords": ["zeekr", "zeekr 001", "zeekr x", "zeekr electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Zeekr 001 electric shooting brake exterior 4k",
            "Zeekr electric vehicle Geely premium",
        ],
        "priority": 3,
    },
    "leapmotor": {
        "keywords": ["leapmotor", "leap motor", "c10", "t03"],
        "cdn_videos": [],
        "pexels_queries": [
            "Leapmotor electric vehicle China affordable",
            "Chinese electric car compact urban",
        ],
        "priority": 4,
    },

    # ── JAPON MARKALAR ──────────────────────────────────────────────
    "nissan": {
        "keywords": ["nissan", "nissan leaf", "nissan ariya", "nissan electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Nissan Ariya electric SUV exterior driving 4k",
            "Nissan Leaf electric hatchback city HD",
            "Nissan electric vehicle modern design",
        ],
        "priority": 2,
    },
    "toyota": {
        "keywords": ["toyota", "bz4x", "bz3", "toyota electric", "toyota ev"],
        "cdn_videos": [],
        "pexels_queries": [
            "Toyota bZ4X electric SUV exterior driving 4k",
            "Toyota electric vehicle modern design HD",
        ],
        "priority": 2,
    },
    "honda": {
        "keywords": ["honda", "honda e", "prologue", "honda electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Honda Prologue electric SUV exterior 4k",
            "Honda electric vehicle modern design HD",
        ],
        "priority": 3,
    },
    "subaru": {
        "keywords": ["subaru", "solterra", "subaru electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Subaru Solterra electric SUV outdoor adventure",
            "Subaru electric all wheel drive",
        ],
        "priority": 3,
    },

    # ── FRANSIZ MARKALAR ────────────────────────────────────────────
    "renault": {
        "keywords": ["renault", "renault zoe", "megane e-tech", "renault electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Renault Megane E-Tech electric hatchback 4k",
            "Renault ZOE electric city car HD",
            "Renault electric vehicle French design",
        ],
        "priority": 3,
    },
    "peugeot": {
        "keywords": ["peugeot", "e-208", "e-2008", "e-308", "peugeot electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Peugeot e-208 electric hatchback city",
            "Peugeot electric vehicle French design 4k",
        ],
        "priority": 3,
    },

    # ── İNGİLİZ MARKALAR ────────────────────────────────────────────
    "jaguar": {
        "keywords": ["jaguar", "jaguar i-pace", "jaguar electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Jaguar I-PACE electric SUV luxury exterior 4k",
            "Jaguar electric vehicle British design HD",
        ],
        "priority": 3,
    },

    # ── İTALYAN MARKALAR ────────────────────────────────────────────
    "lamborghini": {
        "keywords": ["lamborghini", "lanzador", "lamborghini ev",
                     "lamborghini electric", "lamborghini hybrid", "lamborghini prototype"],
        "cdn_videos": [],
        "pexels_queries": [
            "Lamborghini supercar luxury sports car exterior cinematic 4k",
            "exotic supercar futuristic electric hypercar",
            "Italian supercar performance luxury design HD",
            "high performance sports car aerodynamic design",
        ],
        "priority": 2,
    },
    "ferrari": {
        "keywords": ["ferrari", "ferrari sf90", "ferrari electric", "ferrari hybrid",
                     "ferrari purosangue"],
        "cdn_videos": [],
        "pexels_queries": [
            "Ferrari luxury sports car exterior cinematic 4k",
            "Ferrari SF90 hybrid supercar performance",
            "Italian luxury supercar red exterior driving HD",
        ],
        "priority": 2,
    },
    "maserati": {
        "keywords": ["maserati", "maserati grecale", "maserati granturismo",
                     "maserati folgore", "maserati electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Maserati luxury electric car exterior cinematic 4k",
            "Maserati GranTurismo Folgore electric performance",
            "Italian luxury electric vehicle premium design",
        ],
        "priority": 3,
    },
    "alfa_romeo": {
        "keywords": ["alfa romeo", "alfa milan", "alfa junior", "alfa romeo electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "Alfa Romeo electric car sporty Italian design 4k",
            "Alfa Romeo Milano electric compact SUV",
        ],
        "priority": 3,
    },

    # ── VİETNAM MARKALARI ────────────────────────────────────────────
    "vinfast": {
        "keywords": ["vinfast", "vf8", "vf9", "vf6", "vinfast electric"],
        "cdn_videos": [],
        "pexels_queries": [
            "VinFast VF8 electric SUV exterior 4k",
            "VinFast electric vehicle Vietnam modern",
        ],
        "priority": 3,
    },

    # ── ŞARJ & ALTYAPI ──────────────────────────────────────────────
    "chargepoint": {
        "keywords": ["chargepoint", "charging network", "ev charging station",
                     "dc fast charging", "level 2 charging"],
        "cdn_videos": [],
        "pexels_queries": [
            "EV charging station network city night 4k",
            "electric car charging plug cable close up HD",
            "DC fast charging station modern",
        ],
        "priority": 2,
    },
    "abb_charging": {
        "keywords": ["abb", "terra 360", "fast charger", "charging infrastructure"],
        "cdn_videos": [],
        "pexels_queries": [
            "electric vehicle fast charging station technology 4k",
            "EV charger infrastructure modern design HD",
        ],
        "priority": 3,
    },

    # ── PİL & TEKNOLOJİ ─────────────────────────────────────────────
    "catl": {
        "keywords": ["catl", "lfp", "nmc", "battery cell", "battery pack",
                     "solid state battery", "sodium battery"],
        "cdn_videos": [],
        "pexels_queries": [
            "lithium battery cells laboratory technology 4k",
            "EV battery pack manufacturing assembly HD",
            "battery technology research laboratory blue glow",
            "solid state battery futuristic energy",
        ],
        "priority": 2,
    },
    "panasonic_battery": {
        "keywords": ["panasonic", "4680 cell", "cylindrical cell", "battery manufacturer"],
        "cdn_videos": [],
        "pexels_queries": [
            "battery cell factory production line 4k",
            "lithium battery technology manufacturing HD",
        ],
        "priority": 3,
    },
}

# ── Genel EV içeriği için Tesla CDN videoları ─────────────────────
OEM_CDN_FALLBACK = [
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-Y-Desktop-NA.mp4",
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Megapack-Homepage-Desktop.mp4",
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-3-Desktop-NA.mp4",
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Model-S-Homepage-Desktop-LHD-01.mp4",
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-X-Desktop.mp4",
]

# Geriye uyumluluk için alias
OEM_BRAND_VIDEOS = {
    k: {"keywords": v["keywords"], "videos": v["cdn_videos"], "priority": v["priority"]}
    for k, v in GLOBAL_BRAND_DB.items() if v["cdn_videos"]
}
OEM_GENERAL_VIDEOS = OEM_CDN_FALLBACK

# Kategori bazlı marka öncelikleri
CATEGORY_OEM_PRIORITY = {
    "battery_science":  ["catl", "tesla", "byd", "bmw", "panasonic_battery"],
    "range_tests":      ["tesla", "hyundai", "lucid", "byd", "bmw"],
    "charging":         ["chargepoint", "tesla", "abb_charging", "bmw", "volkswagen"],
    "comparisons":      ["tesla", "byd", "hyundai", "kia", "bmw", "mercedes"],
    "cost_ownership":   ["tesla", "volkswagen", "hyundai", "kia", "byd"],
    "market_data":      ["byd", "tesla", "volkswagen", "nio", "hyundai"],
    "infrastructure":   ["chargepoint", "tesla", "abb_charging", "volkswagen"],
    "education":        ["catl", "tesla", "bmw", "hyundai"],
    "trend":            ["tesla", "byd", "hyundai", "rivian", "lucid", "nio"],
    "interactive_tools": ["tesla", "bmw", "hyundai", "kia"],
}



class MediaEngine:
    def __init__(self):
        # Stok video API'leri
        self.pexels_api_key  = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")

        # AI video servisleri
        self.fal_key           = os.getenv("FAL_KEY") or os.getenv("FAL_API_KEY")
        self.hf_token          = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
        self.runway_key        = os.getenv("RUNWAY_API_KEY")
        self.luma_key          = os.getenv("LUMA_API_KEY")
        self.kling_key         = os.getenv("KLING_API_KEY") or os.getenv("KLING_ACCESS_KEY")
        self.stability_key     = os.getenv("STABILITY_API_KEY")
        self.replicate_key     = os.getenv("REPLICATE_API_KEY")

        # Geriye dönük uyum için alias'lar
        self.stability_api_key = self.stability_key
        self.replicate_api_key = self.replicate_key
        self.kling_access_key  = self.kling_key
        self.kling_secret_key  = os.getenv("KLING_SECRET_KEY")

        # Ses motoru
        self.voice_engine = VoiceEngine()

        # Kullanılan klip takip sistemi
        self.used_clips_file = "used_clips.json"
        self._load_used_clips()

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
        print(f"[MediaEngine] [Log] Daha once kullanilan klip sayisi: {len(self._used_clips)}")

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
            print(f"[MediaEngine] [Skip] {skipped} daha once kullanilan klip atlandi.")
        return fresh

    def mark_clips_as_used(self, paths: list):
        count = 0
        for p in paths:
            if p and os.path.exists(p):
                self._used_clips.add(self._get_clip_hash(p))
                count += 1
        self._save_used_clips()
        print(f"[MediaEngine] [OK] {count} klip 'kullanildi' olarak kaydedildi.")

    # ══════════════════════════════════════════════════════════════
    #  OEM MARKA BASИН KİTİ — HD Telifsiz Videolar
    # ══════════════════════════════════════════════════════════════
    def _detect_brands_in_topic(self, topic: str, category: str = None) -> list:
        """Konu metninden ilgili global markaları tespit eder (50+ marka)."""
        topic_lower = topic.lower()
        matched = []
        for brand, data in GLOBAL_BRAND_DB.items():
            for kw in data["keywords"]:
                if kw in topic_lower:
                    matched.append(brand)
                    break

        # Kategori bazlı öncelik
        cat_priority = CATEGORY_OEM_PRIORITY.get(category, [])
        if not matched and cat_priority:
            matched = cat_priority[:4]

        # Hiç eşleşme yoksa genel öncelik
        if not matched:
            matched = ["tesla", "byd", "hyundai", "bmw", "volkswagen"]

        # Önceliğe göre sırala
        matched.sort(key=lambda b: GLOBAL_BRAND_DB.get(b, {}).get("priority", 99))
        return matched

    def _get_brand_pexels_queries(self, topic: str, category: str = None) -> list:
        """Konuya göre marka bazlı Pexels sorguları döndürür."""
        brands = self._detect_brands_in_topic(topic, category)
        queries = []
        for brand in brands[:3]:  # En iyi 3 markadan sorgu al
            brand_data = GLOBAL_BRAND_DB.get(brand, {})
            brand_queries = brand_data.get("pexels_queries", [])
            if brand_queries:
                queries.append(random.choice(brand_queries))
        # Marka sorgularına ek genel EV sorguları ekle
        general = [
            "electric car driving highway cinematic 4k",
            "EV battery technology close up HD",
            "electric vehicle charging station night city",
            "electric car exterior modern design 4k",
        ]
        queries += general
        return queries

    def _download_from_oem(self, topic: str, output_dir: str,
                            count: int, category: str = None) -> list:
        """
        OEM marka basın kitlerinden HD video indirir.
        Önce CDN URL'leri dener; CDN listesi boşsa marka bazlı Pexels sorgusuna geçer.
        Bu sayede tüm 50+ marka için video indirilebilir, sadece Tesla değil.
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        brands = self._detect_brands_in_topic(topic, category)
        print(f"[OEM] Tespit edilen markalar: {brands[:4]}")

        for brand in brands:
            if len(paths) >= count:
                break
            brand_data = GLOBAL_BRAND_DB.get(brand, {})
            video_urls = list(brand_data.get("cdn_videos", []))  # CDN URL listesi
            random.shuffle(video_urls)

            cdn_success = False
            for url in video_urls:
                if len(paths) >= count:
                    break
                fname = f"oem_{brand}_{Path(url).stem[:35]}.mp4"
                out = os.path.join(output_dir, fname)

                # Önbellekte varsa kullan
                if os.path.exists(out) and os.path.getsize(out) > 200_000:
                    if self._get_clip_hash(out) not in self._used_clips:
                        paths.append(out)
                        cdn_success = True
                        print(f"[OEM] [Cache] Onbellekten: {fname}")
                        continue

                try:
                    print(f"[OEM] {brand.upper()} HD video indiriliyor: {fname}")
                    r = requests.get(
                        url, stream=True, timeout=30,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "video/mp4,video/*,*/*",
                            "Referer": "https://www.tesla.com/",
                        }
                    )
                    ct = r.headers.get("content-type", "")
                    if r.status_code == 200 and ("video" in ct or "octet-stream" in ct or not ct):
                        with open(out, "wb") as f:
                            downloaded = 0
                            for chunk in r.iter_content(1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    if downloaded > 300_000_000:  # max 300MB
                                        break
                        size = os.path.getsize(out)
                        if size > 200_000:  # min 200KB = gerçek video
                            paths.append(out)
                            cdn_success = True
                            print(f"[OEM] [OK] {fname} ({size//1024//1024}MB)")
                        else:
                            os.remove(out)
                            print(f"[OEM] [Error] Cok kucuk ({size} byte), atlandi")
                    else:
                        print(f"[OEM] HTTP {r.status_code} / content-type={ct}: {brand}")
                except Exception as e:
                    print(f"[OEM] {brand} hata: {e}")

            # ── CDN yoksa veya başarısızsa: Pexels marka sorgusu ────────────────
            # Bu sayede tüm markalar (BMW, Hyundai, Lamborghini vb.) için video gelir
            if not cdn_success and len(paths) < count:
                brand_queries = brand_data.get("pexels_queries", [])
                if brand_queries and self.pexels_api_key:
                    q = random.choice(brand_queries)
                    print(f"[OEM] {brand.upper()} CDN yok -> Pexels fallback: '{q[:60]}'")
                    try:
                        pex = self._download_from_pexels(
                            q, output_dir, 1, "landscape", category
                        )
                        pex_fresh = [p for p in pex
                                     if p and os.path.exists(p)
                                     and self._get_clip_hash(p) not in self._used_clips]
                        if pex_fresh:
                            paths.extend(pex_fresh[:1])
                            print(f"[OEM] [OK] {brand.upper()} Pexels'tan 1 klip alindi")
                    except Exception as e:
                        print(f"[OEM] {brand} Pexels fallback hata: {e}")

        print(f"[OEM] {len(paths)} HD marka videosu hazır")
        return paths

    # ══════════════════════════════════════════════════════════════
    #  PEXELS — CC0 Stok Video
    # ══════════════════════════════════════════════════════════════
    _IRRELEVANT_TAGS = {
        "fireplace","fire","flame","christmas","xmas","flower","flowers",
        "nature","forest","mountain","beach","ocean","sea","cooking",
        "food","kitchen","coffee","cat","dog","animal","baby","wedding",
        "yoga","meditation","fitness","gym","rain","snow","storm",
        "abstract","background","texture","pattern","paint","art",
        "waterfall","sunrise","timelapse","stars","space","sky",
    }
    _RELEVANT_TAGS = {
        "electric","ev","tesla","battery","charging","car","vehicle",
        "automobile","auto","automotive","transport","technology","drive",
        "highway","road","traffic","city","urban","motor","energy",
        "green","eco","future","innovation","speed","dashboard",
    }

    def _is_ev_related(self, video_data):
        tags = video_data.get("tags", []) or []
        tag_set = {t.lower() for t in tags if isinstance(t, str)}
        if tag_set & self._IRRELEVANT_TAGS:
            return False
        if tag_set & self._RELEVANT_TAGS:
            return True
        return True

    def _get_pexels_query(self, topic, category=None):
        """Önce marka bazlı, sonra kategoriye göre optimize Pexels sorgusu."""
        # 1. Marka bazlı sorgular (en yüksek öncelik)
        brand_queries = self._get_brand_pexels_queries(topic, category)
        if brand_queries:
            return random.choice(brand_queries[:3])  # İlk 3 marka sorgusundan seç

        # 2. Kategori bazlı fallback sorgular
        cat_queries = {
            "battery_science": [
                "lithium battery cell technology laboratory close up 4k",
                "EV battery pack assembly manufacturing HD",
                "solid state battery futuristic technology",
                "CATL battery research laboratory blue glow",
                "battery cell energy density technology",
            ],
            "range_tests": [
                "electric car driving highway aerial view 4k",
                "EV dashboard speedometer range display HD",
                "Tesla Model Y driving road cinematic 4k",
                "Hyundai IONIQ 5 highway driving range test",
                "electric vehicle winter snow driving range",
            ],
            "charging": [
                "Tesla supercharger station multiple cars night 4k",
                "EV fast charging plug cable close up HD",
                "DC fast charging station 350kW modern",
                "electric car charging network city night",
                "ChargePoint EV charging station network",
            ],
            "comparisons": [
                "multiple electric cars parked showroom 4k",
                "Tesla BYD Hyundai electric vehicle lineup HD",
                "car comparison test track aerial cinematic",
                "EV showroom interior premium modern design",
            ],
            "cost_ownership": [
                "electric car dealership showroom interior 4k",
                "car finance calculator business meeting HD",
                "money savings green technology investment",
                "family electric car purchase dealership",
            ],
            "market_data": [
                "electric vehicle factory production line 4k",
                "BYD Tesla factory manufacturing plant aerial",
                "global business data analytics dashboard HD",
                "EV automotive industry modern technology",
            ],
            "infrastructure": [
                "electric car charging network city night 4k",
                "solar panels renewable energy installation HD",
                "smart city electric vehicle charging station",
                "power grid electricity technology modern",
            ],
            "education": [
                "electric motor engine technology close up 4k",
                "car heat pump thermal visualization HD",
                "engineering blueprint technical automotive design",
                "battery chemistry laboratory research science",
            ],
            "trend": [
                "futuristic electric car driving cinematic 4k",
                "new electric vehicle launch reveal event",
                "modern EV exterior driving sunset golden hour",
                "electric car technology innovation 2025",
            ],
        }
        queries = cat_queries.get(category, [
            "electric car driving highway 4k cinematic",
            "EV battery technology close up HD",
            "electric vehicle charging station night",
            "Tesla BYD electric car modern",
            "EV dashboard display technology 4k",
        ])
        return random.choice(queries)

    def _download_from_pexels(self, query, output_dir, count,
                               orientation="landscape", category=None):
        if not self.pexels_api_key:
            return []
        q = self._get_pexels_query(query, category)
        headers = {"Authorization": self.pexels_api_key}
        page = random.randint(1, 8)
        url = (
            f"https://api.pexels.com/videos/search"
            f"?query={urllib.parse.quote(q)}"
            f"&per_page={count + 5}&page={page}"
            f"&orientation={orientation}"
            f"&size=large"  # HD kalite zorla
        )
        paths = []
        try:
            print(f"[Pexels] '{q}' (sayfa {page}, {orientation}) aranıyor...")
            r = requests.get(url, headers=headers, timeout=15)
            videos = r.json().get("videos", []) if r.status_code == 200 else []
            if not videos:
                r2 = requests.get(url.replace(f"page={page}", "page=1"),
                                  headers=headers, timeout=15)
                videos = r2.json().get("videos", []) if r2.status_code == 200 else []
            random.shuffle(videos)
            for i, vd in enumerate(videos):
                if len(paths) >= count:
                    break
                if not self._is_ev_related(vd):
                    continue
                files = sorted(vd.get("video_files", []),
                               key=lambda x: x.get("width", 0), reverse=True)
                # HD tercih: tam 1920px (4K > 1920px klipler montaji yavaslatir)
                hd_files = [f for f in files if f.get("width", 0) == 1920]
                if not hd_files:
                    hd_files = [f for f in files if 1280 <= f.get("width", 0) < 1920]
                if not hd_files:
                    hd_files = [f for f in files if f.get("width", 0) >= 1280]
                if not hd_files:
                    hd_files = files
                if not hd_files:
                    continue
                chosen = hd_files[0]
                q_slug = re.sub(r'[^\w]', '_', q)[:25]
                fname = f"pexels_{q_slug}_{page}_{i}.mp4"
                out = os.path.join(output_dir, fname)
                dl = requests.get(chosen["link"], stream=True, timeout=60)
                if dl.status_code == 200:
                    with open(out, "wb") as f:
                        for chunk in dl.iter_content(1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(out) > 100_000:
                        paths.append(out)
                        print(f"[Pexels] ✅ {fname} ({chosen.get('width')}x{chosen.get('height')})")
        except Exception as e:
            print(f"[Pexels] Hata: {e}")
        return paths

    # ══════════════════════════════════════════════════════════════
    #  PIXABAY — CC0 Stok Video
    # ══════════════════════════════════════════════════════════════
    def _download_from_pixabay(self, query, output_dir, count,
                                orientation="horizontal", category=None):
        if not self.pixabay_api_key:
            return []
        cat_q = {
            "battery_science":  ["lithium battery cell", "battery technology laboratory", "battery factory"],
            "range_tests":      ["electric car highway driving", "dashboard speedometer", "winter road driving"],
            "charging":         ["EV charging station", "electric car charging", "fast charging technology"],
            "comparisons":      ["electric vehicles showroom", "car comparison", "cars parked modern"],
            "cost_ownership":   ["car dealership", "money finance business", "electric car purchase"],
            "market_data":      ["factory production line", "business analytics", "global network technology"],
            "infrastructure":   ["solar panels energy", "power grid", "smart city charging"],
            "education":        ["electric motor technology", "engineering laboratory", "heat pump technology"],
            "trend":            ["electric car futuristic", "new EV exterior", "modern electric vehicle"],
        }
        q = random.choice(cat_q.get(category, [
            "electric car", "EV charging", "electric vehicle technology",
            "EV battery", "electric car driving"
        ]))
        pix_or = "vertical" if orientation == "portrait" else "horizontal"
        page = random.randint(1, 5)
        params = {
            "key": self.pixabay_api_key,
            "q": q,
            "video_type": "film",
            "orientation": pix_or,
            "order": "popular",
            "per_page": count + 5,
            "page": page,
            "safesearch": "true",
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
                                  params=params, timeout=15)
                hits = r2.json().get("hits", []) if r2.status_code == 200 else []
            random.shuffle(hits)
            for i, hit in enumerate(hits[:count + 2]):
                if len(paths) >= count:
                    break
                vids = hit.get("videos", {})
                # HD kalite önceliği: large → medium → small
                chosen = None
                for qual in ["large", "medium", "small", "tiny"]:
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
                q_slug = re.sub(r'[^\w]', '_', q)[:25]
                fname = f"pixabay_{q_slug}_{page}_{i}.mp4"
                out = os.path.join(output_dir, fname)
                dl = requests.get(chosen["url"], stream=True, timeout=60)
                if dl.status_code == 200:
                    with open(out, "wb") as f:
                        for chunk in dl.iter_content(1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(out) > 100_000:
                        paths.append(out)
                        print(f"[Pixabay] ✅ {fname} ({chosen.get('width')}x{chosen.get('height')})")
        except Exception as e:
            print(f"[Pixabay] Hata: {e}")
        return paths

    # ══════════════════════════════════════════════════════════════
    #  ANA İNDİRME — TÜM KAYNAKLAR BİRLEŞİK
    # ══════════════════════════════════════════════════════════════
    def download_stock_videos(self, query, output_dir="assets/temp_videos",
                              count=6, orientation="portrait", category=None,
                              plan=None):
        """
        HD video indirme — öncelik sırası:
        1. OEM Scraper   — 20+ marka press/newsroom sayfaları (telifsiz, editoryal)
        2. OEM Static    — Tesla CDN sabit URL'leri (yedek)
        3. Pexels HD     — Marka bazlı sorgular (API key gerekli)
        4. Pixabay HD    — Kategori bazlı sorgular (API key gerekli)
        5. FreeVideo     — Coverr, Videvo, Mixkit, Dareful (ücretsiz, key yok)
        6. Pexels extra  — Farklı genel fallback sorgusu
        7. AI Video      — fal.ai → HuggingFace → Runway → Luma → Kling → Stability → Replicate
        8. AI Görüntü    — Pollinations.ai → ffmpeg → video klip (kesin son çare)
        """
        os.makedirs(output_dir, exist_ok=True)
        all_paths = []

        # ── ADIM 1: YouTube Creative Commons (EN YÜKSEK ÖNCELİK - HD KALİTE) ──
        print(f"[MediaEngine] YouTube Creative Commons aranıyor: {query}...")
        try:
            # Get more variety by using a slightly broader query for YT CC
            yt_query = query.split(":")[0] if ":" in query else query
            yt_clips = self._download_from_youtube_cc(yt_query, output_dir, count)
            yt_fresh = self._filter_used_clips(yt_clips)
            all_paths += [p for p in yt_fresh if p not in all_paths]
            print(f"[MediaEngine] YouTube CC: {len(yt_fresh)} klip eklendi.")
        except Exception as e:
            print(f"[MediaEngine] YouTube CC hatası: {e}")

        # ── ADIM 2: OEM Scraper — 20+ marka press/newsroom ───────────────────────
        if len(all_paths) < count:
            try:
                from src.oem_scraper import OEMScraper
                oem_scraper = OEMScraper()
                _vtype = "short" if orientation == "portrait" else "long"
                oem_scraped = oem_scraper.get_clips(
                    topic=query,
                    category_id=category or "",
                    count=min(count - len(all_paths), 3),
                    video_type=_vtype,
                )
                oem_scraped_fresh = self._filter_used_clips(oem_scraped)
                all_paths += oem_scraped_fresh
                print(f"[MediaEngine] OEM Scraper (press/newsroom): {len(oem_scraped_fresh)} taze klip")
            except Exception as e:
                print(f"[MediaEngine] OEM Scraper hata (atlandı): {e}")

        # ── ADIM 3: OEM Static — Tesla CDN (doğrulanmış URL'ler) ─────────────────
        if len(all_paths) < count:
            needed = min(count - len(all_paths), 3)
            oem_static = self._download_from_oem(query, output_dir, needed, category)
            oem_static_fresh = self._filter_used_clips(oem_static)
            all_paths += oem_static_fresh
            print(f"[MediaEngine] OEM Tesla CDN: {len(oem_static_fresh)} taze klip")

        # ── ADIM 3: Pexels HD (marka bazlı sorgular) ─────────────────────────────
        if len(all_paths) < count:
            needed = count - len(all_paths)
            pex = self._download_from_pexels(query, output_dir,
                                              needed + 2, orientation, category)
            pex_fresh = self._filter_used_clips(pex)
            all_paths += [p for p in pex_fresh if p not in all_paths]
            print(f"[MediaEngine] Pexels HD: {len(pex_fresh)} taze klip")

        # ── ADIM 4: Pixabay HD ────────────────────────────────────────────────────
        if len(all_paths) < count:
            needed = count - len(all_paths)
            pix_or = "horizontal" if orientation == "portrait" else orientation
            pix = self._download_from_pixabay(query, output_dir,
                                               needed + 2, pix_or, category)
            pix_fresh = self._filter_used_clips(pix)
            all_paths += [p for p in pix_fresh if p not in all_paths]
            print(f"[MediaEngine] Pixabay HD: {len(pix_fresh)} taze klip")

        # ── ADIM 5: FreeVideoSources — key gerektirmeyen kaynaklar ───────────────
        if len(all_paths) < count:
            try:
                from src.free_video_sources import FreeVideoSources
                free_src = FreeVideoSources()
                _fvtype = "short" if orientation == "portrait" else "long"
                free_clips = free_src.download_clips(
                    query=query,
                    count=count - len(all_paths) + 2,
                    video_type=_fvtype,
                )
                free_fresh = self._filter_used_clips(free_clips)
                all_paths += [p for p in free_fresh if p not in all_paths]
                print(f"[MediaEngine] FreeVideo HD: {len(free_fresh)} taze klip")
            except Exception as e:
                print(f"[MediaEngine] FreeVideoSources hata: {e}")

        # ── ADIM 6: Pexels fallback (farklı genel sorgu) ──────────────────────────
        if len(all_paths) < max(2, count // 2):
            fallback_queries = [
                "electric car 4k cinematic luxury",
                "EV technology future automotive",
                "tesla model driving highway 4k",
                "electric vehicle modern exterior HD",
            ]
            extra = self._download_from_pexels(
                random.choice(fallback_queries),
                output_dir + "_extra",
                count, "landscape", category=category
            )
            extra_fresh = self._filter_used_clips(extra)
            all_paths += [p for p in extra_fresh if p not in all_paths]
            print(f"[MediaEngine] Pexels ek fallback: {len(extra_fresh)} klip")

        # ── ADIM 7: AI Video Üretimi ──────────────────────────────────────────────
        if len(all_paths) < max(2, count // 2):
            print(f"[MediaEngine] ⚡ Stok video yetersiz ({len(all_paths)}/{count}), AI video üretimine geçiliyor...")
            ai_video_dir = os.path.join(output_dir, "ai_generated")
            needed = max(1, count - len(all_paths))
            try:
                ai_clips = self.generate_ai_video_clips(
                    topic=query,
                    count=needed + 1,
                    output_dir=ai_video_dir,
                    duration=5,
                )
                ai_fresh = self._filter_used_clips(ai_clips)
                all_paths += [p for p in ai_fresh if p not in all_paths]
                print(f"[MediaEngine] AI Video: {len(ai_fresh)} klip")
            except Exception as e:
                print(f"[MediaEngine] AI Video üretim hatası: {e}")

        # ── ADIM 8: AI Görüntü Fallback — Pollinations.ai (kesin son çare) ────────
        if not all_paths:
            print("[MediaEngine] ⚠️ Tüm video kaynakları başarısız, AI görüntü fallback devreye giriyor...")
            self._used_clips.clear()
            self._save_used_clips()
            ai_img_dir = os.path.join(output_dir, "ai_fallback")
            ai_images = self.generate_ai_fallback_images(
                topic=query,
                count=count,
                output_dir=ai_img_dir,
            )
            scale = "1080:1920" if orientation == "portrait" else "1920:1080"
            converted = []
            for img_path in ai_images:
                video_path = img_path.rsplit(".", 1)[0] + "_clip.mp4"
                try:
                    import subprocess
                    cmd = [
                        "ffmpeg", "-y", "-loop", "1",
                        "-i", img_path,
                        "-c:v", "libx264", "-t", "5",
                        "-pix_fmt", "yuv420p",
                        "-vf", f"scale={scale},setsar=1",
                        "-r", "30", video_path,
                    ]
                    result = subprocess.run(cmd, capture_output=True, timeout=60)
                    if result.returncode == 0 and os.path.exists(video_path) and os.path.getsize(video_path) > 50_000:
                        converted.append(video_path)
                        print(f"[MediaEngine] ✅ AI görüntü → klip: {os.path.basename(video_path)}")
                except Exception as e:
                    print(f"[MediaEngine] Görüntü→video dönüşüm hatası: {e}")
            all_paths += converted

        if not all_paths:
            print("[MediaEngine] ❌ UYARI: Hiç klip bulunamadı!")
            return []

        random.shuffle(all_paths)
        final = all_paths[:count]
        print(f"[MediaEngine] ✅ {len(final)} taze HD klip hazır")
        return final

    # ══════════════════════════════════════════════════════════════
    #  AI VIDEO ÜRETİMİ — 7 Servis Sıralı Fallback
    # ══════════════════════════════════════════════════════════════
    def _get_ai_prompts(self, topic, category=None):
        """Konuya ve kategoriye göre AI video prompt'ları üretir."""
        cat_prompts = {
            "battery_science": [
                "lithium battery cells glowing blue in laboratory, macro close up, 4k cinematic, no text",
                "EV battery pack assembly manufacturing line, high tech factory, 4k, no text",
                "solid state battery technology futuristic visualization, blue energy glow, 4k, no text",
                "battery management system circuit board close up, LED lights, 4k macro, no text",
            ],
            "range_tests": [
                "electric car driving on empty highway at sunset, aerial drone shot, 4k cinematic, no text",
                "Tesla Model 3 interior dashboard showing range display, night driving, 4k, no text",
                "EV driving through winter snow landscape, dramatic lighting, 4k cinematic, no text",
                "electric vehicle speedometer dashboard close up, night, neon lights, 4k, no text",
            ],
            "charging": [
                "Tesla supercharger station at night, multiple EVs charging, neon lights, 4k cinematic, no text",
                "EV charging cable plugging into electric car port, close up macro, 4k, no text",
                "fast charging station futuristic design, electric sparks energy, 4k, no text",
                "electric vehicle DC fast charging, energy flow visualization, 4k, no text",
            ],
            "comparisons": [
                "multiple luxury electric cars parked in modern showroom, 4k cinematic, no text",
                "two electric vehicles side by side on race track, aerial view, 4k, no text",
                "electric car lineup exterior, various models, studio lighting, 4k, no text",
            ],
            "market_data": [
                "electric vehicle factory production line aerial view, modern industrial, 4k, no text",
                "global EV market visualization, digital world map, data flowing, 4k, no text",
                "BYD Tesla factory interior, robots assembling EVs, high tech, 4k, no text",
            ],
            "education": [
                "electric motor cross section animation, spinning magnets, blue energy, 4k, no text",
                "heat pump system working visualization, thermal energy flow, 4k, no text",
                "car aerodynamics wind tunnel test, streamlines visible, 4k cinematic, no text",
            ],
        }
        base_prompts = [
            f"futuristic electric car driving on highway at sunset, cinematic 4k, no text, {topic}",
            "EV battery technology close up, laboratory blue glow, 4k cinematic, no text",
            "electric vehicle charging station at night, city lights reflections, 4k, no text",
            "modern EV exterior driving through city, golden hour, cinematic 4k, no text",
            "aerial drone shot electric car on winding mountain road, 4k, no text",
            "electric motor engine technology heat visualization blue glow, macro 4k, no text",
        ]
        return cat_prompts.get(category, base_prompts)

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
                    print(f"[AI] {svc_name} deneniyor (klip {i+1}/{count})...")
                    result = svc_fn(prompt, out)
                    if result and os.path.exists(result) and os.path.getsize(result) > 50_000:
                        clips.append(result)
                        print(f"[AI] ✅ {svc_name} klip {i+1} hazır")
                        break
                except Exception as e:
                    print(f"[AI] {svc_name}: {e}")

            if len(clips) <= i:
                print(f"[AI] ⚠️ Klip {i+1} tüm servisler başarısız")

        print(f"[AI] Toplam {len(clips)}/{count} AI klip hazır")
        return clips

    # ── fal.ai ─────────────────────────────────────────────────────
    def _generate_fal_video(self, prompt, output_path, duration=5):
        if not self.fal_key:
            return None
        try:
            headers = {
                "Authorization": f"Key {self.fal_key}",
                "Content-Type": "application/json",
            }
            # Kling v2 dene
            r = requests.post(
                "https://fal.run/fal-ai/kling-video/v2/master/text-to-video",
                headers=headers,
                json={"prompt": prompt, "duration": str(min(duration, 5)),
                      "aspect_ratio": "16:9"},
                timeout=30,
            )
            if r.status_code != 200:
                # Minimax dene
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
                # Queue
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

    # ── HuggingFace ─────────────────────────────────────────────────
    def _generate_hf_video(self, prompt, output_path, duration=5):
        if not self.hf_token:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            models = [
                "ali-vilab/text-to-video-ms-1.7b",
                "damo-vilab/text-to-video-ms-1.7b",
            ]
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

    # ── Runway ML ───────────────────────────────────────────────────
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

    # ── Luma ────────────────────────────────────────────────────────
    def _generate_luma_video(self, prompt, output_path, duration=5):
        if not self.luma_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.luma_key}",
                "Content-Type": "application/json",
            }
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

    # ── Kling AI ────────────────────────────────────────────────────
    def _generate_kling_video_v2(self, prompt, output_path, duration=5):
        api_key = self.kling_key
        if not api_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
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

    # ── Stability AI ────────────────────────────────────────────────
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

    # ── Replicate ───────────────────────────────────────────────────
    def _generate_replicate_video(self, prompt, output_path, duration=5):
        if not self.replicate_key:
            return None
        try:
            headers = {
                "Authorization": f"Token {self.replicate_key}",
                "Content-Type": "application/json",
            }
            r = requests.post(
                "https://api.replicate.com/v1/predictions",
                headers=headers,
                json={"version": "9f747673945c62801b13b84701c783929c0ee784e4748ec062204894dda1a351",
                      "input": {"prompt": prompt, "num_frames": duration * 6,
                                "width": 1280, "height": 720,
                                "num_inference_steps": 25}},
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

    # ── Yardımcı: URL'den video indir ──────────────────────────────
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
                f"?width=1920&height=1080&seed={random.randint(1,999999)}"
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
            img.save(output_path, "PNG")
            print(f"[MediaEngine] Thumbnail: {output_path}")
            return output_path
        except Exception as e:
            print(f"[MediaEngine] Thumbnail hatası: {e}")
            return None

    # Eski API uyumu için alias
    def generate_stability_video(self, prompt, output_path, duration=5):
        return self._generate_stability_video(prompt, output_path, duration)

    def generate_replicate_video(self, prompt, output_path, duration=5):
        return self._generate_replicate_video(prompt, output_path, duration)

    def generate_kling_video(self, prompt, output_path, duration=5):
        return self._generate_kling_video_v2(prompt, output_path, duration)
    def _download_from_youtube_cc(self, query: str, output_dir: str, count: int) -> list[str]:
        """
        YouTube'da Creative Commons (CC BY) lisanslı videoları arar ve indirir.
        """
        import subprocess
        paths = []
        
        # Search strategy: Clean query and try layered simplification
        import random
        import re
        
        # Stop words to remove from search queries
        stop_words = ["and", "the", "of", "in", "with", "data", "coefficient", "relationship", "analysis", "specs", "ultra"]
        
        def clean_q(text):
            # Remove special chars and lowercase
            text = re.sub(r'[^a-zA-Z0-9 ]', '', text).lower()
            words = [w for w in text.split() if w not in stop_words and len(w) > 2]
            return words

        clean_words = clean_q(query)
        main_topic = " ".join(clean_words[:2]) if clean_words else "electric car"
        
        # Varied, high-success B-roll queries
        queries_to_try = [
            f"{main_topic} electric car review b-roll",
            f"{main_topic} wind tunnel testing 4k",
            f"{main_topic} vehicle aerodynamics animation",
            f"{main_topic} future ev technology",
        ]
        random.shuffle(queries_to_try)
        
        for search_query in queries_to_try:
            if len(paths) >= count: break
            
            print(f"[MediaEngine] [YT-CC] Deneniyor: {search_query}")
            cmd_search = [
                "yt-dlp", "--get-id", "--max-downloads", "15", # Get more to shuffle
                "--match-filter", "license ~= '(?i)Creative Commons' | license ~= '(?i)cc-by'",
                f"ytsearch15:{search_query}"
            ]
            
            try:
                result = subprocess.run(cmd_search, capture_output=True, text=True, timeout=30)
                all_vids = [vid.strip() for vid in result.stdout.strip().split('\n') if vid.strip()]
                random.shuffle(all_vids) # SHUFFLE to avoid always picking the first result
                
                for vid in all_vids:
                    if len(paths) >= count: break
                    
                    # Check if we already used this video ID recently
                    if self._is_video_id_used(vid):
                        continue
                        
                    out_path = os.path.join(output_dir, f"yt_cc_{vid}.mp4")
                    if os.path.exists(out_path):
                        paths.append(out_path)
                        continue
                    
                    # RANDOM START TIME: Pick a random 12s segment from the first 5 minutes
                    # This dramatically increases variety even if the same video is found
                    start_points = ["30-42", "60-72", "90-102", "150-162", "210-222"]
                    chosen_segment = random.choice(start_points)
                    
                    cmd_dl = [
                        "yt-dlp", "-f", "bestvideo[height<=1080][ext=mp4]",
                        "--download-sections", f"*{chosen_segment}",
                        "--force-overwrites",
                        "-o", out_path,
                        f"https://www.youtube.com/watch?v={vid}"
                    ]
                    subprocess.run(cmd_dl, capture_output=True, timeout=60)
                    if os.path.exists(out_path) and os.path.getsize(out_path) > 150000:
                        paths.append(out_path)
                        self._mark_video_id_used(vid) # Mark as used
            except Exception:
                continue
            
        return paths
    def _is_video_id_used(self, video_id: str) -> bool:
        """Video ID'nin daha önce kullanılıp kullanılmadığını kontrol eder."""
        try:
            history_file = "media_id_history.json"
            if not os.path.exists(history_file):
                return False
            with open(history_file, "r") as f:
                history = json.load(f)
            return video_id in history
        except Exception:
            return False

    def _mark_video_id_used(self, video_id: str):
        """Kullanılan Video ID'yi geçmişe kaydeder."""
        try:
            history_file = "media_id_history.json"
            history = []
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    history = json.load(f)
            if video_id not in history:
                history.append(video_id)
                # Son 500 videoyu tut (hafıza yönetimi)
                history = history[-500:]
                with open(history_file, "w") as f:
                    json.dump(history, f)
        except Exception:
            pass
            
    def _filter_used_clips(self, paths):
        """Eski klipleri filtrele (mevcut mantık)."""
        if not hasattr(self, '_used_clips'):
            self._used_clips = set()
        fresh = [p for p in paths if p not in self._used_clips]
        self._used_clips.update(fresh)
        return fresh
