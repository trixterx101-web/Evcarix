"""
src/writer.py — Evtrix Auto-Studio
====================================
v8.6 BRAND OPTIMIZED:
  - Updated global brand name to 'Evtrix'
  - Groq (Primary) / OpenRouter (Fallback)
  - Dynamic Title selection between Fact and Curiosity/Question
"""

import os
import time
import random
import logging
import re
import json
from typing import Optional

print("=== WRITER RE-LOADED FOR BRAND: EVTRIX ===", flush=True)
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
_GEMINI_KEYS = _load_keys(["GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"])

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
# PUBLIC API v8.6 (Evtrix Optimized)
# ─────────────────────────────────────────────────────────────────────────────

def generate_seo_metadata(topic: str, is_long: bool = False) -> dict:
    """Tek bir LLM çağrısı ile tüm SEO metadatayı (Title, Tags, Hook, SEO Description) üretir."""
    brand_style = (
        "Style: Data-driven, analytical, no-hype. Language: ALWAYS US ENGLISH. Tone: Global Professional. "
        "Identity: Evtrix - The Lead Electric Vehicle Data Authority."
    )
    
    if is_long:
        prompt = (
            f"Generate EXPERT YouTube SEO metadata for a 5-10 minute deep-dive EV video about: '{topic}'.\n"
            f"{brand_style}\n"
            "SEO RULES:\n"
            "1. Generate TWO TITLE VERSIONS (Version A: Fact-based, Version B: Curiosity-based).\n"
            "2. Max 70 chars per title. High-CTR. Put main search keywords at the absolute BEGINNING.\n"
            "3. TAGS: 20 high-ranking tags including broad and specific search terms.\n"
            "4. DESCRIPTION HOOK: Two different opener lines (Hook A and Hook B).\n"
            "5. SEO DESCRIPTION: A detailed, keyword-rich description paragraph (3-4 sentences) that naturaly describes the topic for search algorithm indexation.\n"
            "Return ONLY JSON:\n"
            "{\n"
            "  \"title_a\": \"[FACT TITLE]\",\n"
            "  \"title_b\": \"[CURIOSITY TITLE]\",\n"
            "  \"tags\": [\"tag1\", \"tag2\", ...],\n"
            "  \"hook_a\": \"[HOOK VERSION A]\",\n"
            "  \"hook_b\": \"[HOOK VERSION B]\",\n"
            "  \"keywords\": [\"kw1\", \"kw2\", ...],\n"
            "  \"seo_description\": \"[Detailed SEO Description Paragraph]\"\n"
            "}"
        )
    else:
        prompt = (
            f"Generate VIRAL YouTube Shorts SEO metadata for: '{topic}'.\n"
            f"{brand_style}\n"
            "SEO RULES:\n"
            "1. Generate TWO TITLE VERSIONS (Version A: Number-heavy, Version B: Question-based).\n"
            "2. Max 55 chars per title. High-CTR viral style. Use numbers (%, $, Miles).\n"
            "3. TAGS: 15 high-velocity trending tags including viral short-form tags.\n"
            "4. HOOK: Two punchy, keyword-rich opening sentences (Hook A and Hook B).\n"
            "5. SEO SUMMARY: A short 2-sentence punchy summary filled with search terms.\n"
            "Return ONLY JSON:\n"
            "{\n"
            "  \"title_a\": \"[NUMBER TITLE]\",\n"
            "  \"title_b\": \"[QUESTION TITLE]\",\n"
            "  \"tags\": [\"tag1\", \"tag2\", ...],\n"
            "  \"hook_a\": \"[PUNCHY HOOK A]\",\n"
            "  \"hook_b\": \"[PUNCHY HOOK B]\",\n"
            "  \"seo_description\": \"[Short SEO Summary]\"\n"
            "}"
        )

    res = _llm_chain(prompt)
    try:
        match = re.search(r'\{.*\}', res, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return {
        "title_a": f"{topic.upper()} - Reality Check", 
        "title_b": f"The Truth About {topic}?", 
        "tags": ["ev", "electric car", "evtrix"], 
        "hook_a": "The truth about EVs.", 
        "hook_b": "Shocking EV numbers.",
        "seo_description": f"Exploring the latest data and trends behind {topic}. We break down the key numbers and what they mean for the future."
    }

def generate_script(topic: str, duration_s: int = 40, is_long: bool = False, **kwargs) -> dict:
    words = int(duration_s * 2.4)
    
    if is_long:
        tone = "Style: No hype. Just numbers. Fact-first. Language: MANDATORY US ENGLISH. Start naturally with a strong hook without saying hello. End with 'Subscribe to Evtrix for real EV data.'"
        prompt = (
            f"Write a professional {duration_s}-second deep-dive script (~{words} words) about: {topic}.\n"
            f"{tone}\n"
            "Structure: Hook -> Data Analysis -> Expert Insight -> Conclusion.\n"
            "CRITICAL: USE US ENGLISH ONLY. GLOBAL PERSPECTIVE ONLY.\n"
            "Output ONLY the script text."
        )
    else:
        tone = "Style: No hype. Just numbers. Fact-first. Language: MANDATORY US ENGLISH. CRITICAL RULE: NEVER use introduction phrases like 'Welcome to', 'In this video', or 'Hello'. Start IMMEDIATELY with a shocking number, statistic, or fact. End naturally with 'Subscribe to Evtrix for real data.'"
        prompt = (
            f"Write a viral {duration_s}-second YouTube Shorts script (~{words} words) about: {topic}.\n"
            f"{tone}\n"
            "Use specific percentages and kWh values.\n"
            "CRITICAL: USE US ENGLISH ONLY. GLOBAL PERSPECTIVE ONLY.\n"
            "Output ONLY the script text."
        )
    
    script = _llm_chain(prompt, fallback=f"Fact check on {topic}. Real data shows surprising trends. Subscribe to Evtrix for more.")
    return {"script": script, "voice": "male" if is_long else "female"}

class CreativeWriter:
    def generate_short_content(self, topic: str):
        meta = generate_seo_metadata(topic, is_long=False)
        script_data = generate_script(topic, duration_s=45, is_long=False)
        
        final_tags = self._clean_tags(meta.get("tags", ["ev", "ai", "tech"]))
        
        chosen_title = random.choice([meta.get('title_a'), meta.get('title_b')])
        if not chosen_title:
            chosen_title = meta.get('title', topic)
        
        desc = (
            f"⚡ {meta.get('hook_a', meta.get('hook', 'Interesting data.'))}\n\n"
            f"{meta.get('seo_description', 'Exploring the latest news and facts.')}\n\n"
            "🔔 Subscribe for daily tech updates & real EV data.\n"
            "📱 Follow Evtrix for more insights.\n\n"
            f"{' '.join(['#' + t.replace(' ', '') for t in final_tags[:8]])}"
        )
        
        return {
            "title": chosen_title,
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
        
        desc = (
            f"🚀 {meta.get('hook_a', meta.get('hook', 'Expert analysis.'))}\n\n"
            f"{meta.get('seo_description', 'Deep-diving into the raw data and trends.')}\n\n"
            "⚡ Key points covered:\n"
            "- Industry-leading data analysis\n"
            "- Technical specifications & performance\n"
            "- Future market impact\n\n"
            "📌 Timestamps:\n"
            "0:00 Introduction & Hook\n"
            "1:15 Deep Analysis\n"
            "3:30 Final Verdict\n\n"
            "🔔 Subscribe to Evtrix: The Lead EV Data Authority.\n\n"
            f"{' '.join(['#' + t.replace(' ', '') for t in final_tags[:12]])}"
        )
        
        chosen_title = random.choice([meta.get('title_a'), meta.get('title_b')])
        if not chosen_title:
            chosen_title = meta.get('title', f"{topic} — EV Data Deep Dive")
            
        return {
            "title": chosen_title,
            "script": script_data["script"],
            "voice": "male",
            "tags": final_tags,
            "description": desc,
            "category": "long"
        }

    def _clean_tags(self, tags: list) -> list:
        """Tags limitine ve kaliteye dikkat eder. 'Ranked' mantığı uygular."""
        must_have = ["Evtrix", "Electric Vehicle", "EV", "Tech", "Data", "Shorts"]
        cleaned = []
        for t in must_have:
            cleaned.append(t)
        
        current_len = sum(len(t) + 2 for t in cleaned)
        for t in tags:
            tag = re.sub(r'[^a-zA-Z0-9\s]', '', str(t)).strip()
            if len(tag) < 2 or tag.lower() in [c.lower() for c in cleaned]:
                continue
            tag = " ".join(tag.split())
            if current_len + len(tag) + 2 < 480:
                cleaned.append(tag)
                current_len += len(tag) + 2
        return cleaned[:45]
