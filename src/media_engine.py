import os
import random
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger("MediaEngine")

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

    async def download_stock_videos(self, plan=None, target_clip_count=6, topic=None):
        """AI Video Pipeline: Gemini ile sahne tasarımı + AI Video üretimi."""
        video_type = plan.get("video_type", "short") if plan else "short"
        topic_text = topic or (plan.get("topic") if plan else "electric vehicle")
        script     = plan.get("script", "") if plan else ""
        
        needed = 6 if video_type == "short" else 15
        logger.info(f"[MediaEngine] AI Video üretimi başlatılıyor: {topic_text}")

        try:
            # 1. Sahne Tasarımı (Gemini)
            from src.prompt_generator import generate_scene_prompts
            prompts = generate_scene_prompts(topic_text, script, count=needed)
            
            # 2. Video Üretimi (Fal/Kling/Luma/Runway/Seedance/Veo)
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

    # Yardımcı metodlar gerekirse buraya eklenebilir
