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

def generate_title(topic: str, **kwargs) -> str:
    prompt = f"Create ONE viral YouTube title for EV channel: {topic}. Max 60 chars. ONLY the title."
    return _llm_chain(prompt, fallback=f"{topic} - EV Power")

def generate_script(topic: str, duration_s: int = 40, is_long: bool = False, **kwargs) -> dict:
    words = int(duration_s * 2.5)
    if is_long:
        prompt = f"Write a {duration_s}-second deep dive YouTube video script (~{words} words) about: {topic}. Break it down into sections. No hashtags. Professional and informative tone."
    else:
        prompt = f"Write a {duration_s}-second YouTube Shorts voiceover (~{words} words) about: {topic}. No hashtags. Viral and punchy tone."
    
    script = _llm_chain(prompt, fallback=f"Check out the {topic}! Subscribe for more EV data.")
    return {"script": script, "voice": "female"}

def generate_description(topic: str, title: str, tags_list: list, is_long: bool = False, **kwargs) -> str:
    hashtags = " ".join(f"#{t.replace(' ', '')}" for t in tags_list[:10])
    if is_long:
        return f"{title}\n\nIn this video, we dive deep into {topic}.\n\nTimestamps:\n0:00 Intro\n1:30 Deep Analysis\n3:00 Conclusion\n\n{hashtags}"
    return f"{title}\n\n{topic}\n\n{hashtags}"

def generate_tags(topic: str, *args, **kwargs) -> list:
    prompt = f"Generate 10 YouTube tags for: {topic}. Return ONLY JSON list."
    res = call_openrouter(prompt) or '["ev", "tesla"]'
    try:
        # Regex to find JSON list if LLM adds text
        match = re.search(r'\[.*\]', res, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(res)
    except:
        return ["ev", "electric car"]

class CreativeWriter:
    def generate_short_content(self, topic: str):
        title = generate_title(topic)
        script_data = generate_script(topic, duration_s=45)
        tags = generate_tags(topic)
        desc = generate_description(topic, title, tags)
        return {"title": title, "script": script_data["script"], "voice": script_data["voice"], "tags": tags, "description": desc}
    
    def generate_long_content(self, topic: str, duration_s: int = 240):
        title = generate_title(topic)
        script_data = generate_script(topic, duration_s=duration_s, is_long=True)
        tags = generate_tags(topic)
        desc = generate_description(topic, title, tags, is_long=True)
        return {"title": title, "script": script_data["script"], "voice": "male", "tags": tags, "description": desc}
    
    def generate_title(self, topic, **kwargs): return [generate_title(topic)]
    def generate_script(self, topic, **kwargs): return generate_script(topic, **kwargs)
    def generate_tags(self, topic, title, **kwargs): return generate_tags(topic)
    def generate_description(self, **kwargs): return generate_description(kwargs.get('topic'), kwargs.get('title'), kwargs.get('tags_list', []))
