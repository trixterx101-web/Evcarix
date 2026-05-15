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
        Sadece EV/araç/teknoloji ile     async def download_stock_videos(self, plan=None, target_clip_count=6, topic=None):
        """AI Video Pipeline: Gemini ile sahne tasarımı + AI Video üretimi."""
        video_type = plan.get("video_type", "short") if plan else "short"
        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        script     = plan.get("script", "") if plan else ""
        
        # Shorts için 6 sahne idealdir
        needed = 6 if video_type == "short" else 15
        
        logger.info(f"[MediaEngine] AI Video üretimi başlatılıyor: {topic_text}")

        try:
            # 1. Sahne Tasarımı (Gemini)
            from src.prompt_generator import generate_scene_prompts
            prompts = generate_scene_prompts(topic_text, script, count=needed)
            
            # 2. Video Üretimi (Fal/Kling/Luma/Runway)
            from src.ai_video_generator import AIVideoGenerator
            ai_gen = AIVideoGenerator()
            all_clips = ai_gen.generate_clips(prompts)
            
            if not all_clips:
                logger.error("[MediaEngine] Hiç AI klip üretilemedi!")
                return []

            logger.info(f"[MediaEngine] ✅ {len(all_clips)} AI klip hazır.")
            return all_clips

        except Exception as e:
            logger.error(f"[MediaEngine] AI Pipeline hatası: {e}")
            return []

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
