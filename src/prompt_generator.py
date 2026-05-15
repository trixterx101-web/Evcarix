import os
import json
import logging

logger = logging.getLogger("PromptGenerator")

def generate_scene_prompts(topic: str, script: str, count: int = 6) -> list[str]:
    """Groq ile sahne promptları üret (Gemini başarısız olursa)."""

    # ── 1. Groq (Ücretsiz, Hızlı) ────────────────────────────────
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            logger.info("[PromptGen] Groq deneniyor...")
            from groq import Groq
            client = Groq(api_key=groq_key)

            prompt_text = f"""You are a cinematic video director. Generate exactly {count} short cinematic scene descriptions for a YouTube Shorts video about: '{topic}'

Rules:
- Each scene must be visually descriptive and cinematic
- Focus on electric vehicles, technology, energy
- Return ONLY a valid JSON array of {count} strings, nothing else

Example format:
["scene 1 description", "scene 2 description", ...]"""

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt_text}],
                temperature=0.7,
                max_tokens=500
            )

            text = response.choices[0].message.content
            result = _parse_json_list(text, count)
            if result:
                logger.info(f"[PromptGen] ✅ Groq başarılı: {len(result)} sahne")
                return result
        except Exception as e:
            logger.warning(f"[PromptGen] Groq hatası: {e}")

    # ── 2. Gemini (Yedek) ─────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            logger.info("[PromptGen] Gemini deneniyor...")
            from google import genai
            client = genai.Client(api_key=gemini_key)

            prompt_text = f"Generate exactly {count} cinematic scene descriptions for a video about '{topic}'. Return ONLY a JSON array of strings."
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt_text
            )
            if response and response.text:
                result = _parse_json_list(response.text, count)
                if result:
                    logger.info(f"[PromptGen] ✅ Gemini başarılı: {len(result)} sahne")
                    return result
        except Exception as e:
            logger.warning(f"[PromptGen] Gemini hatası: {e}")

    # ── 3. Statik Fallback ────────────────────────────────────────
    logger.warning("[PromptGen] Tüm AI'lar başarısız, statik fallback kullanılıyor.")
    return _get_fallback_prompts(topic, count)


def _parse_json_list(text, count):
    try:
        clean_text = text.strip()
        if "```" in clean_text:
            clean_text = clean_text.split("```")[1]
            if clean_text.startswith("json"):
                clean_text = clean_text[4:]
        data = json.loads(clean_text.strip())
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return [str(x) for x in v[:count]]
        if isinstance(data, list):
            return [str(x) for x in data[:count]]
    except:
        pass
    return None


def _get_fallback_prompts(topic: str, count: int) -> list[str]:
    base = [
        "Cinematic slow motion shot of an electric car driving on a coastal road, golden hour",
        "Extreme close up of a futuristic EV dashboard with glowing blue lights",
        "Aerial view of a modern charging station in a green city, 4K cinematic",
        "Macro shot of lithium battery cells with electric blue energy flowing",
        "Sleek electric vehicle interior with large panoramic glass roof",
        "Minimalist visualization of electric power lines connecting to a smart car"
    ]
    result = []
    for i in range(count):
        result.append(base[i % len(base)])
    return result
