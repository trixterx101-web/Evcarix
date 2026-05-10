"""
src/ai_video_engine.py — Evcarix Auto-Studio
==========================================
AI Video prompt generation and fallback management.
"""

import logging
import random

logger = logging.getLogger("AIVideoEngine")

AI_PROMPT_TEMPLATES = [
    "Cinematic {topic} driving in Norway winter, vertical 9:16, snow road, realistic EV dashboard, dramatic lighting, 8k",
    "Close up of {topic} battery charging, futuristic neon lights, electricity flowing, technical data overlay, vertical",
    "Futuristic EV city driving at night, cyberpunk aesthetic, rain on windshield, {topic} headlights, vertical 4k",
    "POV driving of {topic} on a scenic mountain road, autumn colors, crisp 8k, smooth gimbal motion, vertical",
    "Macro shot of electric motor spinning, copper coils, high tech machinery, {topic} engineering, vertical cinematic",
]

def generate_video_prompt(topic: str) -> str:
    """
    Konuya göre AI video üretimi için detaylı prompt hazırlar.
    """
    template = random.choice(AI_PROMPT_TEMPLATES)
    prompt = template.format(topic=topic)
    logger.info(f"[AIVideo] Prompt üretildi: {prompt[:60]}...")
    return prompt

async def get_ai_fallback_clip(topic: str) -> str:
    """
    Eğer gerçek video bulunamazsa AI prompt üretir (şimdilik mock).
    """
    prompt = generate_video_prompt(topic)
    # Gelecekte Haiper/Luma API buraya gelecek
    return None # Henüz indirme linki yok
