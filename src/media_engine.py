import os
import random
import logging
import hashlib
import requests
from pathlib import Path

logger = logging.getLogger("MediaEngine")

# Pexels'ta kullanılacak arama terimleri (topic'ten üretilir)
EV_FALLBACK_QUERIES = [
    "electric vehicle charging", "electric car driving", "EV battery",
    "Tesla driving", "electric motor", "sustainable energy car",
    "fast charging station", "electric vehicle technology"
]

class MediaEngine:
    def __init__(self):
        from src.voice_engine import VoiceEngine
        self.voice_engine = VoiceEngine()
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.used_hashes_path = "used_hashes.json"
        self.used_hashes = self._load_used_hashes()

    def _load_used_hashes(self):
        import json
        if os.path.exists(self.used_hashes_path):
            try:
                with open(self.used_hashes_path, "r") as f:
                    return set(json.load(f))
            except: pass
        return set()

    def _save_used_hashes(self, new_hashes):
        import json
        self.used_hashes.update(new_hashes)
        with open(self.used_hashes_path, "w") as f:
            json.dump(list(self.used_hashes), f)

    def _get_file_hash(self, path):
        h = hashlib.md5()
        try:
            with open(path, "rb") as f:
                h.update(f.read(65536))
            return h.hexdigest()
        except: return str(random.random())

    def _build_prompts_from_topic(self, topic: str, count: int) -> list:
        """Gemini olmadan topic'ten basit promptlar üret."""
        words = topic.lower().split()
        base_queries = [
            f"electric vehicle {topic}",
            f"EV charging {topic}",
            f"electric car technology",
            f"battery electric vehicle close up",
            f"sustainable transport future",
            f"electric motor driving highway",
            f"EV dashboard display",
            f"charging station electric car",
        ]
        result = []
        for i in range(count):
            result.append(base_queries[i % len(base_queries)])
        return result

    def _download_pexels_videos(self, query: str, count: int = 2) -> list:
        """Pexels API'dan gerçek stok video indir."""
        if not self.pexels_api_key:
            logger.warning("[MediaEngine] PEXELS_API_KEY yok, Pexels atlanıyor.")
            return []

        out_dir = "assets/footage"
        os.makedirs(out_dir, exist_ok=True)
        clips = []

        try:
            headers = {"Authorization": self.pexels_api_key}
            params = {"query": query, "per_page": count * 2, "orientation": "portrait"}
            r = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params, timeout=15)

            if r.status_code != 200:
                logger.warning(f"[Pexels] HTTP {r.status_code}: {query}")
                return []

            videos = r.json().get("videos", [])
            random.shuffle(videos)

            for video in videos:
                if len(clips) >= count:
                    break

                # En iyi kaliteyi seç (HD tercih)
                files = video.get("video_files", [])
                files_sorted = sorted(files, key=lambda x: x.get("width", 0), reverse=True)
                chosen = None
                for f in files_sorted:
                    if f.get("width", 0) <= 1920:
                        chosen = f
                        break
                if not chosen and files_sorted:
                    chosen = files_sorted[-1]
                if not chosen:
                    continue

                url = chosen.get("link")
                if not url:
                    continue

                vid_id = video.get("id", random.randint(1000, 9999))
                save_path = os.path.join(out_dir, f"pexels_{vid_id}.mp4")

                # Zaten indirilmişse kullan
                if os.path.exists(save_path) and os.path.getsize(save_path) > 10000:
                    clips.append(save_path)
                    continue

                try:
                    resp = requests.get(url, timeout=60, stream=True)
                    if resp.status_code == 200:
                        with open(save_path, "wb") as f:
                            for chunk in resp.iter_content(chunk_size=8192):
                                f.write(chunk)
                        if os.path.getsize(save_path) > 10000:
                            clips.append(save_path)
                            logger.info(f"[Pexels] ✅ İndirildi: {save_path}")
                except Exception as e:
                    logger.warning(f"[Pexels] İndirme hatası: {e}")

        except Exception as e:
            logger.error(f"[Pexels] Genel hata: {e}")

        return clips

    async def download_stock_videos(self, plan=None, target_clip_count=6, topic=None):
        """
        Video Pipeline:
        1. Gemini ile sahne promptları üret (başarısız olursa topic'ten üret)
        2. AI video üret (Fal/Kling/Veo)
        3. Başarısız sahneler için Pexels'tan gerçek stok video indir
        4. Hâlâ eksik varsa FFmpeg fallback
        """
        video_type = plan.get("video_type", "short") if plan else "short"
        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        script = plan.get("script", "") if plan else ""
        needed = 6 if video_type == "short" else 15

        logger.info(f"[MediaEngine] Pipeline başlatılıyor: {topic_text}")

        # ── 1. Sahne Promptları ───────────────────────────────────
        prompts = []
        try:
            from src.prompt_generator import generate_scene_prompts
            prompts = generate_scene_prompts(topic_text, script, count=needed)
            logger.info(f"[MediaEngine] ✅ Gemini promptları üretildi: {len(prompts)} sahne")
        except Exception as e:
            logger.warning(f"[MediaEngine] Gemini prompt hatası, topic'ten üretiliyor: {e}")
            prompts = self._build_prompts_from_topic(topic_text, needed)

        # ── 2. AI Video Üretimi ───────────────────────────────────
        ai_clips = []
        try:
            from src.ai_video_generator import AIVideoGenerator
            ai_gen = AIVideoGenerator()
            ai_clips = ai_gen.generate_clips(prompts)
            logger.info(f"[MediaEngine] AI klipler: {len(ai_clips)}")
        except Exception as e:
            logger.warning(f"[MediaEngine] AI video hatası: {e}")

        # ── 3. Eksik Sahneler için Pexels ─────────────────────────
        all_clips = list(ai_clips)
        
        if len(all_clips) < needed and self.pexels_api_key:
            still_needed = needed - len(all_clips)
            logger.info(f"[MediaEngine] {still_needed} klip eksik, Pexels'a başvuruluyor...")

            # Farklı arama terimleri dene
            search_queries = [
                topic_text,
                f"electric vehicle {topic_text}",
                "electric car technology",
                "EV charging station",
                "sustainable transport",
            ]

            for query in search_queries:
                if len(all_clips) >= needed:
                    break
                pexels_clips = self._download_pexels_videos(query, count=min(3, still_needed))
                for clip in pexels_clips:
                    if clip not in all_clips:
                        all_clips.append(clip)
                        logger.info(f"[Pexels] ✅ Eklendi: {clip}")

        # ── 4. Sonuç ─────────────────────────────────────────────
        if not all_clips:
            logger.error("[MediaEngine] Hiç klip üretilemedi!")
            return []

        logger.info(f"[MediaEngine] ✅ Toplam {len(all_clips)} klip hazır.")
        return all_clips[:needed]
