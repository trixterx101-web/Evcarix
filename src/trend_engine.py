import os
import json
import random
import re
import datetime as dt
import feedparser
import requests
import pandas as pd
from datetime import timezone, timedelta
from dotenv import load_dotenv
load_dotenv()

try:
    from google import genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

TOPIC_HISTORY_FILE = "used_topics.json"
TOPIC_HISTORY_LIMIT = 14

ALLOWED_TOPICS = [
    "battery", "range", "charging", "ownership", "cost",
    "degradation", "LFP", "NMC", "heat pump", "efficiency",
    "winter range", "charging speed", "fast charging", "BMS",
    "real world test", "kWh", "electric vehicle data",
    "EV comparison", "electric car test", "charging network",
    "depreciation", "total cost", "solid state", "WLTP",
]

BLOCKED_TOPICS = [
    "lamborghini", "ferrari", "bugatti", "koenigsegg", "hypercar",
    "supercar", "luxury car", "exotic car", "racing", "drift",
    "formula", "NASCAR", "rally", "stunt", "prank", "vlog",
    "reaction", "challenge", "india", "hindi", "rupee",
    "three wheeler", "scooter", "moped", "rickshaw",
]


class TrendEngine:
    def __init__(self):
        self.feeds = [
            "https://electrek.co/feed/",
            "https://insideevs.com/rss/articles/all/",
            "https://www.teslarati.com/feed/",
            "https://ev-database.org/rss.xml",
            "https://www.greencarreports.com/rss/news",
            "https://cleantechnica.com/feed/",
        ]
        self.ev_search_queries = [
            "electric car range test",
            "EV battery technology 2025",
            "Tesla vs competition real world",
            "electric vehicle charging speed comparison",
            "EV battery degradation data",
            "best electric cars 2025 real test",
            "solid state battery breakthrough",
            "electric car ownership cost analysis",
            "BYD electric car range test",
            "EV winter range cold weather",
            "800V charging electric car comparison",
            "electric car efficiency wh per mile",
            "EV vs hybrid total cost",
            "electric vehicle battery life test",
            "fast charging impact battery health",
        ]

        # Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") if GEMINI_AVAILABLE else None
        self.gemini_client = None
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                print(f"[TrendEngine] Gemini init hatası: {e}")

        # Tüm LLM API key'leri
        self.groq_keys = [k for k in [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ] if k]
        self.openrouter_key    = os.getenv("OPENROUTER_API_KEY")
        self.mistral_key       = os.getenv("MISTRAL_API_KEY")
        self.cohere_key        = os.getenv("COHERE_API_KEY")
        self.together_key      = os.getenv("TOGETHER_API_KEY")

    def _is_relevant(self, title: str) -> bool:
        """Check if video title is relevant to EV data topics."""
        title_lower = title.lower()
        # Reject if any blocked term found
        for blocked in BLOCKED_TOPICS:
            if blocked in title_lower:
                return False
        # Accept if any allowed term found
        for allowed in ALLOWED_TOPICS:
            if allowed in title_lower:
                return True
        # Default: reject if no EV data keyword found
        return False

    def _pick_from_topic_pool(self) -> str | None:
        """Randomly pick a topic from data/topics.csv as fallback."""
        try:
            topics_df = pd.read_csv("data/topics.csv")
            pool = topics_df["topic"].tolist()
            if pool:
                return random.choice(pool)
        except Exception:
            pass
        return None

    # ─── JSON Temizleyici ──────────────────────────────────────────
    def _clean_json(self, text: str) -> str:
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        text = re.sub(r'(?<!\\)[\x00-\x1f\x7f]', ' ', text)
        text = re.sub(r'  +', ' ', text)
        return text

    def _parse_json_safe(self, text: str) -> dict | None:
        try:
            cleaned = self._clean_json(text)
            return json.loads(cleaned)
        except Exception as e:
            print(f"[TrendEngine] JSON parse hatası: {e}")
            return None

    # ─── Konu Geçmişi ─────────────────────────────────────────────
    def _load_topic_history(self):
        if os.path.exists(TOPIC_HISTORY_FILE):
            try:
                with open(TOPIC_HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_topic_history(self, topic):
        history = self._load_topic_history()
        if topic in history:
            history.remove(topic)
        history.append(topic)
        history = history[-TOPIC_HISTORY_LIMIT:]
        with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _is_used_recently(self, topic):
        history = self._load_topic_history()
        topic_lower = topic.lower()
        for h in history:
            if h.lower() in topic_lower or topic_lower in h.lower():
                return True
        return False

    # ─── RSS Haberleri ─────────────────────────────────────────────
    def get_latest_news(self):
        news_items = []
        for url in self.feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    news_items.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.summary if 'summary' in entry else "",
                        "published": entry.published if 'published' in entry else datetime.datetime.now().isoformat(),
                        "source": url.split("//")[1].split("/")[0]
                    })
            except Exception as e:
                print(f"Feed hatası ({url}): {e}")
        return pd.DataFrame(news_items)

    # ─── YouTube Trending ──────────────────────────────────────────
    def get_youtube_trending(self, region_code="US", max_results=20):
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return []
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': region_code,
            'videoCategoryId': '2',
            'maxResults': max_results,
            'key': api_key
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            trending = []
            for it in r.json().get('items', []):
                snip = it.get('snippet', {})
                stats = it.get('statistics', {})
                trending.append({
                    'title': snip.get('title', ''),
                    'channelTitle': snip.get('channelTitle', ''),
                    'videoId': it.get('id'),
                    'viewCount': int(stats.get('viewCount', 0)) if stats.get('viewCount') else 0
                })
            return sorted(trending, key=lambda x: x['viewCount'], reverse=True)
        except Exception as e:
            print(f"[TrendEngine] YouTube trending hatası: {e}")
            return []

    def get_youtube_ev_search(self, max_results=20):
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return []
        query = random.choice(self.ev_search_queries)
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'order': 'viewCount',
            'relevanceLanguage': 'en',
            'maxResults': max_results,
            'key': api_key
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            results = []
            for it in r.json().get('items', []):
                snip = it.get('snippet', {})
                results.append({
                    'title': snip.get('title', ''),
                    'channelTitle': snip.get('channelTitle', ''),
                    'videoId': it.get('id', {}).get('videoId', ''),
                    'query_used': query
                })
            print(f"[TrendEngine] YouTube EV araması '{query}': {len(results)} sonuç")
            return results
        except Exception as e:
            print(f"[TrendEngine] YouTube EV arama hatası: {e}")
            return []

    # ─── YENİ: Son X saatteki EV Short'ları ──────────────────────
    def get_recent_ev_shorts(self, hours_back=6, max_results=15):
        """
        YouTube Data API ile son X saatte yayınlanan EV Short videolarını bulur.
        SADECE başlık + açıklama alır — görüntü/ses ALMAZ — telif riski SIFIR.
        """
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            print("[TrendEngine] YOUTUBE_API_KEY yok, recent EV shorts atlanıyor.")
            return []

        published_after = (datetime.datetime.now(timezone.utc) - timedelta(hours=hours_back))
        published_after_str = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")

        ev_short_queries = [
            "electric car review shorts 2025",
            "EV new model 2025 2026 shorts",
            "electric vehicle launch shorts",
            "tesla new model shorts",
            "BYD electric car review shorts",
            "EV battery range test shorts",
            "electric car comparison shorts",
            "new EV release shorts",
            "EV charging speed test shorts",
            "hyundai kia ioniq ev shorts",
            "rivian lucid electric car shorts",
            "electric car real world test shorts",
        ]
        query = random.choice(ev_short_queries)

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "short",
            "order": "date",
            "publishedAfter": published_after_str,
            "relevanceLanguage": "en",
            "maxResults": max_results,
            "key": api_key,
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("items", [])

            results = []
            ev_keywords = [
                "electric", "ev", "battery", "tesla", "range", "charging",
                "byd", "ioniq", "rivian", "lucid", "volt", "kwh", "hybrid",
                "motor", "watt", "model", "mercedes eq", "bmw i", "kia ev",
                "hyundai", "polestar", "nio", "xpeng", "li auto",
            ]
            for item in items:
                snip = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                title = snip.get("title", "")
                description = snip.get("description", "")
                channel = snip.get("channelTitle", "")
                published = snip.get("publishedAt", "")

                combined = (title + " " + description).lower()
                if not any(kw in combined for kw in ev_keywords):
                    continue

                results.append({
                    "video_id": video_id,
                    "title": title,
                    "description": description[:500],
                    "channel": channel,
                    "published": published,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                })

            print(f"[TrendEngine] Son {hours_back}s: {len(results)} EV Short bulundu (sorgu: '{query}')")
            return results

        except Exception as e:
            print(f"[TrendEngine] get_recent_ev_shorts hatası: {e}")
            return []

    # ─── YENİ: Çoklu LLM ile Script Üretimi ──────────────────────
    def _build_script_prompt(self, video_data: dict) -> tuple[str, str]:
        """System prompt ve user prompt döndürür."""
        title = video_data.get("title", "")
        description = video_data.get("description", "")
        channel = video_data.get("channel", "")

        system = (
            "You are the head writer for Evcarix, a data-driven EV YouTube Shorts channel. "
            "Style: analytical, fact-first, no hype. Motto: 'No hype. Just numbers.' "
            "Always return valid JSON only — no markdown, no extra text, no code blocks."
        )

        user = f"""A competitor channel just published a Short about: "{title}"
Channel: {channel}
Their description: "{description[:300]}"

Write a COMPLETELY ORIGINAL Evcarix Short script inspired by this TOPIC only.
Rules:
- Do NOT copy their words or structure
- Data-driven angle: real stats, percentages, kWh numbers
- Length: 35-45 seconds spoken (80-100 words)
- Start with a shocking stat or surprising fact
- End with: "Subscribe to Evcarix for real EV data."
- English only, USA/Europe/China examples only
- Never mention Turkey or Turkish brands

Return ONLY this JSON (no markdown, no backticks):
{{"topic":"one line topic","title":"YouTube title under 70 chars with specific number","script":"full script text","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7"],"hook":"first sentence only","category":"battery_science|range_tests|charging|comparisons|market_data|education"}}"""

        return system, user

    def _llm_gemini(self, system: str, user: str) -> dict | None:
        """Gemini 2.0 Flash ile üret."""
        if not GEMINI_AVAILABLE or not self.gemini_client:
            return None
        try:
            prompt = f"{system}\n\n{user}"
            resp = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            return self._parse_json_safe(resp.text)
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"[LLM] Gemini kota aşıldı, sonraki LLM'e geçiliyor.")
            else:
                print(f"[LLM] Gemini hatası: {e}")
            return None

    def _llm_groq(self, system: str, user: str, model: str = "llama-3.3-70b-versatile") -> dict | None:
        """Groq ile üret — birden fazla key desteği."""
        if not self.groq_keys:
            return None
        try:
            from groq import Groq
        except ImportError:
            print("[LLM] groq paketi yok: pip install groq")
            return None

        for key in self.groq_keys:
            try:
                client = Groq(api_key=key)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    max_tokens=600,
                    temperature=0.7,
                )
                raw = resp.choices[0].message.content.strip()
                result = self._parse_json_safe(raw)
                if result:
                    return result
            except Exception as e:
                print(f"[LLM] Groq ({model}) hatası: {e}")
                continue
        return None

    def _llm_openrouter(self, system: str, user: str) -> dict | None:
        """
        OpenRouter — 200+ model, ücretsiz tier mevcut.
        Ücretsiz modeller: mistralai/mistral-7b-instruct, nousresearch/nous-capybara-7b vb.
        https://openrouter.ai/keys adresinden ücretsiz key alın.
        """
        if not self.openrouter_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://evcarix.com",
                "X-Title": "Evcarix Auto-Studio",
            }
            # Ücretsiz ve güçlü model
            data = {
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens": 600,
                "temperature": 0.7,
            }
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=data, timeout=30
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            return self._parse_json_safe(raw)
        except Exception as e:
            print(f"[LLM] OpenRouter hatası: {e}")
            return None

    def _llm_mistral(self, system: str, user: str) -> dict | None:
        """
        Mistral AI — mistral-small ücretsiz tier var.
        https://console.mistral.ai/ adresinden ücretsiz key alın.
        """
        if not self.mistral_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.mistral_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "mistral-small-latest",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens": 600,
                "temperature": 0.7,
            }
            r = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers, json=data, timeout=30
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            return self._parse_json_safe(raw)
        except Exception as e:
            print(f"[LLM] Mistral hatası: {e}")
            return None

    def _llm_cohere(self, system: str, user: str) -> dict | None:
        """
        Cohere — command-r ücretsiz tier var (günde 20 istek).
        https://dashboard.cohere.com/api-keys adresinden ücretsiz key alın.
        """
        if not self.cohere_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.cohere_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "command-r",
                "message": user,
                "preamble": system,
                "max_tokens": 600,
                "temperature": 0.7,
            }
            r = requests.post(
                "https://api.cohere.com/v1/chat",
                headers=headers, json=data, timeout=30
            )
            r.raise_for_status()
            raw = r.json().get("text", "").strip()
            return self._parse_json_safe(raw)
        except Exception as e:
            print(f"[LLM] Cohere hatası: {e}")
            return None

    def _llm_together(self, system: str, user: str) -> dict | None:
        """
        Together AI — Llama 3.3 70B, Qwen 2.5 72B ücretsiz $5 kredi.
        https://api.together.xyz adresinden key alın.
        """
        if not self.together_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.together_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens": 600,
                "temperature": 0.7,
            }
            r = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=headers, json=data, timeout=30
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            return self._parse_json_safe(raw)
        except Exception as e:
            print(f"[LLM] Together AI hatası: {e}")
            return None

    def _llm_perplexity(self, system: str, user: str) -> dict | None:
        """
        Perplexity AI — sonar-small-chat ücretsiz $5 kredi.
        https://www.perplexity.ai/settings/api adresinden key alın.
        """
        if not self.perplexity_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.perplexity_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens": 600,
                "temperature": 0.7,
            }
            r = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers, json=data, timeout=30
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            return self._parse_json_safe(raw)
        except Exception as e:
            print(f"[LLM] Perplexity hatası: {e}")
            return None

    def _llm_deepseek(self, system: str, user: str) -> dict | None:
        """
        DeepSeek — deepseek-chat çok ucuz ($0.14/1M token).
        https://platform.deepseek.com/api_keys adresinden key alın.
        """
        if not self.deepseek_key:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_key}",
                "Content-Type": "application/json",
            }
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "max_tokens": 600,
                "temperature": 0.7,
            }
            r = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers, json=data, timeout=30
            )
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            return self._parse_json_safe(raw)
        except Exception as e:
            print(f"[LLM] DeepSeek hatası: {e}")
            return None

    def _llm_huggingface(self, system: str, user: str) -> dict | None:
        """
        HuggingFace Inference API — ücretsiz tier (Mistral 7B, Zephyr vb.).
        https://huggingface.co/settings/tokens adresinden ücretsiz key alın.
        """
        if not self.huggingface_key:
            return None
        try:
            model = "mistralai/Mistral-7B-Instruct-v0.3"
            headers = {
                "Authorization": f"Bearer {self.huggingface_key}",
                "Content-Type": "application/json",
            }
            prompt = f"<s>[INST] {system}\n\n{user} [/INST]"
            data = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 600,
                    "temperature": 0.7,
                    "return_full_text": False,
                },
            }
            r = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers=headers, json=data, timeout=60
            )
            r.raise_for_status()
            result = r.json()
            if isinstance(result, list) and result:
                raw = result[0].get("generated_text", "").strip()
                return self._parse_json_safe(raw)
        except Exception as e:
            print(f"[LLM] HuggingFace hatası: {e}")
        return None

    def _llm_ollama(self, system: str, user: str) -> dict | None:
        """
        Ollama — yerel LLM (ücretsiz, internet gerekmez).
        Kurulum: https://ollama.ai → ollama run llama3
        GitHub Actions'da çalışmaz, local geliştirme için.
        """
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if r.status_code != 200:
                return None
        except Exception:
            return None

        models_to_try = ["llama3.3", "llama3.1", "llama3", "mistral", "qwen2.5"]
        available = [m["name"].split(":")[0] for m in r.json().get("models", [])]

        chosen = next((m for m in models_to_try if m in available), None)
        if not chosen:
            return None

        try:
            data = {
                "model": chosen,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 600},
            }
            resp = requests.post(
                f"{self.ollama_url}/api/chat",
                json=data, timeout=120
            )
            resp.raise_for_status()
            raw = resp.json()["message"]["content"].strip()
            result = self._parse_json_safe(raw)
            if result:
                print(f"[LLM] Ollama ({chosen}) başarılı.")
            return result
        except Exception as e:
            print(f"[LLM] Ollama hatası: {e}")
            return None

    def generate_inspired_script(self, video_data: dict) -> dict | None:
        """
        Bulunan YouTube videosunun SADECE başlık+açıklamasından ilham alarak
        tamamen orijinal Evcarix script üretir.
        LLM öncelik: Gemini → Groq 70B → Groq 8B → OpenRouter → Mistral →
                     Cohere → Together → Perplexity → DeepSeek → HuggingFace → Ollama
        """
        system, user = self._build_script_prompt(video_data)

        llm_pipeline = [
            ("Gemini 2.0 Flash",        lambda: self._llm_gemini(system, user)),
            ("Groq Llama3.3-70B",       lambda: self._llm_groq(system, user, "llama-3.3-70b-versatile")),
            ("Groq Llama3.1-8B",        lambda: self._llm_groq(system, user, "llama-3.1-8b-instant")),
            ("OpenRouter Mistral-7B",   lambda: self._llm_openrouter(system, user)),
            ("Mistral Small",           lambda: self._llm_mistral(system, user)),
            ("Cohere Command-R",        lambda: self._llm_cohere(system, user)),
            ("Together Llama3.3-70B",   lambda: self._llm_together(system, user)),
            ("Perplexity Sonar",        lambda: self._llm_perplexity(system, user)),
            ("DeepSeek Chat",           lambda: self._llm_deepseek(system, user)),
            ("HuggingFace Mistral-7B",  lambda: self._llm_huggingface(system, user)),
            ("Ollama (local)",          lambda: self._llm_ollama(system, user)),
        ]

        for name, fn in llm_pipeline:
            try:
                print(f"[LLM] {name} deneniyor...")
                result = fn()
                if result and all(k in result for k in ["topic", "title", "script"]):
                    result["source_video_id"] = video_data.get("video_id", "")
                    result["source_title"]    = video_data.get("title", "")
                    result["inspired_by"]     = video_data.get("url", "")
                    print(f"[LLM] ✅ {name} başarılı: {result['title'][:50]}")
                    return result
                else:
                    print(f"[LLM] {name} geçersiz yanıt döndü, sonraki deneniyor.")
            except Exception as e:
                print(f"[LLM] {name} exception: {e}")
                continue

        print("[LLM] ❌ Tüm LLM'ler başarısız. Script üretilemedi.")
        return None

    def trigger_from_youtube_trend(self, hours_back=48) -> dict | None:
        """
        Ana tetikleyici:
        1. Son X saatteki EV Short'larını bul
        2. Daha önce kullanılmamış birini seç
        3. Orijinal script üret (çoklu LLM)
        4. daily_plan.json formatında kaydet ve döndür
        """
        print(f"\n[TrendEngine] 🔍 Son {hours_back}s EV Short'ları taranıyor...")

        recent_videos = self.get_recent_ev_shorts(hours_back=hours_back)
        if not recent_videos:
            print("[TrendEngine] Yeni EV Short bulunamadı, normal moda geçiliyor.")
            return None

        # Apply topic relevance filter
        candidates = [v for v in recent_videos if self._is_relevant(v["title"])]
        if not candidates:
            print("[TrendEngine] ⚠️ Hiç uygun trend yok, konu havuzuna geçiliyor.")
            return None

        # Kullanılmamış video seç
        selected_video = None
        for video in candidates:
            if not self._is_used_recently(video["title"]):
                selected_video = video
                break

        if not selected_video:
            print("[TrendEngine] Tüm bulunan videolar daha önce kullanılmış.")
            return None

        print(f"[TrendEngine] 🎯 Seçilen trend : {selected_video['title'][:60]}")
        print(f"[TrendEngine] 📺 Kaynak kanal  : {selected_video['channel']}")
        print(f"[TrendEngine] 🔗 İlham URL      : {selected_video['url']}")
        print(f"[TrendEngine] ⚠️  NOT: Görüntü/ses kopyalanmıyor — sadece konu ilhamı")

        script_data = self.generate_inspired_script(selected_video)
        if not script_data:
            return None

        self._save_topic_history(selected_video["title"])

        now = datetime.datetime.now()
        tags = script_data.get("tags", [])
        for must in ["ev", "electriccar", "evcarix", "Shorts", "ElectricVehicle"]:
            if must not in tags:
                tags.append(must)

        plan = {
            "timestamp":   now.strftime("%Y%m%d_%H%M%S"),
            "slot":        os.getenv("UPLOAD_SLOT", "evening"),
            "config":      {"type": "short", "duration": 55},
            "topic":       script_data["topic"],
            "full_topic":  script_data["topic"],
            "category":    script_data.get("category", "trend"),
            "title":       script_data["title"],
            "all_titles":  [script_data["title"]],
            "script":      script_data["script"],
            "voice":       random.choice(["male", "female"]),
            "description": (
                f"{script_data['title']}\n\n"
                f"Real EV data. No hype. Just numbers. — Evcarix\n\n"
                f"What you'll learn:\n"
                f"— {script_data.get('hook', script_data['topic'])}\n\n"
                f"{chr(10).join('#' + t.replace(' ', '') for t in tags[:15])}"
            ),
            "tags":        tags,
            "variation": {
                "cta_style":  "Subscribe to Evcarix for real EV data.",
                "hook_style": "trend",
                "emoji_set":  ["⚡", "🔋", "📊"],
            },
            "inspired_by":     script_data.get("inspired_by", ""),
            "source_video_id": script_data.get("source_video_id", ""),
        }

        with open("daily_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)

        print(f"[TrendEngine] ✅ Trend plan kaydedildi → daily_plan.json")
        print(f"[TrendEngine] 📝 Başlık: {plan['title']}")
        return plan

    # ─── Mevcut Ana Konu Seçici (değişmedi) ───────────────────────
    def select_trending_topic(self, news_df):
        ev_keywords = [
            'ev', 'electric', 'battery', 'tesla', 'range', 'charging',
            'volt', 'watt', 'efficiency', 'byd', 'ioniq', 'rivian', 'lucid',
            'solid state', 'lithium', 'kwh', 'kilowatt', 'hybrid', 'motor'
        ]
        def is_ev_related(title):
            t = title.lower()
            return any(word in t for word in ev_keywords)

        yt_ev = self.get_youtube_ev_search(max_results=20)
        random.shuffle(yt_ev)
        for item in yt_ev:
            title = item['title']
            if is_ev_related(title) and not self._is_used_recently(title):
                clean = title.encode('ascii', 'ignore').decode('ascii')
                print(f"[TrendEngine] YouTube EV search: {clean}")
                self._save_topic_history(title)
                return title

        yt = self.get_youtube_trending(region_code=os.getenv('YOUTUBE_REGION', 'US'))
        candidates = [i for i in yt if is_ev_related(i['title'])]
        random.shuffle(candidates)
        for item in candidates:
            title = item['title']
            if not self._is_used_recently(title):
                clean = title.encode('ascii', 'ignore').decode('ascii')
                print(f"[TrendEngine] YouTube trending: {clean}")
                self._save_topic_history(title)
                return title

        if GEMINI_AVAILABLE and self.gemini_client and news_df is not None and not news_df.empty:
            try:
                titles = news_df['title'].tolist()
                random.shuffle(titles)
                unused = [t for t in titles if not self._is_used_recently(t)]
                pool = (unused if unused else titles)[:20]
                prompt = (
                    "You are a technical EV analyst for 'Evcarix'. "
                    "Pick the ONE most data-driven, technical headline. "
                    "Return ONLY the headline text.\n\n"
                    + "\n".join(f"- {t}" for t in pool)
                )
                response = self.gemini_client.models.generate_content(
                    model='gemini-2.0-flash', contents=prompt
                )
                selected = response.text.strip()
                if any(t.lower() in selected.lower() or selected.lower() in t.lower() for t in pool):
                    print(f"[TrendEngine] Gemini RSS: {selected}")
                    self._save_topic_history(selected)
                    return selected
            except Exception as e:
                print(f"[TrendEngine] Gemini error: {e}")

        core_topics = [
            "Real-world EV range test vs manufacturer claims",
            "Battery degradation: LFP vs NMC after 100k miles",
            "Winter range loss in modern electric cars: real data",
            "EV charging speed: 400V vs 800V architecture comparison",
            "True cost of EV ownership over 100k miles",
            "Heat pump efficiency in extreme cold weather",
            "Solid-state battery progress: real timeline and data",
            "EV efficiency: Wh/km breakdown by model",
            "Tesla Model 3 vs BYD Seal: head-to-head efficiency test",
            "DC fast charging impact on battery health: long-term data",
        ]
        unused_core = [t for t in core_topics if not self._is_used_recently(t)]
        pool = unused_core if unused_core else core_topics
        selected_core = random.choice(pool)
        print(f"[TrendEngine] Core fallback: {selected_core}")
        self._save_topic_history(selected_core)
        return selected_core


# ── JSON Temizleyici ────────────────────────────────────────────
    def _clean_json(self, text: str) -> str:
        import re
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        text = re.sub(r'(?<!\\)[\x00-\x1f\x7f]', ' ', text)
        text = re.sub(r'  +', ' ', text)
        return text

    # ── Son X saatteki EV Short'ları ───────────────────────────────
    def get_recent_ev_shorts(self, hours_back=6, max_results=15):
        """
        YouTube Data API ile son X saatte yayınlanan EV Short'larını bulur.
        SADECE başlık + açıklama alır — görüntü/ses ALMAZ — telif riski SIFIR.
        """
        from datetime import timezone, timedelta
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            print("[TrendEngine] YOUTUBE_API_KEY yok.")
            return []

        published_after = (dt.datetime.now(timezone.utc) - timedelta(hours=hours_back))
        published_after_str = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")

        queries = [
            "electric car review shorts 2025",
            "EV new model 2025 2026 shorts",
            "electric vehicle launch shorts",
            "tesla new model shorts",
            "BYD electric car review shorts",
            "EV battery range test shorts",
            "electric car comparison shorts",
            "Hyundai Kia EV shorts",
            "rivian lucid electric car shorts",
            "EV charging speed test shorts",
        ]
        query = random.choice(queries)

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "short",
            "order": "date",
            "publishedAfter": published_after_str,
            "relevanceLanguage": "en",
            "maxResults": max_results,
            "key": api_key,
        }
        try:
            r = requests.get("https://www.googleapis.com/youtube/v3/search",
                             params=params, timeout=15)
            r.raise_for_status()
            items = r.json().get("items", [])

            ev_kw = ["electric", "ev", "battery", "tesla", "range", "charging",
                     "byd", "ioniq", "rivian", "lucid", "volt", "kwh", "hybrid",
                     "motor", "watt", "mercedes eq", "bmw i", "kia ev", "hyundai",
                     "polestar", "nio", "xpeng"]
            results = []
            for item in items:
                snip = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                title = snip.get("title", "")
                description = snip.get("description", "")
                combined = (title + " " + description).lower()
                if not any(kw in combined for kw in ev_kw):
                    continue
                results.append({
                    "video_id": video_id,
                    "title": title,
                    "description": description[:500],
                    "channel": snip.get("channelTitle", ""),
                    "published": snip.get("publishedAt", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                })
            print(f"[TrendEngine] Son {hours_back}s: {len(results)} EV Short (sorgu: '{query}')")
            return results
        except Exception as e:
            print(f"[TrendEngine] get_recent_ev_shorts hatası: {e}")
            return []

    # ── Çoklu LLM ile orijinal script üret ─────────────────────────
    def generate_inspired_script(self, video_data: dict) -> dict | None:
        """
        YouTube videosunun SADECE başlık+açıklamasından ilham alarak
        tamamen orijinal Evcarix script üretir.
        LLM Öncelik: Gemini → Groq 70B → Groq 8B → OpenRouter → Mistral →
                     Cohere → Together → Perplexity → DeepSeek → HuggingFace
        """
        title = video_data.get("title", "")
        description = video_data.get("description", "")
        channel = video_data.get("channel", "")

        system = (
            "You are the head writer for Evcarix, a data-driven EV YouTube Shorts channel. "
            "Style: analytical, fact-first, no hype. Motto: 'No hype. Just numbers.' "
            "Always return valid JSON only — no markdown, no extra text."
        )
        user = (
            f"A competitor published a Short about: \"{title}\"\n"
            f"Channel: {channel}\n"
            f"Their description: \"{description[:300]}\"\n\n"
            f"Write a COMPLETELY ORIGINAL Evcarix script inspired by this TOPIC only.\n"
            f"Rules:\n"
            f"- Do NOT copy their words or sentence structure\n"
            f"- Data-driven: real stats, %, kWh, miles numbers\n"
            f"- 35-45 seconds spoken (80-100 words)\n"
            f"- Start with a shocking specific stat\n"
            f"- End with: 'Subscribe to Evcarix for real EV data.'\n"
            f"- English only, USA/Europe/China examples ONLY\n"
            f"- Never mention Turkey\n\n"
            f"Return ONLY this JSON (no backticks):\n"
            f'{{"topic":"one line topic","title":"YouTube title under 70 chars with number",'
            f'"script":"full script","tags":["tag1","tag2","tag3","tag4","tag5","tag6","tag7"],'
            f'"hook":"first sentence","category":"battery_science|range_tests|charging|comparisons|market_data|education"}}'
        )

        # LLM pipeline (CreativeWriter ile aynı sıra)
        llm_calls = [
            ("Gemini",      lambda: self._call_llm_gemini(system, user)),
            ("Groq 70B",    lambda: self._call_llm_groq(system, user, "llama-3.3-70b-versatile")),
            ("Groq 8B",     lambda: self._call_llm_groq(system, user, "llama-3.1-8b-instant")),
            ("OpenRouter",  lambda: self._call_llm_openrouter(system, user)),
            ("Mistral",     lambda: self._call_llm_mistral(system, user)),
            ("Cohere",      lambda: self._call_llm_cohere(system, user)),
            ("Together",    lambda: self._call_llm_together(system, user)),
            ("Perplexity",  lambda: self._call_llm_perplexity(system, user)),
            ("DeepSeek",    lambda: self._call_llm_deepseek(system, user)),
            ("HuggingFace", lambda: self._call_llm_huggingface(system, user)),
        ]

        for name, fn in llm_calls:
            try:
                print(f"[LLM] {name} deneniyor...")
                raw = fn()
                if not raw:
                    continue
                cleaned = self._clean_json(raw)
                import re as _re
                match = _re.search(r'\{.*\}', cleaned, _re.DOTALL)
                if match:
                    result = json.loads(match.group())
                    if all(k in result for k in ["topic", "title", "script"]):
                        result["source_video_id"] = video_data.get("video_id", "")
                        result["source_title"]    = title
                        result["inspired_by"]     = video_data.get("url", "")
                        print(f"[LLM] ✅ {name}: {result['title'][:50]}")
                        return result
            except Exception as e:
                print(f"[LLM] {name} hata: {e}")

        print("[LLM] ❌ Tüm LLM'ler başarısız.")
        return None

    def _call_llm_gemini(self, system, user):
        if not GEMINI_AVAILABLE or not self.gemini_client:
            return None
        try:
            resp = self.gemini_client.models.generate_content(
                model='gemini-2.0-flash', contents=f"{system}\n\n{user}")
            return resp.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print("[LLM] Gemini kota →")
            else:
                print(f"[LLM] Gemini: {e}")
            return None

    def _call_llm_groq(self, system, user, model):
        groq_keys = [k for k in [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ] if k]
        if not groq_keys:
            return None
        try:
            from groq import Groq
            for key in groq_keys:
                try:
                    client = Groq(api_key=key)
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system},
                                  {"role": "user", "content": user}],
                        max_tokens=600, temperature=0.7,
                    )
                    return resp.choices[0].message.content.strip()
                except Exception as e:
                    if "429" in str(e) or "rate_limit" in str(e).lower():
                        continue
                    raise
        except Exception as e:
            print(f"[LLM] Groq ({model}): {e}")
        return None

    def _call_llm_openrouter(self, system, user):
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            return None
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "HTTP-Referer": "https://evcarix.com"},
                json={"model": "mistralai/mistral-7b-instruct:free",
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}],
                      "max_tokens": 600},
                timeout=30,
            )
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM] OpenRouter: {e}")
            return None

    def _call_llm_mistral(self, system, user):
        key = os.getenv("MISTRAL_API_KEY")
        if not key:
            return None
        try:
            r = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "mistral-small-latest",
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}],
                      "max_tokens": 600},
                timeout=30,
            )
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM] Mistral: {e}")
            return None

    def _call_llm_cohere(self, system, user):
        key = os.getenv("COHERE_API_KEY")
        if not key:
            return None
        try:
            r = requests.post(
                "https://api.cohere.com/v1/chat",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "command-r", "message": user, "preamble": system, "max_tokens": 600},
                timeout=30,
            )
            return r.json().get("text", "").strip()
        except Exception as e:
            print(f"[LLM] Cohere: {e}")
            return None

    def _call_llm_together(self, system, user):
        key = os.getenv("TOGETHER_API_KEY")
        if not key:
            return None
        try:
            r = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}],
                      "max_tokens": 600},
                timeout=30,
            )
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM] Together: {e}")
            return None

    def _call_llm_perplexity(self, system, user):
        key = os.getenv("PERPLEXITY_API_KEY")
        if not key:
            return None
        try:
            r = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-sonar-small-128k-online",
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}],
                      "max_tokens": 600},
                timeout=30,
            )
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM] Perplexity: {e}")
            return None

    def _call_llm_deepseek(self, system, user):
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            return None
        try:
            r = requests.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat",
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user", "content": user}],
                      "max_tokens": 600},
                timeout=30,
            )
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[LLM] DeepSeek: {e}")
            return None

    def _call_llm_huggingface(self, system, user):
        key = os.getenv("HUGGINGFACE_API_KEY")
        if not key:
            return None
        try:
            model = "mistralai/Mistral-7B-Instruct-v0.3"
            prompt_text = f"<s>[INST] {system}\n\n{user} [/INST]"
            r = requests.post(
                f"https://api-inference.huggingface.co/models/{model}",
                headers={"Authorization": f"Bearer {key}"},
                json={"inputs": prompt_text,
                      "parameters": {"max_new_tokens": 600,
                                     "temperature": 0.7,
                                     "return_full_text": False}},
                timeout=60,
            )
            result = r.json()
            if isinstance(result, list) and result:
                return result[0].get("generated_text", "").strip()
        except Exception as e:
            print(f"[LLM] HuggingFace: {e}")
        return None

    # ── Ana Trend Tetikleyici ───────────────────────────────────────
    def trigger_from_youtube_trend(self, hours_back=48) -> dict | None:
        """
        1. Son X saatteki EV Short'larını bul
        2. Kullanılmamış birini seç
        3. Tamamen orijinal script üret (çoklu LLM)
        4. daily_plan.json formatında döndür
        """
        print(f"\n[TrendEngine] 🔍 Son {hours_back}s EV Short'ları taranıyor...")
        recent = self.get_recent_ev_shorts(hours_back=hours_back)
        if not recent:
            print("[TrendEngine] Yeni EV Short bulunamadı.")
            return None

        selected = None
        for video in recent:
            if not self._is_used_recently(video["title"]):
                selected = video
                break

        if not selected:
            print("[TrendEngine] Tüm bulunan videolar daha önce kullanılmış.")
            return None

        print(f"[TrendEngine] 🎯 Seçilen  : {selected['title'][:60]}")
        print(f"[TrendEngine] 📺 Kanal    : {selected['channel']}")
        print(f"[TrendEngine] 🔗 İlham URL: {selected['url']}")
        print(f"[TrendEngine] ⚠️  NOT      : Görüntü/ses kopyalanmıyor — sadece konu ilhamı")

        script_data = self.generate_inspired_script(selected)
        if not script_data:
            return None

        self._save_topic_history(selected["title"])

        now = dt.datetime.now()
        tags = script_data.get("tags", [])
        for must in ["ev", "electriccar", "evcarix", "Shorts", "ElectricVehicle"]:
            if must not in tags:
                tags.append(must)

        plan = {
            "timestamp":       now.strftime("%Y%m%d_%H%M%S"),
            "slot":            os.getenv("UPLOAD_SLOT", "evening"),
            "config":          {"type": "short", "duration": 55},
            "topic":           script_data["topic"],
            "full_topic":      script_data["topic"],
            "category":        script_data.get("category", "trend"),
            "title":           script_data["title"],
            "all_titles":      [script_data["title"]],
            "script":          script_data["script"],
            "voice":           random.choice(["male", "female"]),
            "description":     (
                f"{script_data['title']}\n\n"
                f"Real EV data. No hype. Just numbers. — Evcarix\n\n"
                f"What you'll learn:\n"
                f"— {script_data.get('hook', script_data['topic'])}\n\n"
                f"{chr(10).join('#' + t.replace(' ', '') for t in tags[:15])}"
            ),
            "tags":            tags,
            "variation": {
                "cta_style":  "Subscribe to Evcarix for real EV data.",
                "hook_style": "trend",
                "emoji_set":  ["⚡", "🔋", "📊"],
            },
            "inspired_by":     script_data.get("inspired_by", ""),
            "source_video_id": script_data.get("source_video_id", ""),
        }

        with open("daily_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)

        print(f"[TrendEngine] ✅ Trend plan kaydedildi → daily_plan.json")
        print(f"[TrendEngine] 📝 Başlık: {plan['title']}")
        return plan


if __name__ == "__main__":
    engine = TrendEngine()
    news = engine.get_latest_news()
    result = engine.trigger_from_youtube_trend(hours_back=24)
    if result:
        print("BAŞARILI:", result['title'])
    else:
        print("Trend bulunamadı, normal topic:", engine.select_trending_topic(news))
