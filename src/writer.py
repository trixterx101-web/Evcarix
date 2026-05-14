"""
src/writer.py — Evcarix Auto-Studio
====================================
v8.0 REFACTORED:
  - Groq (Primary)
  - OpenRouter (Fallback)
  - Gemini (DISABLED by default)
"""

import os
import time
import random
import logging
import re
import json
from typing import Optional

print("=== NEW WRITER LOADED ===", flush=True)
logger = logging.getLogger("Writer")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

ENABLE_GEMINI = False
PRIMARY_LLM = "groq"

_PLACEHOLDERS = {"", "YOUR_NEW_GEMINI_KEY_HERE", "YOUR_KEY_HERE", "PLACEHOLDER", "none", "None"}
_cooldowns: dict[str, float] = {}   

def _load_keys(env_names: list[str]) -> list[str]:
    seen, out = set(), []
    for name in env_names:
        k = os.getenv(name, "").strip()
        if k and k not in _PLACEHOLDERS:
            if k not in seen:
                seen.add(k)
                out.append(k)
    return out

_GROQ_KEYS = _load_keys(["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"])
_GEMINI_KEYS = _load_keys(["GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3"])

def _available_keys(keys: list[str]) -> list[str]:
    now = time.time()
    return [k for k in keys if _cooldowns.get(k, 0) <= now]

# ─────────────────────────────────────────────────────────────────────────────
# PROVIDERS
# ─────────────────────────────────────────────────────────────────────────────

def call_groq(prompt: str, model: str = "llama-3.3-70b-versatile") -> Optional[str]:
    avail = _available_keys(_GROQ_KEYS)
    if not avail: return None
    try:
        from groq import Groq
        for key in avail:
            try:
                client = Groq(api_key=key)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=900,
                )
                return resp.choices[0].message.content.strip()
            except Exception:
                _cooldowns[key] = time.time() + 120
    except: pass
    return None

def call_openrouter(prompt: str, model: str = "meta-llama/llama-3-8b-instruct:free") -> Optional[str]:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key or key in _PLACEHOLDERS: return None
    try:
        import requests
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except: pass
    return None

def call_openai(prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key in _PLACEHOLDERS: return None
    try:
        import requests
        response = requests.post(
            url="https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            },
            timeout=30
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except: pass
    return None

def call_gemini(prompt: str, model: str = "gemini-2.0-flash") -> Optional[str]:
    if not ENABLE_GEMINI: return None
    avail = _available_keys(_GEMINI_KEYS)
    if not avail: return None
    try:
        import google.generativeai as genai
        for key in avail:
            try:
                genai.configure(api_key=key)
                m = genai.GenerativeModel(model)
                resp = m.generate_content(prompt, request_options={"timeout": 60})
                return resp.text.strip()
            except Exception as e:
                logger.error(f"[Gemini REAL ERROR] {e}")
                _cooldowns[key] = time.time() + 300
    except: pass
    return None

# ─────────────────────────────────────────────────────────────────────────────
# CORE CHAIN
# ─────────────────────────────────────────────────────────────────────────────

def _llm_chain(prompt: str, fallback: str = "") -> str:
    """v8.0 Revised Chain"""
    providers = [
        lambda: call_groq(prompt),
        lambda: call_openrouter(prompt, "meta-llama/llama-3-8b-instruct:free"),
        lambda: call_openrouter(prompt, "mistralai/mistral-7b-instruct"),
    ]
    
    if ENABLE_GEMINI:
        providers.append(lambda: call_gemini(prompt))
    
    for prov in providers:
        try:
            res = prov()
            if res: 
                if "groq" in str(prov): logger.info("[LLM] ✅ Groq aktif")
                return res
        except: continue
        
    return fallback

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API v8.5 (SEO & CTR Optimized)
# ─────────────────────────────────────────────────────────────────────────────

def generate_seo_metadata(topic: str, is_long: bool = False) -> dict:
    """Tek bir LLM çağrısı ile tüm SEO metadatayı (Title, Tags, Hook) üretir."""
    brand_style = (
        "Style: Data-driven, analytical, no-hype. Language: ALWAYS US ENGLISH. Tone: Global Professional. "
        "Identity: Evcarix - The World's Lead EV Data Authority."
    )
    
    if is_long:
        prompt = (
            f"Generate EXPERT YouTube SEO metadata for a 5-10 minute deep-dive EV video about: '{topic}'.\n"
            f"{brand_style}\n"
            "SEO RULES:\n"
            "1. TITLE: Must be high-CTR (Click-Through Rate). Use psychological hooks (Curiosity, Urgency, or Fear). "
            "Put main keywords (e.g., Tesla, Solid-State, Range) at the BEGINNING. Max 70 chars.\n"
            "2. TAGS: Provide 20 'ranked' tags. Include high-volume broad terms, medium-tail specific terms, and 'Evcarix' brand tags.\n"
            "3. DESCRIPTION HOOK: First 2 lines are CRITICAL for SEO. Use keywords naturally.\n"
            "4. KEYWORDS: Extract the 5 most powerful ranking keywords.\n"
            "Return ONLY JSON:\n"
            "{\n"
            "  \"title\": \"[HIGH CTR TITLE]\",\n"
            "  \"tags\": [\"tag1\", \"tag2\", ...],\n"
            "  \"hook\": \"[SEO OPTIMIZED DESCRIPTION OPENER]\",\n"
            "  \"keywords\": [\"kw1\", \"kw2\", ...]\n"
            "}"
        )
    else:
        prompt = (
            f"Generate VIRAL YouTube Shorts SEO metadata for: '{topic}'.\n"
            f"{brand_style}\n"
            "SEO RULES:\n"
            "1. TITLE: Viral style. Use numbers (%, $, Miles). Must stop the scroll. Max 55 chars.\n"
            "2. TAGS: 15 high-velocity trending tags (Shorts-specific).\n"
            "3. HOOK: Punchy, keyword-rich opening sentence.\n"
            "Return ONLY JSON:\n"
            "{\n"
            "  \"title\": \"[VIRAL SHORT TITLE]\",\n"
            "  \"tags\": [\"tag1\", \"tag2\", ...],\n"
            "  \"hook\": \"[PUNCHY HOOK]\"\n"
            "}"
        )
    
    res = _llm_chain(prompt)
    try:
        match = re.search(r'\{.*\}', res, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return {"title": f"{topic} - Reality Check", "tags": ["ev", "electric car"], "hook": "The truth about EVs."}

def generate_script(topic: str, duration_s: int = 40, is_long: bool = False, **kwargs) -> dict:
    words = int(duration_s * 2.4) # Slightly slower for clarity
    tone = "Style: No hype. Just numbers. Fact-first. Language: MANDATORY US ENGLISH. Start with 'Welcome to EV-care-icks.' and end with 'Subscribe to EV-care-icks for real EV data.'"
    
    if is_long:
        prompt = (
            f"Write a professional {duration_s}-second deep-dive script (~{words} words) about: {topic}.\n"
            f"{tone}\n"
            "Structure: Hook -> Data Analysis -> Expert Insight -> Conclusion.\n"
            "CRITICAL: USE US ENGLISH ONLY. GLOBAL PERSPECTIVE ONLY.\n"
            "Output ONLY the script text."
        )
    else:
        prompt = (
            f"Write a viral {duration_s}-second YouTube Shorts script (~{words} words) about: {topic}.\n"
            f"{tone}\n"
            "Use specific percentages and kWh values.\n"
            "CRITICAL: USE US ENGLISH ONLY. GLOBAL PERSPECTIVE ONLY.\n"
            "Output ONLY the script text."
        )
    
    script = _llm_chain(prompt, fallback=f"Welcome to EV-care-icks. Today we analyze {topic}. Subscribe for real data.")
    return {"script": script, "voice": "male" if is_long else "female"}

class CreativeWriter:
    def generate_short_content(self, topic: str):
        meta = generate_seo_metadata(topic, is_long=False)
        script_data = generate_script(topic, duration_s=45, is_long=False)
        
        # Tag temizliği ve 500 karakter sınırı
        raw_tags = meta.get("tags", ["ev", "electric car", "evcarix"])
        final_tags = self._clean_tags(raw_tags)
        
        desc = (
            f"{meta['title']}\n\n"
            f"📊 {meta['hook']}\n\n"
            "Real EV data. No hype. Just numbers. — Evcarix\n\n"
            f"{' '.join(['#' + t.replace(' ', '') for t in final_tags[:10]])}"
        )
        
        return {
            "title": meta['title'],
            "script": script_data["script"],
            "voice": script_data["voice"],
            "tags": final_tags,
            "description": desc,
            "category": "short"
        }
    
    def generate_long_content(self, topic: str, duration_s: int = 240):
        meta = generate_seo_metadata(topic, is_long=True)
        script_data = generate_script(topic, duration_s=duration_s, is_long=True)
        
        final_tags = self._clean_tags(meta.get("tags", []))
        
        # Long description with timestamps
        desc = (
            f"{meta['title']}\n\n"
            f"💡 {meta['hook']}\n\n"
            "In this deep-dive report, we analyze the raw data behind electric vehicle technology.\n\n"
            "📌 Timestamps:\n"
            "0:00 Introduction & Data Hook\n"
            "1:15 Deep Dive Analysis\n"
            "3:30 Final Verdict & Summary\n"
            "4:45 Conclusion\n\n"
            "No hype. Just numbers. Join the Evcarix community.\n\n"
            f"{' '.join(['#' + t.replace(' ', '') for t in final_tags[:12]])}"
        )
        
        return {
            "title": meta['title'],
            "script": script_data["script"],
            "voice": "male",
            "tags": final_tags,
            "description": desc,
            "category": "long"
        }

    def _clean_tags(self, tags: list) -> list:
        """Tags limitine (500 char) ve kaliteye dikkat eder. 'Ranked' mantığı uygular."""
        # En rütbeli/güçlü etiketler en başa
        must_have = ["Evcarix", "Electric Vehicle", "EV", "Tech", "Data", "Shorts"]
        cleaned = []
        for t in must_have:
            cleaned.append(t)
        
        current_len = sum(len(t) + 2 for t in cleaned)
        # LLM'den gelen etiketleri temizle ve ekle
        for t in tags:
            tag = re.sub(r'[^a-zA-Z0-9\s]', '', str(t)).strip()
            if len(tag) < 2 or tag.lower() in [c.lower() for c in cleaned]:
                continue
            # Gereksiz boşlukları temizle
            tag = " ".join(tag.split())
            if current_len + len(tag) + 2 < 480:
                cleaned.append(tag)
                current_len += len(tag) + 2
        return cleaned[:45]
