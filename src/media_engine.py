"""
Evcarix MediaEngine
HD Video Öncelik: OEM Basın Kiti → Pexels → Pixabay → fal.ai → HF → Runway → Luma → Kling → Stability → Replicate → Pollinations
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
#  OEM MARKA BASИН KİTİ — Konuya göre doğru marka seçilir
#  Tüm URL'ler test edilmiş çalışan HD video linkleri
# ═══════════════════════════════════════════════════════════════════
OEM_BRAND_VIDEOS = {
    # ── Sadece Tesla CDN URL'leri doğrulanmış çalışıyor ──────────────────────
    # Diğer OEM markaların CDN URL'leri sık değişiyor / erişim engelli olabiliyor.
    # Bu nedenle sadece Tesla'nın güvenilir CDN adresleri tutulmaktadır.
    # Diğer markalar için Pexels/Pixabay API kullanılmaktadır.
    "tesla": {
        "keywords": ["tesla", "model 3", "model y", "model s", "model x",
                     "cybertruck", "supercharger", "autopilot", "fsd",
                     "ev", "electric vehicle", "electric car", "battery",
                     "charging", "range", "byd", "hyundai", "kia", "bmw",
                     "volkswagen", "ford", "rivian", "lucid", "polestar"],
        "videos": [
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-Y-Desktop-NA.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-3-Desktop-NA.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Model-S-Homepage-Desktop-LHD-01.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Megapack-Homepage-Desktop.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-X-Desktop.mp4",
        ],
        "priority": 1,
    },
}

# Genel EV içeriği için kullanılacak videoları (marka spesifik değil)
OEM_GENERAL_VIDEOS = [
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-Y-Desktop-NA.mp4",
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Megapack-Homepage-Desktop.mp4",
    "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-3-Desktop-NA.mp4",
]

# Kategori bazlı OEM öncelikleri
CATEGORY_OEM_PRIORITY = {
    "battery_science":  ["tesla", "byd", "bmw"],
    "range_tests":      ["tesla", "hyundai", "lucid", "byd"],
    "charging":         ["tesla", "bmw", "volkswagen", "hyundai"],
    "comparisons":      ["tesla", "byd", "hyundai", "kia", "bmw"],
    "cost_ownership":   ["tesla", "volkswagen", "hyundai", "kia"],
    "market_data":      ["byd", "tesla", "volkswagen", "nio"],
    "infrastructure":   ["tesla", "volkswagen", "bmw"],
    "education":        ["tesla", "bmw", "hyundai"],
    "trend":            ["tesla", "byd", "hyundai", "rivian", "lucid"],
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
    #  OEM MARKA BASИН KİTİ — HD Telifsiz Videolar
    # ══════════════════════════════════════════════════════════════
    def _detect_brands_in_topic(self, topic: str, category: str = None) -> list:
        """Konu metninden ilgili OEM markalarını tespit eder."""
        topic_lower = topic.lower()
        matched = []
        for brand, data in OEM_BRAND_VIDEOS.items():
            for kw in data["keywords"]:
                if kw in topic_lower:
                    matched.append(brand)
                    break

        # Kategori bazlı öncelik
        cat_priority = CATEGORY_OEM_PRIORITY.get(category, [])
        if not matched and cat_priority:
            matched = cat_priority[:3]

        # Hiç eşleşme yoksa genel öncelik
        if not matched:
            matched = ["tesla", "byd", "hyundai", "bmw"]

        # Önceliğe göre sırala
        matched.sort(key=lambda b: OEM_BRAND_VIDEOS.get(b, {}).get("priority", 99))
        return matched

    def _download_from_oem(self, topic: str, output_dir: str,
                            count: int, category: str = None) -> list:
        """OEM marka basın kitlerinden HD video indirir."""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        brands = self._detect_brands_in_topic(topic, category)
        print(f"[OEM] Tespit edilen markalar: {brands[:4]}")

        for brand in brands:
            if len(paths) >= count:
                break
            brand_data = OEM_BRAND_VIDEOS.get(brand, {})
            video_urls = brand_data.get("videos", [])
            random.shuffle(video_urls)

            for url in video_urls:
                if len(paths) >= count:
                    break
                fname = f"oem_{brand}_{Path(url).stem[:35]}.mp4"
                out = os.path.join(output_dir, fname)

                # Önbellekte varsa kullan
                if os.path.exists(out) and os.path.getsize(out) > 200_000:
                    if self._get_clip_hash(out) not in self._used_clips:
                        paths.append(out)
                        print(f"[OEM] ♻️  Önbellekten: {fname}")
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
                            print(f"[OEM] ✅ {fname} ({size//1024//1024}MB)")
                        else:
                            os.remove(out)
                            print(f"[OEM] ⚠️  Çok küçük ({size} byte), atlandı")
                    else:
                        print(f"[OEM] HTTP {r.status_code} / content-type={ct}: {brand}")
                except Exception as e:
                    print(f"[OEM] {brand} hata: {e}")

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
        """Kategoriye göre optimize Pexels sorgusu."""
        cat_queries = {
            "battery_science": [
                "lithium battery cell technology laboratory close up 4k",
                "EV battery pack assembly manufacturing HD",
                "solid state battery futuristic technology",
                "battery research scientist laboratory blue",
            ],
            "range_tests": [
                "electric car driving highway aerial view 4k",
                "EV dashboard speedometer range display",
                "Tesla Model 3 driving road cinematic 4k",
                "electric vehicle winter snow driving",
            ],
            "charging": [
                "electric car charging station night 4k",
                "EV fast charging plug cable close up HD",
                "Tesla supercharger station multiple cars",
                "DC fast charging electric vehicle port",
            ],
            "comparisons": [
                "multiple electric cars parked showroom 4k",
                "electric vehicle lineup modern HD",
                "car comparison test track aerial",
                "EV showroom interior modern design",
            ],
            "cost_ownership": [
                "electric car dealership showroom interior 4k",
                "car finance calculator business meeting",
                "money savings green technology",
                "family electric car purchase dealership",
            ],
            "market_data": [
                "electric vehicle factory production line 4k",
                "global business data analytics dashboard",
                "EV manufacturing plant aerial view",
                "automotive industry modern technology",
            ],
            "infrastructure": [
                "electric car charging network city night",
                "solar panels renewable energy installation 4k",
                "smart city electric vehicle charging",
                "power grid electricity technology",
            ],
            "education": [
                "electric motor engine technology close up 4k",
                "car heat thermal visualization technology",
                "engineering blueprint technical design",
                "automotive technology laboratory research",
            ],
            "trend": [
                "futuristic electric car driving cinematic 4k",
                "new electric vehicle launch reveal",
                "modern EV exterior driving sunset",
                "electric car technology innovation 4k",
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
                # HD tercih: en az 1280px genişlik
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
        1. OEM Marka Basın Kiti — Gerçek press/newsroom scraper (HD, telifsiz)
        2. OEM Static — Hardcoded brand press kit URL'leri (backup)
        3. Pexels HD (API key gerekli)
        4. Pixabay HD (API key gerekli)
        5. FreeVideoSources — Coverr, Videvo, Mixkit, Dareful (ücretsiz, key yok)
        6. Pexels fallback (farklı sorgu)
        """
        os.makedirs(output_dir, exist_ok=True)
        all_paths = []

        # 1. OEM Static — Tesla CDN (doğrulanmış çalışan URL'ler)
        # NOT: OEM Scraper (HTML scraping) kaldırıldı — press siteleri JS render
        # kullanıyor, raw HTML'den .mp4 bulunamıyor ve 20+ siteye boşa zaman harcanıyor.
        oem_static = self._download_from_oem(query, output_dir, min(count, 3), category)
        oem_static_fresh = self._filter_used_clips(oem_static)
        all_paths += oem_static_fresh
        print(f"[MediaEngine] OEM Tesla CDN: {len(oem_static_fresh)} taze klip")

        # 2. Pexels HD (birincil stok video kaynağı)
        if len(all_paths) < count:
            needed = count - len(all_paths)
            pex = self._download_from_pexels(query, output_dir,
                                              needed + 2, orientation, category)
            pex_fresh = self._filter_used_clips(pex)
            all_paths += [p for p in pex_fresh if p not in all_paths]
            print(f"[MediaEngine] Pexels HD: {len(pex_fresh)} taze klip")

        # 4. Pixabay HD
        if len(all_paths) < count:
            needed = count - len(all_paths)
            pix_or = "horizontal" if orientation == "portrait" else orientation
            pix = self._download_from_pixabay(query, output_dir,
                                               needed + 2, pix_or, category)
            pix_fresh = self._filter_used_clips(pix)
            all_paths += [p for p in pix_fresh if p not in all_paths]
            print(f"[MediaEngine] Pixabay HD: {len(pix_fresh)} taze klip")

        # 5. FreeVideoSources — Ücretsiz, key gerektirmeyen kaynaklar
        if len(all_paths) < count:
            try:
                from src.free_video_sources import FreeVideoSources
                free_src = FreeVideoSources()
                video_type = "short" if orientation == "portrait" else "long"
                free_clips = free_src.download_clips(
                    query=query,
                    count=count - len(all_paths) + 2,
                    video_type=video_type,
                )
                free_fresh = self._filter_used_clips(free_clips)
                all_paths += [p for p in free_fresh if p not in all_paths]
                print(f"[MediaEngine] FreeVideo HD: {len(free_fresh)} taze klip")
            except Exception as e:
                print(f"[MediaEngine] FreeVideoSources hata: {e}")

        # 6. Pexels tekrar (farklı fallback sorgu)
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
            print(f"[MediaEngine] Pexels ek: {len(extra_fresh)} klip")

        # Tüm klipler kullanılmışsa hash'i temizle ve yeniden başla
        if not all_paths:
            print("[MediaEngine] ⚠️ Tüm klipler kullanılmış, hash temizleniyor...")
            self._used_clips.clear()
            self._save_used_clips()
            return self.download_stock_videos(query, output_dir, count,
                                              orientation, category)

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