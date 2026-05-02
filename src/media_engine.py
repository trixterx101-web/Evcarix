import os
import re
import random
import subprocess
import json
import datetime
import math
import requests
import urllib.parse
from PIL import Image
from src.voice_engine import VoiceEngine
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════════════
#  NASA / DOE KAMU MALI URL'LERİ  (API gerektirmez, doğrudan CDN)
# ═══════════════════════════════════════════════════════════════════
NASA_PUBLIC_VIDEOS = [
    "https://images-assets.nasa.gov/video/NHQ_2022_0214_EVSE_Charging_Stations/NHQ_2022_0214_EVSE_Charging_Stations~orig.mp4",
    "https://images-assets.nasa.gov/video/KSC-20220503-MH-CST01-0001-Kennedy_Electric_Vehicle/KSC-20220503-MH-CST01-0001-Kennedy_Electric_Vehicle~orig.mp4",
]

DOE_PUBLIC_VIDEOS = [
    "https://www.energy.gov/sites/default/files/2022-02/ev-charging-broll.mp4",
    "https://www.energy.gov/sites/default/files/2023-04/argonne-battery-lab.mp4",
]

# ═══════════════════════════════════════════════════════════════════
#  OEM PRESS KIT ARAMA TANIMLARI
# ═══════════════════════════════════════════════════════════════════
OEM_PRESS_SEARCH = {
    "tesla": {
        "direct_videos": [
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-Y-Desktop-NA.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Homepage-Model-S-Desktop.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Model-3-Hero-Desktop.mp4",
            "https://digitalassets.tesla.com/tesla-contents/video/upload/f_auto,q_auto/Megapack-Homepage-Desktop.mp4",
        ]
    },
    "lucid": {
        "direct_videos": [
            "https://www.lucidmotors.com/media/video/lucid-air-exterior-driving.mp4",
            "https://www.lucidmotors.com/media/video/lucid-air-interior-overview.mp4",
        ]
    },
    "waymo": {
        "direct_videos": [
            "https://storage.googleapis.com/waymo-uploads/files/research/open-dataset/waymo-open-dataset.mp4",
        ]
    },
}

# ═══════════════════════════════════════════════════════════════════
#  YOUTUBE CC EV ARAMA TERİMLERİ (yt-dlp ile CC lisanslı)
# ═══════════════════════════════════════════════════════════════════
YTCC_EV_QUERIES = [
    "electric car review 2024 creative commons",
    "EV battery technology explained creative commons",
    "electric vehicle charging station creative commons",
    "Tesla Model 3 range test creative commons",
    "electric car comparison 2024 creative commons",
    "EV vs gasoline real world test creative commons",
]



class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")
        self.replicate_api_key = os.getenv("REPLICATE_API_TOKEN")
        self.kling_access_key = os.getenv("KLING_ACCESS_KEY")
        self.kling_secret_key = os.getenv("KLING_SECRET_KEY")
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        self.coverr_api_key = os.getenv("COVERR_API_KEY")
        self.voice_engine = VoiceEngine()
        
        # Kullanılan klip takip sistemi
        self.used_clips_file = "used_clips.json"
        self._load_used_clips()

        # yt-dlp kurulu mu kontrol et
        try:
            subprocess.run(["yt-dlp", "--version"],
                           capture_output=True, check=True, timeout=10)
            self.ytdlp_available = True
        except Exception:
            self.ytdlp_available = False
            print("[MediaEngine] yt-dlp bulunamadı. pip install yt-dlp ile kurun.")

    async def generate_voiceover(self, text, output_path, voice_type="female", rate="+10%"):
        return await self.voice_engine.generate_voice(text, output_path, voice_type=voice_type, rate=rate)

    # Kelimeler EV ile ilgisi olmayan stok videolari elemek icin
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
        """Pexels video tags'ine bakarak EV ile ilgili olup olmadigini kontrol eder."""
        tags = video_data.get("tags", []) or []
        tag_set = {t.lower() for t in tags if isinstance(t, str)}
        # Ilgisiz tag varsa reddet
        if tag_set & self._IRRELEVANT_TAGS:
            return False
        # En az bir EV-ilgili tag varsa kabul et
        if tag_set & self._RELEVANT_TAGS:
            return True
        # User adi bazen ipucu verir
        user_name = (video_data.get("user", {}) or {}).get("name", "").lower()
        if any(w in user_name for w in ["ev", "tesla", "electric", "auto", "car"]):
            return True
        # Varsayilan olarak kabul et (cok agresif filtreleme yapma)
        return True

    def _get_professional_query(self, topic, category=None):
        """Her çalışmada farklı bir arama sorgusu üretir — kategoriye gore EV odakli + konu anahtar kelimeleri."""
        clean_topic = topic.split(':')[0].split('?')[0].strip() if ':' in topic or '?' in topic else topic
        
        # Konu başlığından anahtar kelimeler çıkar
        topic_keywords = []
        important_words = ["battery", "charging", "range", "tesla", "hyundai", "byd", "kia", "bmw", 
                          "mercedes", "audi", "volkswagen", "ford", "gm", "nissan", "toyota", 
                          "lucid", "rivian", "polestar", "nio", "xpeng", "cost", "price", 
                          "depreciation", "market", "sales", "infrastructure", "grid", 
                          "solar", "motor", "heat", "pump", "aerodynamics", "drag", "efficiency"]
        for word in important_words:
            if word.lower() in clean_topic.lower():
                topic_keywords.append(word)
        
        # Kategoriye gore spesifik EV arama stratejileri
        category_strategies = {
            "battery_science": [
                "lithium battery cell technology laboratory close up",
                "EV battery pack assembly manufacturing 4k",
                "battery chemistry research scientist lab",
                "solid state battery futuristic technology",
                "battery management system BMS circuit board",
            ],
            "range_tests": [
                "electric car driving highway aerial view 4k",
                "Tesla driving on road winter snow",
                "EV dashboard speedometer range display",
                "electric vehicle on open road cinematic",
                "car driving city night lights 4k",
            ],
            "charging": [
                "electric car charging station night 4k",
                "EV fast charging plug cable close up",
                "Tesla supercharger station cars charging",
                "charging station technology futuristic",
                "electric vehicle charging port detail",
            ],
            "cost_ownership": [
                "electric car showroom dealership interior",
                "EV repair shop mechanic working",
                "car insurance documents calculator business",
                "money savings finance calculator digital",
                "family buying car dealer handshake",
            ],
            "comparisons": [
                "two electric cars side by side showroom",
                "car comparison test track racing",
                "EV lineup multiple cars parked",
                "car specifications chart display screen",
                "electric vehicles parked row modern",
            ],
            "market_data": [
                "global business data analytics screen",
                "stock market chart graph rising",
                "world map digital connections network",
                "factory production line cars manufacturing",
                "business meeting presentation data charts",
            ],
            "infrastructure": [
                "electric car charging network city",
                "power grid electricity transmission tower",
                "solar panels renewable energy field",
                "smart city technology traffic lights",
                "apartment building parking garage night",
            ],
            "education": [
                "electric motor engine technology close up",
                "heat pump HVAC system technology",
                "car aerodynamics wind tunnel test",
                "thermal imaging heat visualization technology",
                "engineering blueprint technical drawing",
            ],
            "interactive_tools": [
                "smartphone calculator app close up",
                "digital screen data visualization charts",
                "mobile app interface modern design",
                "computer screen analytics dashboard",
                "technology user interface futuristic",
            ],
        }

        if category and category in category_strategies:
            base_query = random.choice(category_strategies[category])
            # Konu anahtar kelimelerini sorguya ekle
            if topic_keywords:
                base_query = f"{base_query} {' '.join(topic_keywords[:2])}"
            return base_query

        # Varsayilan genel EV sorgulari - konu anahtar kelimeleriyle
        strategies = [
            f"{clean_topic} EV driving 4k",
            f"Tesla {clean_topic} exterior 4k",
            f"electric vehicle {clean_topic} test",
            f"EV battery {clean_topic} technology",
            f"electric car charging station 4k",
            f"Tesla Model 3 {clean_topic} driving",
            f"EV dashboard display technology",
            f"electric vehicle production line",
            f"lithium battery cell technology",
            f"BYD electric car driving",
        ]
        base_query = random.choice(strategies)
        # Konu anahtar kelimelerini sorguya ekle
        if topic_keywords:
            base_query = f"{base_query} {' '.join(topic_keywords[:2])}"
        return base_query

    # ─── Pexels Video İndirme ──────────────────────────────────────────────────
    def _download_from_pexels(self, query, output_dir, count, orientation, category=None):
        """Pexels API'den rastgele sayfa ve sorgu ile video indirir."""
        if not self.pexels_api_key:
            print("[Pexels] API key bulunamadı, atlanıyor.")
            return []

        optimized_query = self._get_professional_query(query, category=category)
        headers = {"Authorization": self.pexels_api_key}
        page = random.randint(1, 8)

        url = (
            f"https://api.pexels.com/videos/search"
            f"?query={optimized_query}"
            f"&per_page={count + 4}"
            f"&page={page}"
            f"&orientation={orientation}"
        )
        paths = []
        try:
            print(f"[Pexels] '{optimized_query}' (sayfa {page}) aranıyor...")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                videos = response.json().get('videos', [])
                if not videos:
                    url_p1 = url.replace(f"&page={page}", "&page=1")
                    response = requests.get(url_p1, headers=headers, timeout=15)
                    videos = response.json().get('videos', []) if response.status_code == 200 else []
                random.shuffle(videos)
                for i, video_data in enumerate(videos):
                    if len(paths) >= count:
                        break
                    # EV ile ilgisi olmayan videolari atla (somin, cicek, doga...)
                    if not self._is_ev_related(video_data):
                        tags = video_data.get("tags", [])
                        print(f"[Pexels] ⚠️ EV ile ilgisiz video atlandi (tags: {tags[:3]})")
                        continue
                    video_files = video_data.get('video_files', [])
                    if not video_files:
                        continue
                    sorted_files = sorted(video_files, key=lambda x: x.get('width', 0), reverse=True)
                    # VIDEO_TYPE'a göre orientation kontrolü
                    video_type = os.environ.get("VIDEO_TYPE", "short").strip().lower()
                    if video_type == "long":
                        # Landscape (16:9) videoları seç - width >= height
                        portrait_files = [f for f in sorted_files if f.get('width', 0) >= f.get('height', 0)]
                    else:
                        # Portrait (9:16) videoları seç - 9:16 formatı için zorunlu
                        # Aspect ratio >= 1.6 (yaklaşık 9:16'dan daha dikey)
                        portrait_files = [f for f in sorted_files if f.get('width', 0) > 0 and (f.get('height', 0) / f.get('width', 1)) >= 1.6]
                    if portrait_files:
                        chosen = random.choice(portrait_files[:3]) if len(portrait_files) >= 3 else portrait_files[0]
                    else:
                        # Portrait yoksa atla
                        print(f"[Pexels] ⚠️ {video_type.upper()} video bulunamadı, atlanıyor")
                        continue
                    video_url = chosen['link']
                    clean_q = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:30]
                    filename = f"pexels_{clean_q}_{page}_{i}.mp4"
                    out_path = os.path.join(output_dir, filename)
                    v_res = requests.get(video_url, stream=True, timeout=60)
                    if v_res.status_code == 200:
                        with open(out_path, 'wb') as f:
                            for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        paths.append(out_path)
                        print(f"[Pexels] ✅ İndirildi: {filename}")
            else:
                print(f"[Pexels] API hatası: {response.status_code}")
        except Exception as e:
            print(f"[Pexels] İndirme hatası: {e}")
        return paths

    # ─── Pixabay Video İndirme ─────────────────────────────────────────────────
    def _download_from_pixabay(self, query, output_dir, count, orientation, category=None):
        """Pixabay API'den video indirir. Ücretsiz & ticari kullanım serbest."""
        if not self.pixabay_api_key:
            print("[Pixabay] API key bulunamadı, atlanıyor.")
            return []

        pixabay_queries_map = {
            "battery_science": ["lithium battery cell", "battery laboratory", "battery technology", "battery factory production"],
            "range_tests": ["electric car highway driving", "winter road driving", "dashboard speedometer", "electric vehicle test"],
            "charging": ["EV charging station", "Tesla supercharger", "electric car charging", "DC fast charging"],
            "cost_ownership": ["car dealership", "car insurance", "money calculator", "business finance"],
            "comparisons": ["electric vehicles comparison", "car showroom", "car comparison test", "cars parked"],
            "market_data": ["business analytics", "stock market", "factory production", "global network"],
            "infrastructure": ["power grid", "solar panels", "smart city", "charging network"],
            "education": ["electric motor", "heat pump", "engineering technology", "wind tunnel"],
            "interactive_tools": ["smartphone app", "data visualization", "digital screen", "technology interface"],
        }
        default_queries = [
            "electric car",
            "EV charging",
            "electric vehicle",
            "tesla car",
            "EV battery technology",
            "electric car charging station",
            "EV production factory",
            "electric car dashboard",
        ]
        pixabay_queries = pixabay_queries_map.get(category, default_queries)
        optimized_query = random.choice(pixabay_queries)
        page = random.randint(1, 5)
        pix_orientation = "vertical" if orientation == "portrait" else "horizontal"

        url = "https://pixabay.com/api/videos/"
        params = {
            'key': self.pixabay_api_key,
            'q': optimized_query,
            'video_type': 'film',
            'orientation': pix_orientation,
            'order': 'popular',
            'per_page': count + 4,
            'page': page,
            'safesearch': 'true',
        }
        paths = []
        try:
            print(f"[Pixabay] '{optimized_query}' (sayfa {page}) aranıyor...")
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                hits = response.json().get('hits', [])
                if not hits:
                    params['page'] = 1
                    response = requests.get(url, params=params, timeout=15)
                    hits = response.json().get('hits', []) if response.status_code == 200 else []
                random.shuffle(hits)
                for i, hit in enumerate(hits[:count]):
                    videos_dict = hit.get('videos', {})
                    chosen_video = None
                    # VIDEO_TYPE'a göre orientation kontrolü
                    video_type = os.environ.get("VIDEO_TYPE", "short").strip().lower()
                    for quality in ['large', 'medium', 'small', 'tiny']:
                        if quality in videos_dict and videos_dict[quality].get('url'):
                            vid = videos_dict[quality]
                            w, h = vid.get('width', 0), vid.get('height', 0)
                            if w > 0:
                                if video_type == "long":
                                    # Landscape (16:9) videoları seç - width >= height
                                    if w >= h:
                                        chosen_video = vid
                                        break
                                else:
                                    # Portrait (9:16) için aspect ratio >= 1.6
                                    if h / w >= 1.6:
                                        chosen_video = vid
                                        break
                    if not chosen_video:
                        print(f"[Pixabay] ⚠️ {video_type.upper()} video bulunamadı, atlanıyor")
                        continue
                    video_url = chosen_video['url']
                    clean_q = re.sub(r'[^\w\s-]', '', optimized_query).strip().replace(' ', '_')[:30]
                    filename = f"pixabay_{clean_q}_{page}_{i}.mp4"
                    out_path = os.path.join(output_dir, filename)
                    v_res = requests.get(video_url, stream=True, timeout=60)
                    if v_res.status_code == 200:
                        with open(out_path, 'wb') as f:
                            for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        paths.append(out_path)
                        print(f"[Pixabay] ✅ İndirildi: {filename}")
            else:
                print(f"[Pixabay] API hatası: {response.status_code}")
        except Exception as e:
            print(f"[Pixabay] İndirme hatası: {e}")
        return paths

    # ─── Coverr Video İndirme ──────────────────────────────────────────────────
    def _download_from_coverr(self, query, output_dir, count, orientation="portrait", category=None):
        """Coverr.co API'den ücretsiz stok video indirir."""
        if not self.coverr_api_key:
            print("[Coverr] API key bulunamadı, atlanıyor.")
            return []

        optimized_query = self._get_professional_query(query, category=category)
        paths = []
        try:
            # Coverr API search
            url = (
                f"https://api.coverr.co/videos"
                f"?query={urllib.parse.quote(optimized_query)}"
                f"&page_size={count + 4}"
                f"&urls=true"
            )
            headers = {
                "Authorization": f"Bearer {self.coverr_api_key}",
                "Accept": "application/json"
            }

            print(f"[Coverr] '{optimized_query}' aranıyor...")
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"[Coverr] API hatası: {response.status_code}")
                return []

            data = response.json()
            hits = data.get('hits', [])

            if not hits:
                print(f"[Coverr] Video bulunamadı: {optimized_query}")
                return []

            downloaded = 0
            for video in hits:
                if downloaded >= count:
                    break

                # Filter for portrait/vertical videos based on VIDEO_TYPE
                video_type = os.environ.get("VIDEO_TYPE", "short").strip().lower()
                is_vertical = video.get('is_vertical', False)
                aspect_ratio = video.get('aspect_ratio', '')
                max_height = video.get('max_height', 0)
                max_width = video.get('max_width', 0)

                if video_type == "long":
                    # Accept landscape videos: width >= height
                    if max_width > 0 and max_height > max_width:
                        continue
                else:
                    # Accept portrait videos: height >= 1.6 * width
                    if not is_vertical and max_height / max(max_width, 1) < 1.6:
                        continue

                urls = video.get('urls', {})
                mp4_url = urls.get('mp4', '')
                mp4_download = urls.get('mp4_download', '')

                video_url = mp4_download or mp4_url
                if not video_url:
                    continue

                title = video.get('title', 'coverr_video').replace(' ', '_')[:40]
                safe_title = re.sub(r'[^\w\-]', '', title)
                filename = f"coverr_{safe_title}.mp4"
                out_path = os.path.join(output_dir, filename)

                if os.path.exists(out_path):
                    paths.append(out_path)
                    downloaded += 1
                    continue

                print(f"[Coverr] İndiriliyor: {title[:40]}...")
                r = requests.get(video_url, stream=True, timeout=60)
                if r.status_code == 200:
                    with open(out_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    paths.append(out_path)
                    downloaded += 1
                    print(f"[Coverr] ✅ İndirildi: {filename}")

                    # Register download stats (required by Coverr API)
                    video_id = video.get('id', '')
                    if video_id:
                        try:
                            requests.patch(
                                f"https://api.coverr.co/videos/{video_id}/stats/downloads",
                                headers=headers,
                                timeout=5
                            )
                        except Exception:
                            pass

            if not paths:
                print(f"[Coverr] Portrait video bulunamadı, atlanıyor")
        except Exception as e:
            print(f"[Coverr] İndirme hatası: {e}")
        return paths

    # ─── Ana İndirme Metodu — Pexels + Pixabay + Coverr birleşik ──────────────
    def download_stock_videos(self, query, output_dir="assets/temp_videos",
                              count=6, orientation="portrait", category=None):
        """
        Tüm kaynaklardan taze video indirir.
        Daha önce kullanılan klipler otomatik olarak hariç tutulur.
        Öncelik: Pexels → Pixabay → OEM PressKit → NASA/DOE → Pexels (ek)
        """
        import json as _json
        os.makedirs(output_dir, exist_ok=True)
        all_paths = []

        # 1. Pexels (kalite öncelikli)
        pex_q = self._get_professional_query(query, category)
        pex = self._download_from_pexels(pex_q, output_dir, 3, orientation, category=category)
        pex_fresh = self._filter_used_clips(pex)
        all_paths += pex_fresh
        print(f"[MediaEngine] Pexels (kalite): {len(pex_fresh)} taze klip")

        # 2. Pexels (topic bazlı — farklı sorgu)
        if len(all_paths) < count:
            topic_query = f"Tesla {query} exterior 4k" if "tesla" not in query.lower() else query
            pex2 = self._download_from_pexels(topic_query, output_dir, count, orientation, category=category)
            pex2_fresh = self._filter_used_clips(pex2)
            all_paths += [p for p in pex2_fresh if p not in all_paths]
            print(f"[MediaEngine] Pexels (topic): {len(pex2_fresh)} taze klip")

        # 3. Pixabay
        if len(all_paths) < count:
            pix = self._download_from_pixabay(query, output_dir,
                                               count - len(all_paths), orientation, category=category)
            pix_fresh = self._filter_used_clips(pix)
            all_paths += [p for p in pix_fresh if p not in all_paths]
            print(f"[MediaEngine] Pixabay: {len(pix_fresh)} taze klip")

        # 4. OEM Press Kit
        if len(all_paths) < count:
            oem = self._download_from_oem_presskit(output_dir, 3, category)
            oem_fresh = self._filter_used_clips(oem)
            all_paths += [p for p in oem_fresh if p not in all_paths]
            print(f"[MediaEngine] OEM PressKit: {len(oem_fresh)} taze klip")

        # 5. NASA/DOE
        if len(all_paths) < count:
            pub = self._download_public_domain(output_dir, 2)
            pub_fresh = self._filter_used_clips(pub)
            all_paths += [p for p in pub_fresh if p not in all_paths]
            print(f"[MediaEngine] NASA/DOE: {len(pub_fresh)} taze klip")

        # 5.5. Free video sources fallback (no API key needed)
        if len(all_paths) < count:
            print("[MediaEngine] 🆓 Ücretsiz video kaynakları deneniyor...")
            from src.free_video_sources import FreeVideoSources, EV_SEARCH_TERMS
            free_src = FreeVideoSources()
            ev_terms = random.sample(EV_SEARCH_TERMS, min(3, len(EV_SEARCH_TERMS)))
            needed_count = count - len(all_paths)
            for term in ev_terms:
                if len(all_paths) >= count:
                    break
                free_clips = free_src.download_clips(
                    query=term,
                    count=needed_count,
                    video_type=os.environ.get("VIDEO_TYPE", "short")
                )
                all_paths += [p for p in free_clips if p not in all_paths]
                print(f"[MediaEngine] FreeVideoSources: {len(free_clips)} klip")

        # 6. Stok biterse: AI video + tekrar kullanım fallback
        if len(all_paths) < count:
            print("[MediaEngine] ⚠️  Stok videolar tükendi. AI video + tekrar kullanım devreye giriyor...")
            
            # 6a. AI video üret (varsa)
            ai_clips = self.generate_ai_video_clips(query, count=count - len(all_paths))
            if ai_clips:
                all_paths += [p for p in ai_clips if p not in all_paths]
                print(f"[MediaEngine] 🤖 AI video: {len(ai_clips)} klip eklendi")
            
            # 6b. Yine yetersizse hash temizle ve tekrar dene (başşa dön)
            if len(all_paths) < count:
                print("[MediaEngine] 🔄 Hash geçmişi temizleniyor, klipler tekrar kullanılacak...")
                self._used_clips.clear()
                self._save_used_clips()
                # Tekrar Pexels'ten indir (bu sefer filtresiz)
                retry = self._download_from_pexels(
                    self._get_professional_query(query, category),
                    output_dir + "_retry",
                    count, orientation, category=category
                )
                all_paths += [p for p in retry if p not in all_paths]
                print(f"[MediaEngine] Yeniden indirme: {len(retry)} klip")

        random.shuffle(all_paths)

        if not all_paths:
            print("[MediaEngine] ⚠️  Hiçbir kaynaktan taze video alınamadı!")
            return []

        final = all_paths[:count]
        print(f"[MediaEngine] ✅ {len(final)} taze klip hazır (daha önce kullanılanlar hariç)")
        return final

    # ─── NASA / DOE Kamu Malı Videolar ───────────────────────────────────────
    def _download_public_domain(self, output_dir, count):
        """NASA ve DOE kamu malı EV/enerji videolarını indirir. Telif yok."""
        from pathlib import Path
        os.makedirs(output_dir, exist_ok=True)
        all_urls = NASA_PUBLIC_VIDEOS + DOE_PUBLIC_VIDEOS
        random.shuffle(all_urls)
        paths = []

        for url in all_urls:
            if len(paths) >= count:
                break
            try:
                fname = f"pubdomain_{Path(url).name[:40]}"
                if not fname.endswith(".mp4"):
                    fname += ".mp4"
                out = os.path.join(output_dir, fname)

                if os.path.exists(out) and os.path.getsize(out) > 100_000:
                    paths.append(out)
                    print(f"[PubDomain] ♻️  Önbellekten: {fname}")
                    continue

                print(f"[PubDomain] NASA/DOE indiriliyor: {fname}")
                r = requests.get(url, stream=True, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    with open(out, 'wb') as f:
                        for chunk in r.iter_content(1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    if os.path.getsize(out) > 100_000:
                        paths.append(out)
                        print(f"[PubDomain] ✅ {fname}")
                    else:
                        os.remove(out)
            except Exception as e:
                print(f"[PubDomain] Hata: {e}")
        return paths

    # ─── OEM Press Kit Videolar ───────────────────────────────────────────────
    def _download_from_oem_presskit(self, output_dir, count, category=None):
        """Tesla, Hyundai, BMW vb. üreticilerin basın kiti videolarını indirir."""
        from pathlib import Path
        os.makedirs(output_dir, exist_ok=True)
        paths = []

        priority = {
            "battery_science": ["tesla", "bmw"],
            "range_tests": ["tesla", "hyundai", "kia"],
            "charging": ["tesla", "rivian", "ford"],
            "comparisons": ["hyundai", "kia", "bmw"],
        }
        brands = priority.get(category, list(OEM_PRESS_SEARCH.keys()))
        random.shuffle(brands)

        for brand in brands:
            if len(paths) >= count:
                break
            brand_data = OEM_PRESS_SEARCH.get(brand, {})
            direct_urls = brand_data.get("direct_videos", [])
            random.shuffle(direct_urls)

            for url in direct_urls:
                if len(paths) >= count:
                    break
                try:
                    fname = f"oem_{brand}_{Path(url).stem[:30]}.mp4"
                    out = os.path.join(output_dir, fname)

                    if os.path.exists(out) and os.path.getsize(out) > 100_000:
                        paths.append(out)
                        print(f"[OEM] ♻️  Önbellekten: {fname}")
                        continue

                    print(f"[OEM] {brand.upper()} basın kiti indiriliyor: {fname}")
                    r = requests.get(url, stream=True, timeout=60,
                                     headers={"User-Agent": "Mozilla/5.0 (compatible; Evcarix/1.0)"})
                    if r.status_code == 200:
                        with open(out, 'wb') as f:
                            for chunk in r.iter_content(1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        if os.path.getsize(out) > 100_000:
                            paths.append(out)
                            print(f"[OEM] ✅ {fname}")
                        else:
                            os.remove(out)
                            print(f"[OEM] ⚠️  Dosya çok küçük, atlandı")
                    else:
                        print(f"[OEM] HTTP {r.status_code}: {url}")
                except Exception as e:
                    print(f"[OEM] {brand} indirme hatası: {e}")

        return paths

    # ─── YouTube CC (yt-dlp) ─────────────────────────────────────────────────
    def _download_from_youtube_cc(self, query, output_dir, count, max_duration=60):
        """yt-dlp ile YouTube'dan yalnızca Creative Commons lisanslı EV videolarını indirir."""
        from pathlib import Path
        if not self.ytdlp_available:
            print("[YT-CC] yt-dlp yok, atlanıyor.")
            return []

        os.makedirs(output_dir, exist_ok=True)
        q = random.choice(YTCC_EV_QUERIES)
        paths = []

        try:
            print(f"[YT-CC] '{q}' CC lisanslı video aranıyor...")
            cmd = [
                "yt-dlp",
                f"ytsearch{count * 3}:{q}",
                "--match-filter", "license='creativeCommon'",
                "--match-filter", f"duration < {max_duration}",
                "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]",
                "--merge-output-format", "mp4",
                "-o", os.path.join(output_dir, "ytcc_%(id)s.%(ext)s"),
                "--no-playlist",
                "--max-downloads", str(count),
                "--quiet",
                "--no-warnings",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            for f in Path(output_dir).glob("ytcc_*.mp4"):
                if f.stat().st_size > 100_000:
                    paths.append(str(f))
                    print(f"[YT-CC] ✅ {f.name}")
                if len(paths) >= count:
                    break
            print(f"[YT-CC] {len(paths)} CC video indirildi.")
        except subprocess.TimeoutExpired:
            print("[YT-CC] Zaman aşımı (3 dk)")
        except Exception as e:
            print(f"[YT-CC] Hata: {e}")
        return paths

    def generate_ai_fallback_images(self, topic, count=3, output_dir="assets/ai_fallback"):
        """Stok video bulunamazsa Pollinations.ai'dan EV temalı görüntü üretir."""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        prompts = [
            f"futuristic electric car driving on highway at sunset, cinematic 4k, dramatic lighting, no text, no watermark, {topic}",
            f"EV battery technology close up, laboratory, lithium cells, futuristic, blue glow, high detail, no text, no watermark",
            f"electric vehicle charging station at night, city lights, cyberpunk aesthetic, cinematic, no text, no watermark",
            f"Tesla or modern EV dashboard display, holographic interface, technology, dark background, no text, no watermark",
            f"aerial view of electric car on winding road, mountains, golden hour, cinematic, no text, no watermark",
        ]
        for i in range(min(count, len(prompts))):
            prompt = prompts[i]
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&negative=blurry,text,watermark,low%20quality"
            out_path = os.path.join(output_dir, f"ai_fallback_{i}.jpg")
            try:
                print(f"[Pollinations] AI görüntü üretiliyor ({i+1}/{count})...")
                r = requests.get(url, timeout=60)
                if r.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(r.content)
                    paths.append(out_path)
                    print(f"[Pollinations] ✅ Kaydedildi: {out_path}")
                else:
                    print(f"[Pollinations] HTTP {r.status_code}")
            except Exception as e:
                print(f"[Pollinations] Hata: {e}")
        return paths

    # ─── Stability AI Video Generation ─────────────────────────────────────
    def generate_stability_video(self, prompt, output_path, duration=5):
        """Stability AI ile 5 saniyelik video üretir."""
        if not self.stability_api_key:
            print("[Stability] API key bulunamadı, atlanıyor.")
            return None

        try:
            import stability_sdk
            from stability_sdk import client

            stability_api = client.StabilityInference(
                key=self.stability_api_key,
                verbose=True,
            )

            # Stability AI currently focuses on image-to-video or text-to-image
            # For video generation, we'll use their image generation and then animate
            print(f"[Stability] Video üretimi için prompt: {prompt[:50]}...")
            
            # Generate image first - 9:16 format
            answers = stability_api.generate(
                prompt=prompt,
                steps=30,
                cfg_scale=8.0,
                width=1080,
                height=1920,
                samples=1,
                sampler=stability_sdk.samplers.KARRAS
            )

            for resp in answers:
                for artifact in resp.artifacts:
                    if artifact.type == stability_sdk.generation.TYPE_IMAGE:
                        img_path = output_path.replace('.mp4', '_temp.png')
                        with open(img_path, 'wb') as f:
                            f.write(artifact.binary)
                        print(f"[Stability] Görüntü oluşturuldu, animasyon yapılıyor...")
                        
                        # Animate the image using simple pan/zoom (simulated video)
                        return self._animate_image_to_video(img_path, output_path, duration)
            
            return None
        except ImportError:
            print("[Stability] stability_sdk yüklü değil, atlanıyor.")
            return None
        except Exception as e:
            print(f"[Stability] Hata: {e}")
            return None

    # ─── Replicate Video Generation ────────────────────────────────────────
    def generate_replicate_video(self, prompt, output_path, duration=5):
        """Replicate API ile video üretir (Stable Video Diffusion vb.)."""
        if not self.replicate_api_key:
            print("[Replicate] API key bulunamadı, atlanıyor.")
            return None

        try:
            import replicate

            print(f"[Replicate] Video üretimi için prompt: {prompt[:50]}...")
            
            # Use Stable Video Diffusion or similar model - force 9:16 aspect ratio
            output = replicate.run(
                "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
                input={
                    "input_image": None,  # Can use image-to-video
                    "video_length": duration,
                    "sizing_strategy": "maintain_aspect_ratio",
                    "motion_bucket_id": 127,
                    "frames_per_second": 6,
                    "width": 1080,
                    "height": 1920
                }
            )
            
            # Download the video
            if output and len(output) > 0:
                video_url = output[0] if isinstance(output, list) else output
                r = requests.get(video_url, stream=True, timeout=120)
                if r.status_code == 200:
                    with open(output_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    print(f"[Replicate] ✅ Video indirildi: {output_path}")
                    return output_path
            
            return None
        except ImportError:
            print("[Replicate] replicate yüklü değil, atlanıyor.")
            return None
        except Exception as e:
            print(f"[Replicate] Hata: {e}")
            return None

    # ─── Kling AI Video Generation ───────────────────────────────────────────
    def generate_kling_video(self, prompt, output_path, duration=5):
        """Kling AI ile video üretir."""
        if not self.kling_access_key or not self.kling_secret_key:
            print("[Kling] API key bulunamadı, atlanıyor.")
            return None

        try:
            print(f"[Kling] Video üretimi için prompt: {prompt[:50]}...")
            
            # Kling AI video generation API
            url = "https://api.klingai.com/v1/videos/generations"
            headers = {
                "Authorization": f"Bearer {self.kling_access_key}",
                "Content-Type": "application/json"
            }
            data = {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": "9:16",
                "model": "kling-v1"
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("data", {}).get("task_id")
                if task_id:
                    # Poll for result
                    import time
                    max_wait = 300  # 5 minutes
                    waited = 0
                    while waited < max_wait:
                        time.sleep(10)
                        waited += 10
                        status_url = f"https://api.klingai.com/v1/videos/generations/{task_id}"
                        status_resp = requests.get(status_url, headers=headers, timeout=30)
                        if status_resp.status_code == 200:
                            status_data = status_resp.json()
                            task_status = status_data.get("data", {}).get("status")
                            if task_status == "succeed":
                                video_url = status_data.get("data", {}).get("urls", [{}])[0].get("url")
                                if video_url:
                                    r = requests.get(video_url, stream=True, timeout=120)
                                    if r.status_code == 200:
                                        with open(output_path, 'wb') as f:
                                            for chunk in r.iter_content(chunk_size=1024 * 1024):
                                                if chunk:
                                                    f.write(chunk)
                                        print(f"[Kling] ✅ Video indirildi: {output_path}")
                                        return output_path
                            elif task_status == "failed":
                                print(f"[Kling] ❌ Video üretimi başarısız")
                                break
            
            return None
        except Exception as e:
            print(f"[Kling] Hata: {e}")
            return None

    # ─── Qwen AI Video Generation ───────────────────────────────────────────
    def generate_qwen_video(self, prompt, output_path, duration=5):
        """Qwen AI (DashScope) ile video üretir."""
        if not self.dashscope_api_key:
            print("[Qwen] API key bulunamadı, atlanıyor.")
            return None

        try:
            print(f"[Qwen] Video üretimi için prompt: {prompt[:50]}...")

            # Qwen DashScope API for video generation
            # Note: Using Alibaba Cloud DashScope API
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.dashscope_api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "qwen-vl-max",  # or appropriate video model
                "input": {
                    "prompt": prompt,
                    "duration": duration
                },
                "parameters": {
                    "size": "1080*1920",  # 9:16 aspect ratio
                    "fps": 24
                }
            }

            response = requests.post(url, headers=headers, json=data, timeout=60)
            if response.status_code == 200:
                result = response.json()
                task_id = result.get("output", {}).get("task_id")
                if task_id:
                    # Poll for result
                    import time
                    max_wait = 300  # 5 minutes
                    waited = 0
                    while waited < max_wait:
                        time.sleep(10)
                        waited += 10
                        status_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
                        status_resp = requests.get(status_url, headers=headers, timeout=30)
                        if status_resp.status_code == 200:
                            status_data = status_resp.json()
                            task_status = status_data.get("output", {}).get("task_status")
                            if task_status == "SUCCEEDED":
                                video_url = status_data.get("output", {}).get("results", [{}])[0].get("url")
                                if video_url:
                                    r = requests.get(video_url, stream=True, timeout=120)
                                    if r.status_code == 200:
                                        with open(output_path, 'wb') as f:
                                            for chunk in r.iter_content(chunk_size=1024 * 1024):
                                                if chunk:
                                                    f.write(chunk)
                                        print(f"[Qwen] ✅ Video indirildi: {output_path}")
                                        return output_path
                            elif task_status == "FAILED":
                                print(f"[Qwen] ❌ Video üretimi başarısız")
                                break

            return None
        except Exception as e:
            print(f"[Qwen] Hata: {e}")
            return None

    # ─── HuggingFace Video Generation ────────────────────────────────────────
    def generate_huggingface_video(self, prompt, output_path, duration=5):
        """HuggingFace Spaces (Gradio API) ile görüntü üretir, pan/zoom ile videoya çevirir."""
        if not self.hf_token:
            print("[HuggingFace] API key bulunamadı, atlanıyor.")
            return None

        try:
            from gradio_client import Client

            print(f"[HuggingFace] Spaces üzerinden görüntü üretimi: {prompt[:50]}...")

            # Use free HuggingFace Space for image generation
            # Try multiple Spaces in order
            spaces = [
                "stabilityai/stable-diffusion-3-medium",
                "black-forest-labs/FLUX.1-schnell",
                "stabilityai/stable-diffusion-xl-base-1.0",
            ]

            for space_name in spaces:
                try:
                    print(f"[HuggingFace] {space_name} deneniyor...")
                    client = Client(space_name, token=self.hf_token)

                    # Call the text-to-image API
                    result = client.predict(
                        prompt=prompt,
                        api_name="/call"
                    )

                    if result:
                        # result might be a file path or URL
                        img_path = output_path.replace('.mp4', '_temp.png')

                        if isinstance(result, str) and os.path.exists(result):
                            # Local file path from Gradio
                            import shutil
                            shutil.copy2(result, img_path)
                        elif isinstance(result, str) and result.startswith('http'):
                            # URL - download it
                            r = requests.get(result, timeout=60)
                            if r.status_code == 200:
                                with open(img_path, 'wb') as f:
                                    f.write(r.content)
                            else:
                                continue
                        elif isinstance(result, (list, tuple)):
                            # Some spaces return [filepath, seed] etc.
                            file_path = result[0] if result else None
                            if file_path and os.path.exists(str(file_path)):
                                import shutil
                                shutil.copy2(str(file_path), img_path)
                            else:
                                continue
                        else:
                            continue

                        if os.path.exists(img_path):
                            print(f"[HuggingFace] ✅ Görüntü oluşturuldu, animasyon yapılıyor...")
                            return self._animate_image_to_video(img_path, output_path, duration)
                except Exception as e:
                    print(f"[HuggingFace] {space_name} hatası: {str(e)[:100]}")
                    continue

            # Fallback: Try Inference API directly
            print("[HuggingFace] Spaces başarısız, Inference API deneniyor...")
            model_id = "stabilityai/stable-diffusion-xl-base-1.0"
            api_url = f"https://api-inference.huggingface.co/models/{model_id}"
            headers = {"Authorization": f"Bearer {self.hf_token}"}

            response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=120)
            if response.status_code == 503:
                import time
                time.sleep(20)
                response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=120)

            if response.status_code == 200:
                img_path = output_path.replace('.mp4', '_temp.png')
                with open(img_path, 'wb') as f:
                    f.write(response.content)
                print(f"[HuggingFace] ✅ Görüntü oluşturuldu, animasyon yapılıyor...")
                return self._animate_image_to_video(img_path, output_path, duration)
            else:
                print(f"[HuggingFace] Inference API hatası: {response.status_code}")

            return None
        except ImportError:
            print("[HuggingFace] gradio_client yüklü değil, pip install gradio_client")
            return None
        except Exception as e:
            print(f"[HuggingFace] Hata: {e}")
            return None

    # ─── Helper: Animate Image to Video (Pan/Zoom Effect) ─────────────────
    def _animate_image_to_video(self, image_path, output_path, duration=5):
        """Statik görüntüyü pan/zoom efektiyle videoya çevirir."""
        try:
            from moviepy.editor import ImageClip
            import numpy as np

            img = Image.open(image_path)
            w, h = img.size
            
            # Calculate crop dimensions for pan effect
            if w / h > 9 / 16:
                target_w = int(h * 9 / 16)
                start_x = 0
                end_x = w - target_w
            else:
                target_h = int(w * 16 / 9)
                start_y = 0
                end_y = h - target_h
                img = img.resize((w, target_h))
                w, h = img.size
                target_w = int(h * 9 / 16)
                start_x = 0
                end_x = w - target_w

            # Create video with pan effect
            def make_frame(t):
                progress = t / duration
                current_x = int(start_x + (end_x - start_x) * progress)
                crop = img.crop((current_x, 0, current_x + target_w, h))
                crop = crop.resize((1080, 1920))
                return np.array(crop)

            from moviepy.editor import VideoClip
            clip = VideoClip(make_frame, duration=duration)
            clip.write_videofile(output_path, fps=24, codec='libx264', audio=False)
            clip.close()
            
            # Cleanup temp image
            if os.path.exists(image_path):
                os.remove(image_path)
            
            return output_path
        except Exception as e:
            print(f"[Animation] Hata: {e}")
            return None

    # ─── Generate Multiple Video Clips from AI Services ───────────────────
    def generate_ai_video_clips(self, topic, count=6, output_dir="assets/ai_videos", duration=5):
        """Birden fazla AI video klip üretir (Stability, Replicate, Kling, Qwen, HuggingFace)."""
        # Hiç AI video API key'i yoksa hızlıca çık
        has_any_key = any([
            self.stability_api_key,
            self.replicate_api_key,
            self.kling_access_key,
            self.dashscope_api_key,
            self.hf_token,
        ])
        if not has_any_key:
            print("[AI Videos] Hiç AI video API key'i yok, stok videoya geçiliyor.")
            return []

        os.makedirs(output_dir, exist_ok=True)
        clips = []

        prompts = [
            f"futuristic electric car driving on highway at sunset, cinematic 4k, dramatic lighting, {topic}",
            f"EV battery technology close up, laboratory, lithium cells, futuristic blue glow, {topic}",
            f"electric vehicle charging station at night, city lights, cyberpunk aesthetic, {topic}",
            f"Tesla or modern EV dashboard display, holographic interface, technology, {topic}",
            f"aerial view of electric car on winding road, mountains, golden hour, cinematic, {topic}",
            f"electric motor engine technology close up, heat visualization, futuristic, {topic}",
        ]

        # Try each service for each clip
        services = [
            ("Stability", self.generate_stability_video),
            ("Replicate", self.generate_replicate_video),
            ("Kling", self.generate_kling_video),
            ("Qwen", self.generate_qwen_video),
            ("HuggingFace", self.generate_huggingface_video),
        ]
        
        for i in range(min(count, len(prompts))):
            prompt = prompts[i % len(prompts)]
            output_path = os.path.join(output_dir, f"ai_clip_{i}.mp4")
            
            # Try each service until one succeeds
            for service_name, service_func in services:
                try:
                    print(f"[AI Videos] {service_name} deneniyor (klip {i+1}/{count})...")
                    result = service_func(prompt, output_path, duration=duration)
                    if result and os.path.exists(result):
                        clips.append(result)
                        print(f"[AI Videos] ✅ {service_name} ile klip {i+1} oluşturuldu")
                        break
                except Exception as e:
                    print(f"[AI Videos] {service_name} hatası: {e}")
                    continue
            
            if len(clips) <= i:
                print(f"[AI Videos] ⚠️ Klip {i+1} oluşturulamadı")
        
        print(f"[AI Videos] Toplam {len(clips)}/{count} klip oluşturuldu")
        return clips

    def generate_thumbnail(self, video_path, title, output_path,
                           channel_name="EVCARIX", slogan="No hype. Just numbers."):
        """9:16 (1080x1920) dikey thumbnail oluşturur."""
        from PIL import Image, ImageDraw, ImageFont
        from moviepy.editor import VideoFileClip
        try:
            clip = VideoFileClip(video_path)
            frame_time = min(2.0, clip.duration * 0.1)
            frame = clip.get_frame(frame_time)
            clip.close()

            img = Image.fromarray(frame).resize((1080, 1920))

            # Premium Gradient Overlay (Darker & Smoother)
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            for y in range(img.height):
                alpha = int(220 * (y / img.height)**1.5)
                ov_draw.rectangle([(0, y), (img.width, y + 1)], fill=(0, 0, 0, alpha))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Font yükle
            def get_font(font_name, size):
                possible_paths = [
                    f"fonts/{font_name}.ttf",
                    f"C:/Windows/Fonts/{font_name}.ttf",
                    f"C:/Windows/Fonts/{font_name.replace('Bold', 'bd')}.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
                return ImageFont.load_default()

            title_font = get_font("Roboto-Bold", 100)
            ch_font = get_font("Roboto-Bold", 45)
            sl_font = get_font("Roboto-Regular", 32)

            # Başlık satırlarına böl
            words = title.split()
            lines, current = [], ""
            for w in words:
                test = (current + " " + w).strip()
                bbox = draw.textbbox((0, 0), test, font=title_font)
                if bbox[2] - bbox[0] > 1000:
                    lines.append(current)
                    current = w
                else:
                    current = test
            if current:
                lines.append(current)

            # Başlık çiz (Sarı & Siyah Glow + Kalın Stroke)
            y_start = (img.height // 2) - (len(lines) * 55)
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                x = (img.width - (bbox[2] - bbox[0])) // 2

                # Kalın Stroke (Outline)
                stroke_w = 6
                for dx in range(-stroke_w, stroke_w + 1):
                    for dy in range(-stroke_w, stroke_w + 1):
                        draw.text((x + dx, y_start + dy), line, font=title_font, fill=(0, 0, 0))

                # Ana metin
                draw.text((x, y_start), line, font=title_font, fill=(255, 235, 0))
                y_start += 120

            # Kanal & Misyon (Altta bant şeklinde)
            footer_h = 160
            footer_bg = Image.new("RGBA", (img.width, footer_h), (0, 0, 0, 220))
            img_rgba = img.convert("RGBA")
            img_rgba.paste(footer_bg, (0, img.height - footer_h), footer_bg)
            img = img_rgba.convert("RGB")
            draw = ImageDraw.Draw(img)

            # Kanal adı (Vurgulu Yeşil)
            cb = draw.textbbox((0, 0), channel_name, font=ch_font)
            cx = (img.width - (cb[2] - cb[0])) // 2
            draw.text((cx, img.height - 130), channel_name, font=ch_font, fill=(50, 255, 100))

            # Slogan (Parlak Beyaz)
            sb = draw.textbbox((0, 0), slogan, font=sl_font)
            sx = (img.width - (sb[2] - sb[0])) // 2
            draw.text((sx, img.height - 65), slogan.upper(), font=sl_font, fill=(255, 255, 255))

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "PNG")
            print(f"[MediaEngine] Premium Thumbnail kaydedildi: {output_path}")
            return output_path
        except Exception as e:
            print(f"[MediaEngine] Thumbnail hatası: {e}")
            return None

    # ── Kullanılan Klip Takip Sistemi ─────────────────────────────
    def _load_used_clips(self):
        """Daha önce kullanılan video klip hash'lerini yükler."""
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
        """Kullanılan klip listesini diske kaydeder (max 500 kayıt)."""
        clip_list = list(self._used_clips)[-500:]
        with open(self.used_clips_file, "w") as f:
            json.dump(clip_list, f)

    def _get_clip_hash(self, file_path: str) -> str:
        """Dosya adı + boyut = benzersiz tanımlayıcı (MD5 gerektirmez)."""
        try:
            size = os.path.getsize(file_path)
            return f"{os.path.basename(file_path)}_{size}"
        except Exception:
            return os.path.basename(file_path)

    def _filter_used_clips(self, paths: list) -> list:
        """Daha önce kullanılan klipleri listeden çıkarır."""
        fresh, skipped = [], 0
        for p in paths:
            if not p or not os.path.exists(p):
                continue
            clip_hash = self._get_clip_hash(p)
            if clip_hash not in self._used_clips:
                fresh.append(p)
            else:
                skipped += 1
        if skipped > 0:
            print(f"[MediaEngine] 🔄 {skipped} daha önce kullanılan klip atlandı → taze klip kullanılıyor.")
        return fresh

    def mark_clips_as_used(self, paths: list):
        """Video başarıyla üretilince klipleri kullanıldı olarak işaretle."""
        count = 0
        for p in paths:
            if p and os.path.exists(p):
                self._used_clips.add(self._get_clip_hash(p))
                count += 1
        self._save_used_clips()
        print(f"[MediaEngine] ✅ {count} klip 'kullanıldı' olarak kaydedildi → bir daha seçilmeyecek.")
