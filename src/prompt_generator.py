import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Gemini kullanarak sahneler tasarlar. Teşhis modu aktiftir."""
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY eksik!")
        return _get_fallback_prompts(topic, count)

    genai.configure(api_key=api_key)
    
    # Kapsamlı model listesi
    model_candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-2.0-flash-exp",
        "gemini-pro",
        "models/gemini-1.5-flash",
        "models/gemini-pro"
    ]

    system_prompt = f"Topic: {topic}\nGenerate exactly {count} cinematic video scene prompts as a JSON array of strings."

    success_text = None
    
    for model_name in model_candidates:
        try:
            logger.info(f"[PromptGen] Deneniyor: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(system_prompt)
            if response and response.text:
                success_text = response.text.strip()
                logger.info(f"[PromptGen] ✅ {model_name} BAŞARILI!")
                break
        except Exception as e:
            err_msg = str(e)
            logger.warning(f"[PromptGen] {model_name} başarısız: {err_msg[:100]}")
            
            # Eğer 404 alıyorsak, API'nin neleri gördüğünü bir kez loglayalım
            if "404" in err_msg and model_name == model_candidates[0]:
                try:
                    logger.info("[PromptGen] 🔍 Mevcut modeller taranıyor...")
                    available_models = [m.name for m in genai.list_models()]
                    logger.info(f"[PromptGen] API'nin gördüğü modeller: {available_models}")
                except: pass
            continue

    if success_text:
        try:
            if "```" in success_text:
                success_text = success_text.split("```")[1].replace("json", "").strip()
            prompts = json.loads(success_text)
            if isinstance(prompts, list) and len(prompts) >= count:
                return prompts[:count]
        except: pass

    logger.warning("[PromptGen] Hiçbir model çalışmadı, fallback'e geçiliyor.")
    return _get_fallback_prompts(topic, count)

def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    # ... (Aynı fallback mantığı)
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
