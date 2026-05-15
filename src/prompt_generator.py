import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Gemini kullanarak sinematik video sahneleri tasarlar."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY eksik!")
        return _get_fallback_prompts(topic, count)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    system_prompt = f"""You are a cinematic video director for YouTube Shorts.
Topic: {topic}
Script Summary: {script[:500]}

Generate exactly {count} different cinematic video scene prompts.
Each prompt = one 5-second high-quality shot that visually represents this topic.

Rules:
- Photorealistic, 8K, cinematic lighting, dramatic composition.
- No text, no logos, no watermarks, no distorted faces.
- Each scene must be visually distinct from the others.
- Optimized for portrait (9:16) AI video generation.
- Focus on tech, electric vehicles, and future energy aesthetics.

Return ONLY a JSON array of {count} strings. No explanation."""

    try:
        response = model.generate_content(system_prompt)
        text = response.text.strip()
        
        # Markdown bloklarını temizle
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        
        prompts = json.loads(text)
        if isinstance(prompts, list) and len(prompts) >= count:
            logger.info(f"✅ Gemini {len(prompts)} sahne tarifi üretti.")
            return prompts[:count]
    except Exception as e:
        logger.error(f"Gemini prompt üretimi hatası: {e}")
    
    return _get_fallback_prompts(topic, count)

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    """Gemini başarısız olursa konu bazlı hazır kaliteli promptlar döner."""
    FALLBACKS = {
        "battery": [
            "Extreme macro shot of glowing lithium battery cells with blue energy pulses, 8K cinematic lighting",
            "Automated electric vehicle battery assembly line with robotic arms and blue laser sparks",
            "Holographic display showing battery charge percentage increasing, futuristic lab background",
            "Close up of an EV charging port with glowing blue light reflections on wet pavement at night",
            "Solid state battery architecture visualization with electric currents flowing through crystals",
            "Futuristic energy storage facility with walls of glowing power cells, cinematic wide shot"
        ],
        "default": [
            "Cinematic shot of a futuristic electric car driving through a neon city at night, rain reflections",
            "High tech laboratory with researchers working on advanced energy systems, blue ambient light",
            "Aerial drone shot of a vast solar farm during golden hour, cinematic 4K",
            "Abstract visualization of clean energy flowing through a digital smart city grid",
            "Futuristic robotic hand holding a glowing energy core, mechanical detail, 8K",
            "Sleek electric vehicle interior with large glowing dashboard screens and ambient lighting"
        ]
    }
    key = "battery" if "battery" in topic.lower() else "default"
    return FALLBACKS[key][:count]
