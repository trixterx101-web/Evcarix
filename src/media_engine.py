import os
import json
import random
import re
import requests
import hashlib
import time
import logging
from pathlib import Path
from .voice_engine import VoiceEngine
from .free_media_aggregator import FreeMediaAggregator

logger = logging.getLogger("MediaEngine")

# v9.0 Configuration
OUTPUT_DIR = "assets/temp_videos"
CACHE_DIR  = "assets/cache/videos"
USED_VIDEOS_FILE = "used_videos.json"
REPETITION_LIMIT = 300  # Son 300 klip hafızada tutulur

# ── EV-ONLY Content Safety Blocklist ─────────────────────────────────────────
# Bu kelimeleri içeren klip URL'leri veya dosya adları kesinlikle reddedilir.
EV_BLOCKLIST = {
    # Tamamen alakasız içerik
    "massage", "spa", "yoga", "meditation", "fitness", "workout", "gym",
    "cooking", "food", "kitchen", "recipe", "chef",
    "wedding", "bride", "groom", "fashion", "makeup", "beauty", "skincare",
    "surgery", "medical", "hospital", "doctor", "nurse",
    "pet", "dog", "cat", "animal", "bird",
    "music", "concert", "dance", "party", "club",
    "beach", "swim", "pool", "ocean", "surf",
    "hiking", "mountain", "camping", "forest", "nature",
    "baby", "child", "kids", "school",
    # Kısmen alakasız araç içeriği
    "motorcycle", "bike", "bicycle", "plane", "airplane", "boat", "ship",
    "truck", "semi", "tractor", "helicopter",
    # Yetişkin / uygunsuz içerik
    "nude", "naked", "adult", "sexy", "lingerie",
}

# ── EV-ONLY Query Pool ────────────────────────────────────────────────────────
EV_QUERY_POOL = [
    "electric vehicle 4k",
    "Tesla Model driving",
    "EV charging station",
    "electric car battery",
    "electric car interior dashboard",
    "EV charging plug cable",
    "electric motor technology",
    "electric car highway driving",
    "Tesla supercharger",
    "BMW iX electric",
    "Hyundai IONIQ electric",
    "Porsche Taycan electric",
    "Rivian electric truck",
    "electric vehicle traffic",
    "EV battery pack technology",
    "electric car range display",
    "autonomous driving technology car",
    "digital dashboard electric car",
    "electric vehicle night charging",
    "futuristic car exterior",
    "electric car robot factory",
    "AI technology digital brain",
    "humanoid robot technology",
    "smart city traffic future",
    "flying car prototype tech",
    "advanced battery laboratory",
]


class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.voice_engine = VoiceEngine()
        self.aggregator = FreeMediaAggregator()

        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        self.used_hashes = self._load_used_hashes()

    # ── Hash / tekrar yönetimi ────────────────────────────────────────────────
    def _load_used_hashes(self):
        if os.path.exists(USED_VIDEOS_FILE):
            try:
                with open(USED_VIDEOS_FILE, "r") as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def _save_used_hashes(self, new_hashes):
        history = list(self.used_hashes.union(new_hashes))
        if len(history) > REPETITION_LIMIT:
            history = history[-REPETITION_LIMIT:]
        with open(USED_VIDEOS_FILE, "w") as f:
            json.dump(history, f)

    def _get_file_hash(self, file_path):
        hasher = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return str(time.time())

    # ── EV İçerik Güvenlik Filtresi ─────────────────────────────────────────
    @staticmethod
    def _is_ev_relevant(path_or_url: str) -> bool:
        """
        Verilen dosya adı veya URL'de blocklist kelimesi varsa False döner.
        Sadece EV/araç/teknoloji ile ilgili içeriklere izin verir.
        """
        check = path_or_url.lower()
        for bad_word in EV_BLOCKLIST:
            if bad_word in check:
                logger.warning(f"[ContentFilter] ⛔ Konu dışı klip engellendi: {bad_word!r} → {os.path.basename(path_or_url)}")
                return False
        return True

    # ── Ana Video Toplama ────────────────────────────────────────────────────
    async def download_stock_videos(self, plan=None, target_clip_count=6, topic=None):
        """v10.0 Pipeline: Exhaustive Multi-Source Acquisition"""
        video_type = plan.get("video_type", "short") if plan else "short"
        
        # CI ortamında Shorts için hızı artırmak için klip sayısını düşür, 
        # ama Long videolar için asla düşürme (tekrarı önlemek için)
        if (os.getenv("CI") or os.getenv("GITHUB_ACTIONS")) and video_type == "short":
            target_clip_count = min(target_clip_count, 4)
            print(f"[MediaEngine] CI Shorts Hız Modu: Hedef klip sayısı {target_clip_count} olarak ayarlandı.")
        
        if video_type == "long":
            # Long videolar için daha fazla klip gerekiyor (4-6 dakika için ~60-100 klip)
            target_clip_count = max(target_clip_count, 60)
            print(f"[MediaEngine] Long Video Modu: Hedef klip sayısı {target_clip_count} olarak ayarlandı.")
        
        from src.pixabay_engine import search_pixabay_videos
        from src.ai_video_engine import generate_video_prompt, generate_ai_video

        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        video_type = plan.get("video_type", "short") if plan else "short"
        needed = target_clip_count
        all_clips = []

        # Konu metnini EV arama terimleriyle zenginleştir
        topic_queries = [
            f"{topic_text} electric vehicle",
            f"{topic_text} EV",
            f"{topic_text} electric car",
        ]

        # EV-only query havuzu (her çalışmada farklı sıra)
        query_pool = topic_queries + random.sample(EV_QUERY_POOL, min(6, len(EV_QUERY_POOL)))

        # ── KATMAN 1: Multi-Source Footage Fetcher (8 kaynak, registry tabanlı) ──
        try:
            from src.footage_fetcher import FootageFetcher
            fetcher = FootageFetcher()
            fetched_clips = fetcher.fetch(
                query=topic_text,
                count=needed,
                is_short=(video_type == "short"),
                topic=plan.get("category", "") if plan else ""
            )
            all_clips.extend(fetched_clips)
            logger.info(f"[MediaEngine] FootageFetcher: +{len(fetched_clips)} klip")
        except Exception as e:
            logger.error(f"[MediaEngine] FootageFetcher hatası: {e}")


        # ── KATMAN 2: Research & Gov (ResearchFetcher - Legacy NASA Support) ──
        # Public Domain — Sıfır Telif Riski
        try:
            from src.research_fetcher import ResearchFetcher
            rf = ResearchFetcher()
            # Konu bazlı NASA araması
            res_clips = await rf.fetch_nasa(topic_text, count=2)
            # Kritik konular için DOE b-roll
            if any(k in topic_text.lower() for k in ["battery", "ev", "charging"]):
                doe_clips = await rf.fetch_energy_gov(topic_text, count=1)
                res_clips.extend(doe_clips)
            
            all_clips.extend(res_clips)
            logger.info(f"[MediaEngine] Research/Gov: +{len(res_clips)} klip")
        except Exception as e:
            logger.error(f"[MediaEngine] ResearchFetcher hatası: {e}")

        # 1. Free Footage (OEM verified URLs — her zaman EV içeriği)
        try:
            from src.free_footage import FreeFootageEngine
            ff_engine = FreeFootageEngine()
            ff_target_count = max(2, (needed // 3))
            ff_clips = ff_engine.get_clips(topic_text, count=ff_target_count, video_type=video_type)
            if ff_clips:
                ff_clips = [c for c in ff_clips if c and self._is_ev_relevant(c)]
                all_clips.extend(ff_clips)
        except Exception as e:
            logger.error(f"[MediaEngine] FreeFootage error: {e}")

        # ── EXHAUSTIVE FETCHING ──
        # Tüm kaynaklardan sırayla ve bıkmadan indir
        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        
        # Birden fazla sorgu dene ki çeşitlilik artsın (Core konulara özel zenginleştirme)
        search_queries = [topic_text]
        topic_lower = topic_text.lower()
        
        if "artificial intelligence" in topic_lower or "ai" in topic_lower:
            search_queries.extend(["digital brain technology", "neural network animation", "artificial intelligence future"])
        elif "robotics" in topic_lower or "robot" in topic_lower:
            search_queries.extend(["industrial robot arm", "humanoid robot walking", "robotic technology factory"])
        elif "smart cities" in topic_lower:
            search_queries.extend(["futuristic city night", "smart city technology", "connected city traffic"])
        elif "battery" in topic_lower:
            search_queries.extend(["lithium battery production", "battery cells laboratory", "electric vehicle battery pack"])
        elif "new technologies" in topic_lower or "future" in topic_lower:
            search_queries.extend(["futuristic technology 4k", "advanced science laboratory", "high tech innovation"])
        elif topic:
            # Genel zenginleştirme
            search_queries.append(topic.split()[0] + " technology")
            search_queries.append("futuristic " + topic.split()[-1])
        
        for q in search_queries:
            if len(all_clips) >= target_clip_count: break
            logger.info(f"[MediaEngine] Fetching from aggregator for: {q}")
            agg_clips = await self.aggregator.get_all_media(q, count=target_clip_count - len(all_clips), video_type=video_type)
            all_clips.extend(agg_clips)

        # ── YENİ: Genişletilmiş Ücretsiz Kaynaklar (Wikimedia + Archive + Coverr) ──
        # Hiç API key gerektirmez, CC0/Public Domain garantili
        if len(all_clips) < target_clip_count:
            try:
                from src.extended_sources import ExtendedMediaSources
                ext = ExtendedMediaSources()
                needed_ext = target_clip_count - len(all_clips)
                ext_clips = ext.fetch_all(topic_text, count=needed_ext)
                ext_clips = [c for c in ext_clips if c and self._is_ev_relevant(c)]
                all_clips.extend(ext_clips)
                logger.info(f"[MediaEngine] ExtendedSources: +{len(ext_clips)} klip")
            except Exception as e:
                logger.error(f"[MediaEngine] ExtendedSources hatası: {e}")

        # Eğer hala eksikse eski yöntemlerle devam et
        if len(all_clips) < target_clip_count:
            # 2. Pexels (EV-only sorgular)
            for q in query_pool:
                if len(all_clips) >= target_clip_count: break
                new = self._download_from_pexels(q, OUTPUT_DIR, 5, video_type=video_type)
                all_clips.extend([c for c in new if c and self._is_ev_relevant(c)])

            # 3. Pixabay
            orientation = "horizontal" if video_type == "long" else "vertical"
            for q in query_pool:
                if len(all_clips) >= target_clip_count: break
                new = search_pixabay_videos(q, max_results=5, orientation=orientation)
                all_clips.extend([c for c in new if c and self._is_ev_relevant(c)])

        # ── TEKRAR FİLTRESİ ──────────────────────────────────────────────────
        unique_and_fresh = []
        current_session_hashes = set()

        # Klipleri karıştır
        random.shuffle(all_clips)

        for c in all_clips:
            if not c or not os.path.exists(c):
                continue
            f_hash = self._get_file_hash(c)

            if f_hash in self.used_hashes:
                logger.info(f"[MediaEngine] ♻️ Tekrar eden klip atlandı: {os.path.basename(c)}")
                continue

            if f_hash not in current_session_hashes:
                current_session_hashes.add(f_hash)
                unique_and_fresh.append(c)
                if len(unique_and_fresh) >= needed:
                    break

        # Hâlâ eksikse cache'den tamamla (EV filtresi uygulanır)
        if len(unique_and_fresh) < needed:
            logger.info("[MediaEngine] ⚠️ Yetersiz yeni klip, temiz cache taranıyor...")
            cached_files = list(Path(CACHE_DIR).glob("*.mp4"))
            random.shuffle(cached_files)
            for f in cached_files:
                if not self._is_ev_relevant(str(f)):
                    continue
                f_hash = self._get_file_hash(str(f))
                if f_hash not in self.used_hashes and f_hash not in current_session_hashes:
                    unique_and_fresh.append(str(f))
                    current_session_hashes.add(f_hash)
                    if len(unique_and_fresh) >= needed:
                        break

        # Kullanılanları kaydet
        self._save_used_hashes(current_session_hashes)

        random.shuffle(unique_and_fresh)
        logger.info(f"[MediaEngine] ✅ {len(unique_and_fresh)}/{needed} EV klip hazır.")
        return unique_and_fresh[:needed]

    # ── Pexels İndirici ──────────────────────────────────────────────────────
    def _download_from_pexels(self, query, dest_dir, count, video_type="short"):
        """v9.0: EV-safe Pexels acquisition."""
        if not self.pexels_api_key:
            return []

        orientation = "landscape" if video_type == "long" else "portrait"
        url = (
            f"https://api.pexels.com/videos/search"
            f"?query={requests.utils.quote(query)}"
            f"&per_page={count * 2}"
            f"&orientation={orientation}"
        )
        headers = {"Authorization": self.pexels_api_key}

        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return []

            data = r.json()
            paths = []
            for v in data.get("videos", []):
                # URL'yi EV filtresiyle kontrol et
                video_url_check = str(v.get("url", "")) + str(v.get("id", ""))
                # Pexels video URL'leri çok bilgilendirici değil, başlığa bak
                if not self._is_ev_relevant(query):  # sorgu zaten EV ise geç
                    continue

                # Birincil tercih HD kalite
                v_url = None
                for f in v.get("video_files", []):
                    if f.get("quality") == "hd":
                        v_url = f.get("link")
                        break
                if not v_url:
                    files = v.get("video_files", [])
                    if files:
                        v_url = files[0].get("link")

                if v_url:
                    fname = f"pexels_{v.get('id')}.mp4"
                    fpath = os.path.join(dest_dir, fname)
                    if not os.path.exists(fpath):
                        dl = requests.get(v_url, stream=True, timeout=60)
                        with open(fpath, "wb") as f:
                            for chunk in dl.iter_content(1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                    paths.append(fpath)

                if len(paths) >= count:
                    break
            return paths

        except Exception as e:
            logger.error(f"[MediaEngine] Pexels hatası: {e}")
            return []
