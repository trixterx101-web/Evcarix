import os
import random
import requests
import logging
from pathlib import Path

logger = logging.getLogger("AIVideoEngine")

AI_PROMPT_TEMPLATES = [
    "Cinematic {topic} futuristic EV, neon lights, 4k, digital art",
    "Close up {topic} battery tech, glowing circuits, cyberpunk",
    "Futuristic electric car city driving, rainy night, synthwave",
    "Minimalist {topic} interior, clean interface, white aesthetic",
    "Technical schematic {topic}, blue holographic lines, 3d data"
]

def generate_video_prompt(topic: str) -> str:
    template = random.choice(AI_PROMPT_TEMPLATES)
    return template.format(topic=topic)

async def generate_ai_video(prompt: str, video_type="short") -> str | None:
    """
    v8.5: AI Video Generation / Artistic Fallback.
    Şu an için özel 'Artistik' sorgularla stok sitelerinden en kaliteli sahneleri seçer.
    Gelecekte buraya Luma/Haiper API anahtarları eklenebilir.
    """
    logger.info(f"[AIVideo] Generating artistic scene for: {prompt[:50]}")
    
    # Gerçek bir AI Video API'si yoksa (Luma, Runway vb.), 
    # stok sitelerindeki en artistik/fütüristik klipleri 'AI üretimi' gibi kullanırız.
    try:
        from src.media_engine import MediaEngine
        me = MediaEngine()
        
        # Pexels'de 'artistic' ve 'futuristic' araması yap
        search_query = f"futuristic {prompt.split(',')[0]}"
        clips = me._download_from_pexels(search_query, "assets/temp_videos", 1, video_type=video_type)
        
        if clips:
            logger.info(f"[AIVideo] Artistic clip acquired: {clips[0]}")
            return clips[0]
            
        return None
    except Exception as e:
        logger.error(f"[AIVideo] AI generation hatası: {e}")
        return None
