"""
Evcarix CreativeWriter
YouTube Trend SEO + Viral Optimizasyon
LLM: Gemini → Groq 70B → Groq 8B → OpenRouter → Mistral →
     Cohere → Together → Perplexity → DeepSeek → HuggingFace
"""
import os
import re
import json
import random
import requests

try:
    from google import genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()

CHANNEL_CORE_TAGS = [
    "ev", "electric car", "electric vehicle", "evcarix",
    "EV data", "real world EV test", "battery technology",
    "no hype just numbers", "EV range test", "EV charging",
]

TOP_SHORTS_HASHTAGS = [
    "#Shorts", "#EV", "#ElectricCar", "#ElectricVehicle",
    "#Tesla", "#EVBattery", "#BYD", "#EVRange", "#Evcarix",
    "#EVCharging", "#EVReview", "#ElectricCarReview",
    "#EVData", "#BatteryTech", "#EVShorts",
]

VIRAL_TITLE_TEMPLATES = {
    "battery_science": [
        "This EV Battery Lost {pct}% in Just {time}",
        "LFP vs NMC: The {pct}% Difference After {miles} Miles",
        "Why EV Owners Are Losing ${cost} Every Year on Battery",
        "Real Battery Degradation Rate: {pct}% in {miles} Miles",
        "The Hidden Battery Problem No One Talks About",
    ],
    "range_tests": [
        "EV Promises {range} Miles — Gets {real} in Reality",
        "Real Highway Range: {pct}% Less Than Advertised",
        "EV at {temp}°F: Only {range} Miles Left",
        "{miles}-Mile EV Real Test: The Shocking Truth",
        "Why This EV's {range}-Mile Claim Is Wrong",
    ],
    "charging": [
        "800V vs 400V: {min} Minutes Difference — Real Test",
        "Real DC Fast Charging Cost: ${cost} Per 100 Miles",
        "Why Charging Speed Drops After {pct}% Battery",
        "{min}-Minute Charge Claim? We Tested It",
        "Home vs DC Fast Charging: ${cost}/Year Difference",
    ],
    "comparisons": [
        "Tesla vs BYD: Who Actually Wins on Real Range",
        "We Tested Both — The Data Doesn't Lie",
        "Real Data: This EV Beats Tesla by {miles} Miles",
        "EV Comparison 2025: The Numbers Are Surprising",
        "{brand1} vs {brand2}: {pct}% Performance Gap",
    ],
    "cost_ownership": [
        "EV True Cost: ${cost} More Than Dealers Say",
        "{pct}% of EV Owners Overpay by ${cost}",
        "5-Year EV Cost vs Gas: Real Math, No Hype",
        "Hidden EV Costs: ${cost} Nobody Warns You About",
        "Why Your EV Costs ${cost}/Year More Than Expected",
    ],
    "market_data": [
        "EV Sales Dropped {pct}% — Here's the Real Reason",
        "China EVs Are {pct}% Cheaper: The Truth Behind It",
        "BYD Beat Tesla with {pct}% Market Share — Real Data",
        "{pct}% of US Buyers Chose EV Last Quarter",
        "EV Market 2025: {count}M Units, 1 Clear Winner",
    ],
    "education": [
        "Why Your EV Loses {pct}% Range Below {temp}°F",
        "EV Regen Braking: Adds {pct}% Range — Tested",
        "How Heat Pump Saves {pct}% Battery in Winter",
        "What {kw}kW Really Means for Your Daily Drive",
        "The Physics Behind {pct}% EV Efficiency Loss",
    ],
}


class CreativeWriter:
    def __init__(self):
        # Gemini
        self.gemini_api_keys = []
        if GEMINI_AVAILABLE:
            for i in range(1, 4):
                key = os.getenv(f"GEMINI_API_KEY_{i}") if i > 1 else os.getenv("GEMINI_API_KEY")
                if key:
                    self.gemini_api_keys.append(key)
        self.gemini_client = None
        if GEMINI_AVAILABLE and self.gemini_api_keys:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_keys[0])
            except Exception as e:
                print(f"[Writer] Gemini init hatası: {e}")

        # Tüm LLM key'leri
        self.groq_keys = [k for k in [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY_2"),
            os.getenv("GROQ_API_KEY_3"),
        ] if k]
        self.openrouter_key  = os.getenv("OPENROUTER_API_KEY")
        self.mistral_key     = os.getenv("MISTRAL_API_KEY")
        self.cohere_key      = os.getenv("COHERE_API_KEY")
        self.together_key    = os.getenv("TOGETHER_API_KEY")
        self.perplexity_key  = os.getenv("PERPLEXITY_API_KEY")
        self.deepseek_key    = os.getenv("DEEPSEEK_API_KEY")
        self.huggingface_key = os.getenv("HUGGINGFACE_API_KEY")

    # ── JSON Temizleyici ────────────────────────────────────────────
    def _clean_json(self, text: str) -> str:
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()
        text = re.sub(r'(?<!\\)[\x00-\x1f\x7f]', ' ', text)
        text = re.sub(r'  +', ' ', text)
        return text

    # ── Merkezi LLM çağrısı — 10 servis, sıralı fallback ───────────
    def _call_llm(self, system: str, user: str, max_tokens: int = 600) -> str | None:
        # 1. Gemini
        if GEMINI_AVAILABLE and self.gemini_api_keys:
            for key in self.gemini_api_keys:
                try:
                    client = genai.Client(api_key=key)
                    resp = client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents=f"{system}\n\n{user}"
                    )
                    if resp.text:
                        print("[LLM] ✅ Gemini")
                        return resp.text.strip()
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        print("[LLM] Gemini kota aşıldı →")
                    else:
                        print(f"[LLM] Gemini: {e}")

        # 2. Groq 70B
        for key in self.groq_keys:
            try:
                from groq import Groq
                client = Groq(api_key=key)
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=max_tokens, temperature=0.7,
                )
                text = resp.choices[0].message.content.strip()
                if text:
                    print("[LLM] ✅ Groq 70B")
                    return text
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    print("[LLM] Groq 70B kota →")
                else:
                    print(f"[LLM] Groq 70B: {e}")

        # 3. Groq 8B
        for key in self.groq_keys:
            try:
                from groq import Groq
                client = Groq(api_key=key)
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    max_tokens=max_tokens, temperature=0.7,
                )
                text = resp.choices[0].message.content.strip()
                if text:
                    print("[LLM] ✅ Groq 8B")
                    return text
            except Exception as e:
                print(f"[LLM] Groq 8B: {e}")

        # 4. OpenRouter
        if self.openrouter_key:
            try:
                r = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openrouter_key}",
                             "Content-Type": "application/json",
                             "HTTP-Referer": "https://evcarix.com"},
                    json={"model": "mistralai/mistral-7b-instruct:free",
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": user}],
                          "max_tokens": max_tokens},
                    timeout=30,
                )
                text = r.json()["choices"][0]["message"]["content"].strip()
                if text:
                    print("[LLM] ✅ OpenRouter")
                    return text
            except Exception as e:
                print(f"[LLM] OpenRouter: {e}")

        # 5. Mistral
        if self.mistral_key:
            try:
                r = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.mistral_key}",
                             "Content-Type": "application/json"},
                    json={"model": "mistral-small-latest",
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": user}],
                          "max_tokens": max_tokens},
                    timeout=30,
                )
                text = r.json()["choices"][0]["message"]["content"].strip()
                if text:
                    print("[LLM] ✅ Mistral")
                    return text
            except Exception as e:
                print(f"[LLM] Mistral: {e}")

        # 6. Cohere
        if self.cohere_key:
            try:
                r = requests.post(
                    "https://api.cohere.com/v1/chat",
                    headers={"Authorization": f"Bearer {self.cohere_key}",
                             "Content-Type": "application/json"},
                    json={"model": "command-r", "message": user,
                          "preamble": system, "max_tokens": max_tokens},
                    timeout=30,
                )
                text = r.json().get("text", "").strip()
                if text:
                    print("[LLM] ✅ Cohere")
                    return text
            except Exception as e:
                print(f"[LLM] Cohere: {e}")

        # 7. Together AI
        if self.together_key:
            try:
                r = requests.post(
                    "https://api.together.xyz/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.together_key}",
                             "Content-Type": "application/json"},
                    json={"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": user}],
                          "max_tokens": max_tokens},
                    timeout=30,
                )
                text = r.json()["choices"][0]["message"]["content"].strip()
                if text:
                    print("[LLM] ✅ Together")
                    return text
            except Exception as e:
                print(f"[LLM] Together: {e}")

        # 8. Perplexity
        if self.perplexity_key:
            try:
                r = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers={"Authorization": f"Bearer {self.perplexity_key}",
                             "Content-Type": "application/json"},
                    json={"model": "llama-3.1-sonar-small-128k-online",
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": user}],
                          "max_tokens": max_tokens},
                    timeout=30,
                )
                text = r.json()["choices"][0]["message"]["content"].strip()
                if text:
                    print("[LLM] ✅ Perplexity")
                    return text
            except Exception as e:
                print(f"[LLM] Perplexity: {e}")

        # 9. DeepSeek
        if self.deepseek_key:
            try:
                r = requests.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {self.deepseek_key}",
                             "Content-Type": "application/json"},
                    json={"model": "deepseek-chat",
                          "messages": [{"role": "system", "content": system},
                                       {"role": "user", "content": user}],
                          "max_tokens": max_tokens},
                    timeout=30,
                )
                text = r.json()["choices"][0]["message"]["content"].strip()
                if text:
                    print("[LLM] ✅ DeepSeek")
                    return text
            except Exception as e:
                print(f"[LLM] DeepSeek: {e}")

        # 10. HuggingFace
        if self.huggingface_key:
            try:
                model = "mistralai/Mistral-7B-Instruct-v0.3"
                prompt_text = f"<s>[INST] {system}\n\n{user} [/INST]"
                r = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers={"Authorization": f"Bearer {self.huggingface_key}"},
                    json={"inputs": prompt_text,
                          "parameters": {"max_new_tokens": max_tokens,
                                         "temperature": 0.7,
                                         "return_full_text": False}},
                    timeout=60,
                )
                result = r.json()
                if isinstance(result, list) and result:
                    text = result[0].get("generated_text", "").strip()
                    if text:
                        print("[LLM] ✅ HuggingFace")
                        return text
            except Exception as e:
                print(f"[LLM] HuggingFace: {e}")

        print("[LLM] ❌ Tüm LLM servisleri başarısız.")
        return None

    # ── SEO Anahtar Kelime Çıkarıcı (tag + title için) ─────────────
    def _extract_seo_keywords(self, topic: str) -> dict:
        topic_lower = topic.lower()
        
        # Markalar ve Modeller
        brand_map = {
            "tesla": ["Tesla Model Y", "Tesla Model 3", "Tesla FSD"],
            "byd": ["BYD Seal", "BYD Atto 3", "BYD Dolphin"],
            "hyundai": ["Hyundai IONIQ 5", "Hyundai IONIQ 6"],
            "kia": ["Kia EV6", "Kia EV9"],
            "bmw": ["BMW iX", "BMW i4"],
            "mercedes": ["Mercedes EQS", "Mercedes EQE"],
            "volkswagen": ["VW ID.4", "VW ID.3", "ID.7"],
            "audi": ["Audi Q4 e-tron", "Audi e-tron GT"],
            "porsche": ["Porsche Taycan"],
            "rivian": ["Rivian R1S", "Rivian R1T"],
            "lucid": ["Lucid Air"],
            "nio": ["NIO ET7", "NIO ET5"],
            "polestar": ["Polestar 2", "Polestar 3"],
            "ford": ["Ford Mach-E", "F-150 Lightning"],
            "chevrolet": ["Chevy Blazer EV", "Equinox EV"],
        }
        
        # Teknolojiler (Search Volume Yüksek)
        tech_map = {
            "lfp": ["LFP battery degradation", "LFP vs NMC"],
            "nmc": ["NMC battery efficiency"],
            "range": ["real-world EV range", "EV highway range test"],
            "charging": ["EV fast charging speed", "800V charging architecture"],
            "winter": ["EV winter range loss", "cold weather performance"],
            "degradation": ["battery health", "100k mile test"],
            "solid state": ["solid state battery 2026", "new battery tech"],
            "cost": ["EV ownership cost", "is EV cheaper than gas"],
            "used": ["used EV market", "buying used electric car"],
        }
        
        found_brands = []
        for kw, tags in brand_map.items():
            if kw in topic_lower:
                found_brands.extend(tags)
                
        found_tech = []
        for kw, tags in tech_map.items():
            if kw in topic_lower:
                found_tech.extend(tags)
                
        return {
            "primary": found_brands[:1] + found_tech[:1],
            "secondary": found_brands[1:3] + found_tech[1:3]
        }

    # ── Başlık ─────────────────────────────────────────────────────
    def generate_title(self, topic, history_titles=None, category=None, format_type="short"):
        history_block = ""
        if history_titles:
            recent = history_titles[-20:]
            history_block = (
                "\nCRITICAL — NEVER repeat these used titles (no similar patterns or hooks):\n"
                + "\n".join(f"- {t}" for t in recent) + "\n"
            )

        keywords = self._extract_seo_keywords(topic)
        primary_kw = keywords["primary"][0] if keywords["primary"] else topic.split()[0]
        
        if format_type == "long":
            char_range = "60-75"
            format_rules = (
                f"LONG VIDEO TITLE RULES (Search Focus):\n"
                f"1. START with the Primary Keyword: '{primary_kw}'\n"
                f"2. Use colon or vertical bar: 'Primary Keyword: Secondary Detail (Result)'\n"
                f"3. Add 2025/2026 year tag for freshness\n"
                f"4. Add parenthetical for CTR: (Honest Truth), (Data Revealed), (Real World Test)\n"
                f"Example: '{primary_kw}: Real Range Loss After 3 Years (2025 Data)'"
            )
        else:
            char_range = "50-62"
            format_rules = (
                f"SHORTS TITLE RULES (Viral/Suggested Focus):\n"
                f"1. SHOCKING NUMBER first to stop the scroll\n"
                f"2. Mention '{primary_kw}' in the first 3 words if possible\n"
                f"3. Zero filler words (no 'The', 'How to', 'Look at')\n"
                f"Example: '23% Battery Loss? {primary_kw} Cold Weather Test ❄️'"
            )

        system = (
            "You are a YouTube Metadata Master. Your goal is to get videos to #1 in Search and "
            "into the 'Up Next' suggested feed. You understand that Search = Exact Keywords, "
            "Suggested = High CTR + Topic SIGNAL. American English only."
        )
        user = (
            f"Write 5 high-performing YouTube title variants for Evcarix.\n"
            f"Topic: {topic}\nCategory: {category or 'general'}\n"
            f"Target Format: {'Long-form Deep Dive' if format_type == 'long' else 'Shorts'}\n\n"
            f"{format_rules}\n\n"
            f"SEO REQUIREMENTS:\n"
            f"- Length: {char_range} chars (YouTube truncates at 70 on mobile)\n"
            f"- Numbers: MUST include real data (%, $, miles, kWh, minutes, years)\n"
            f"- Power words: REAL, BRUTAL, TRUTH, EXPOSED, HONEST, COST, FAILED\n"
            f"- Geography: USA/Europe/China ONLY — NO Turkey/Middle East references\n"
            f"- Return ONLY a JSON array of 5 strings."
        )

        raw = self._call_llm(system, user, max_tokens=500)
        if raw:
            try:
                cleaned = self._clean_json(raw)
                match = re.search(r'\[.*?\]', cleaned, re.DOTALL)
                if match:
                    titles = json.loads(match.group())
                    if isinstance(titles, list) and titles:
                        history_set = {h.lower() for h in (history_titles or [])}
                        fresh = [t for t in titles if t.lower() not in history_set]
                        return (fresh[:5] if fresh else titles[:5])
            except Exception as e:
                print(f"[Writer] Title parse: {e}")

        # Fallback
        max_c = 75 if format_type == "long" else 65
        templates = VIRAL_TITLE_TEMPLATES.get(category, [
            f"Real {topic[:30]} Data: {random.randint(10,40)}% Gap Exposed",
            f"Why {topic[:25]} Costs ${random.randint(200,800)} More",
            f"{topic[:30]}: {random.randint(15,45)}% Worse Than Claimed",
            f"The Hidden Truth About {topic[:25]}",
            f"{topic[:30]} After {random.randint(50,200)}k Miles: Brutal Truth",
        ])
        return [t[:max_c] for t in templates[:5]]

    # ── Senaryo ────────────────────────────────────────────────────
    def generate_script(self, topic, format_type="short", category=None):
        category_instructions = {
            "battery_science": (
                "Battery chemistry deep-dive. Use: LFP vs NMC vs NCA degradation %, "
                "cycle counts, temperature effects in °C and °F, real lab data. "
                "Example phrases: 'After 1000 cycles, capacity dropped to X%...'"
            ),
            "range_tests": (
                "Real-world range test. Use: EPA/WLTP vs actual miles, speed in mph, "
                "temperature, Wh/mile. Example: 'We drove 300 miles at 70mph, real range was X% below EPA...'"
            ),
            "charging": (
                "Charging technology. Use: kW peak, minutes to 80%, charge curve, "
                "400V vs 800V, cost per kWh. Example: '10 to 80% in 18 minutes, peak power dropped after 45%...'"
            ),
            "comparisons": (
                "Head-to-head data. Side-by-side: range, efficiency, charging speed, price. "
                "Example: 'Car A wins range by X miles, but Car B charges X minutes faster...'"
            ),
            "cost_ownership": (
                "Financial breakdown. Real $amounts: 5-year cost, maintenance, insurance, depreciation. "
                "Example: 'Total 5-year cost: $X, saving $Y vs gas...'"
            ),
            "market_data": (
                "Industry stats. Use: market share %, sales volume, USA/Europe/China, YoY growth. "
                "Example: 'BYD overtook Tesla with X% share in Q1 2025...'"
            ),
            "education": (
                "Technical explainer. Simple analogies + physics. "
                "Example: 'Think of it like a pipe — at 70mph, aero drag consumes X% of battery...'"
            ),
            "infrastructure": (
                "Infrastructure data. Charger counts, uptime %, coverage maps, smart charging. "
                "Example: 'The network has 95% uptime, but apartment dwellers face a 3-year payback...'"
            ),
        }
        cat_extra = category_instructions.get(
            category, "Focus on real data, numbers, measurable facts. No marketing hype.")

        if format_type == "short":
            # Shorts script with explicit word count
            MIN_WORDS_SHORT = 90   # enough for 40s at 130wpm
            MAX_WORDS_SHORT = 130  # enough for 60s at 130wpm
            
            system = (
                "You are Evcarix's head scriptwriter. Style: data-first, analytical, no hype. "
                "Motto: 'No hype. Just numbers.' American English only. "
                "Return format: SES: [male/female]\nSENARYO: [script]"
            )
            user = f"""
Write a 60-second YouTube Shorts narration script for the "Ev-CAR-ix" channel.
Topic: {topic}
Category: {category or 'general'}
Category guide: {cat_extra}
REQUIRED word count: {MIN_WORDS_SHORT} to {MAX_WORDS_SHORT} words (this is mandatory — do not write fewer)

Structure (write ALL sections as continuous spoken text):
- Hook (0-5s): One shocking data point to stop the scroll
- Problem (5-20s): What people believe vs real data
- Data reveal (20-45s): The actual numbers and what they mean
- Takeaway (45-55s): One clear conclusion
- CTA (55-60s): Subscribe to "Ev-CAR-ix" for real EV data, no hype

IMPORTANT INSTRUCTIONS:
1. Channel Name: ALWAYS use "Ev-CAR-ix" (spell it exactly like this for pronunciation). NEVER use placeholders like FCR9 or generic names.
2. Numbers & Units: ALWAYS put a space between numbers and units (e.g., "71 kWh" NOT "71kWh", "190 miles" NOT "190m").
3. Brand Models: ALWAYS put a space between brand and model (e.g., "BYD M6" NOT "BYDM6").
4. Tone: Data-driven, punchy, no hype. American English only.
5. First sentence MUST have a specific % or $ or kWh or miles number.
6. NO generic adjectives: amazing, incredible, insane, unbelievable.
7. Regions: USA, Europe, China ONLY — NEVER Turkey.

Return:
SES: [male or female]
SENARYO: [script]
"""
        else:
            # Long-form script with explicit word count and structure
            target_duration = 210  # 3.5 minutes (range: 3-4 min = 180-240s)
            min_words = int(target_duration * 2.0)  # 420 words minimum
            max_words = int(target_duration * 2.8)  # 588 words maximum
            
            system = (
                "You are Evcarix's senior analyst. Write data-rich EV scripts. "
                "American English only. Return: SES: [male/female]\nSENARYO: [script]"
            )
            user = f"""
Write a full YouTube video narration script for the "Ev-CAR-ix" channel.
Topic: {topic}
Duration: {target_duration} seconds ({target_duration // 60} minutes)
Word count: {min_words} to {max_words} words

IMPORTANT INSTRUCTIONS:
1. Channel Name: ALWAYS use "Ev-CAR-ix" (spell it exactly like this for pronunciation). NEVER use placeholders like FCR9.
2. Numbers & Units: ALWAYS put a space between numbers and units (e.g., "45 kWh").
3. Brand Models: ALWAYS put a space between brand and model (e.g., "Tesla Model 3").
4. Structure: Write the COMPLETE script (INTRO, SECTION 1, 2, 3, DATA REVEAL, CONCLUSION, CTA).
5. No Headings: Return ONLY the spoken text, no section headers.

Return:
SES: [male or female]
SENARYO: [script]
"""

        raw = self._call_llm(system, user, max_tokens=2000)
        if raw:
            parsed = self._parse_response(raw)
            # Word count validation for both short and long-form
            actual_words = len(parsed["script"].split())
            if format_type == "short":
                if actual_words < MIN_WORDS_SHORT:
                    print(f"[Writer] ⚠️ Shorts script too short ({actual_words} words, need {MIN_WORDS_SHORT}). Retrying...")
                    # Retry with explicit word count reminder
                    user += f"\n\nCRITICAL: Write EXACTLY {MIN_WORDS_SHORT}-{MAX_WORDS_SHORT} words. Your previous response had only {actual_words} words which is too short and will cause the audio to loop and repeat. Write a complete, flowing narration that fills the full duration."
                    raw = self._call_llm(system, user, max_tokens=2000)
                    if raw:
                        parsed = self._parse_response(raw)
            else:
                if actual_words < min_words:
                    print(f"[Writer] ⚠️ Script too short ({actual_words} words, need {min_words}). Retrying...")
                    # Retry with explicit word count reminder
                    user += f"\n\nIMPORTANT: Your previous response was too short. Write at least {min_words} words."
                    raw = self._call_llm(system, user, max_tokens=2000)
                    if raw:
                        parsed = self._parse_response(raw)
            return parsed

        return {
            "voice": "female",
            "script": (
                f"Did you know most EVs lose between 20 and 30 percent of their range in cold weather? "
                f"Today we break down the real numbers on {topic}. "
                f"Our data from 500 real-world tests shows the performance gap is far wider than manufacturers admit. "
                f"Subscribe to Evcarix for real EV data."
            )
        }

    def _parse_response(self, text):
        voice = "female"
        script = text
        if "SES:" in text:
            voice_part = text.split("SES:")[1].split("\n")[0].strip().lower()
            voice = "male" if "male" in voice_part else "female"
            if "SENARYO:" in text:
                script = text.split("SENARYO:")[1].strip()
        return {"voice": voice, "script": script}

    # ── Açıklama ───────────────────────────────────────────────────
    def generate_description(self, topic, title, tags_list, cta_override=None, category=None, format_type="short"):
        cta = cta_override or "Subscribe to Evcarix — No hype. Just numbers. ⚡"

        channel_about = (
            "\n\n🔋 About Evcarix:\n"
            "Data-driven EV channel. Real-world range tests | Battery degradation | "
            "LFP vs NMC | Fast charging impact | EV cost breakdowns.\n"
            "If you want real EV numbers — welcome to Evcarix. ⚡"
        )

        # YouTube shows max 3 hashtags ABOVE the video title — choose wisely
        top_hashtags = "#EV #ElectricCar #Evcarix"
        if format_type == "short":
            top_hashtags = "#Shorts #EV #Evcarix"

        if format_type == "long":
            system = (
                "You are a YouTube SEO expert for long-form EV videos. "
                "Descriptions must start with the primary keyword in sentence 1 (YouTube indexes this). "
                "Generate 12-15 realistic chapter timestamps for a 12-15 min deep-dive. "
                "American English only. Return only the description body text."
            )
            user = (
                f"Write a YouTube long-form video description for Evcarix.\n"
                f"Title: '{title}'\nTopic: {topic}\nCategory: {category or 'general'}\n\n"
                f"STRUCTURE (follow exactly):\n\n"
                f"[OPENING — 2-3 sentences]: Primary keyword in first sentence + specific number. "
                f"What this video proves/reveals. Must be compelling enough to rank in search.\n\n"
                f"📊 What this video covers:\n"
                f"— [6 specific data-driven bullets with real numbers and units]\n\n"
                f"⏱ CHAPTERS:\n"
                f"0:00 Introduction\n"
                f"[Generate 11-13 more chapters with realistic timestamps for the topic — "
                f"use times like 1:24, 3:15, 5:40, 7:55, 9:30, 11:10, 12:45, 14:00, 15:20]\n\n"
                f"🔔 {cta}\n"
                f"📚 EV Data Playlists: Weekly Deep Dives | Battery Science | Range Tests\n\n"
                f"[CLOSING — 60 words]: Keyword-rich paragraph. Mention topic, USA/Europe/China, "
                f"Evcarix channel value. Include 4-5 searchable long-tail phrases naturally.\n\n"
                f"RULES: Primary keyword 4-6x | Real numbers throughout | "
                f"USA/Europe/China ONLY | Max 600 words total."
            )
            max_tok = 900
        else:
            system = (
                "You are a YouTube Shorts SEO expert. "
                "First 125 characters of description show in mobile search results — make them count. "
                "American English only. Return only the description body text."
            )
            user = (
                f"Write a YouTube Shorts description for Evcarix.\n"
                f"Title: '{title}'\nTopic: {topic}\nCategory: {category or 'general'}\n\n"
                f"STRUCTURE (follow exactly):\n\n"
                f"[LINE 1-2 — CRITICAL]: Primary keyword + specific number. "
                f"This appears in search results — must hook AND contain keyword.\n\n"
                f"⚡ What the data shows:\n"
                f"— [4 data bullets, max 12 words each, must include number/unit]\n\n"
                f"⏱ Timestamps:\n"
                f"0:00 The stat that changes everything\n"
                f"0:10 Real-world test data\n"
                f"0:32 What this means for EV buyers\n"
                f"0:52 Key takeaway\n\n"
                f"🔔 {cta}\n\n"
                f"RULES: Max 220 words | Primary keyword in first 10 words | "
                f"5-6 long-tail keywords embedded | USA/Europe/China ONLY."
            )
            max_tok = 400

        seo_body = self._call_llm(system, user, max_tokens=max_tok)

        if not seo_body:
            if format_type == "long":
                seo_body = (
                    f"{topic} — real-world data with no manufacturer spin. "
                    f"This video breaks down the actual numbers from USA, Europe, and China.\n\n"
                    f"📊 What this video covers:\n"
                    f"— Real performance data vs official claims\n"
                    f"— Battery efficiency and degradation percentages\n"
                    f"— True 5-year ownership cost in dollars\n"
                    f"— Side-by-side comparison with verified numbers\n\n"
                    f"⏱ CHAPTERS:\n"
                    f"0:00 Introduction\n1:30 The Data\n5:00 Analysis\n10:00 Conclusion\n\n"
                    f"🔔 {cta}"
                )
            else:
                seo_body = (
                    f"{topic} — real data, no hype. Here's what the numbers actually show.\n\n"
                    f"⚡ What the data shows:\n"
                    f"— Real-world performance vs manufacturer claims\n"
                    f"— Actual efficiency and cost numbers\n"
                    f"— Data from USA, Europe, and China\n"
                    f"— What this means for EV buyers\n\n"
                    f"⏱ Timestamps:\n"
                    f"0:00 The stat\n0:10 Data\n0:32 Analysis\n0:52 Takeaway\n\n"
                    f"🔔 {cta}"
                )

        return f"{seo_body}{channel_about}\n\n{top_hashtags}"

    # ── Etiketler ──────────────────────────────────────────────────
    def generate_tags(self, topic, title, category=None, format_type="short"):
        # Exact-match seed tags per category (what people actually search)
        cat_seed = {
            "battery_science": ["LFP battery", "NMC battery", "EV battery degradation",
                                 "solid state battery", "battery cycle life", "LFP vs NMC",
                                 "EV battery chemistry", "lithium battery lifespan"],
            "range_tests":     ["EV range test", "real world EV range", "EPA vs real range",
                                 "EV winter range loss", "electric car range 2025",
                                 "EV highway range test", "EV range cold weather"],
            "charging":        ["EV charging speed", "DC fast charging", "800V charging",
                                 "EV charging cost", "home charging vs fast charging",
                                 "EV charging network", "how fast does EV charge"],
            "comparisons":     ["EV comparison 2025", "electric car comparison",
                                 "best electric car 2025", "Tesla vs BYD comparison",
                                 "EV head to head test", "electric car ranking 2025"],
            "cost_ownership":  ["EV total cost of ownership", "electric car vs gas cost",
                                 "EV depreciation", "EV insurance cost",
                                 "EV maintenance cost", "is EV cheaper than gas"],
            "market_data":     ["EV market share 2025", "electric car sales data",
                                 "BYD vs Tesla sales", "EV adoption rate",
                                 "global EV market", "best selling electric car 2025"],
            "education":       ["how EV battery works", "EV heat pump explained",
                                 "regenerative braking explained", "EV efficiency explained",
                                 "electric motor explained", "EV thermal management"],
            "infrastructure":  ["EV charging network", "EV charging infrastructure",
                                 "home EV charger", "public charging cost",
                                 "EV grid impact", "smart charging EV"],
        }
        keywords = self._extract_seo_keywords(topic)
        brand_tags = keywords["primary"] + keywords["secondary"]
        format_tags = ["Shorts", "EVShorts"] if format_type == "short" else ["EV deep dive", "electric car guide", "EV data analysis"]

        # Kategoriye göre seed tag'leri seç veya varsayılanı kullan
        seed = cat_seed.get(category, cat_seed["range_tests"])

        system = (
            "You are a YouTube SEO specialist. Tags help YouTube understand your video topic for "
            "search indexing and topic clustering (Suggested Videos). "
            "Return ONLY a comma-separated list. No hashtags. No numbering. American English."
        )
        user = (
            f"Generate optimized YouTube tags for Evcarix video.\n"
            f"Title: '{title}'\nTopic: {topic}\nCategory: {category or 'general'}\n"
            f"Format: {'Long-form video' if format_type == 'long' else 'YouTube Shorts'}\n\n"
            f"TAG STRATEGY (YouTube uses tags for search + topic clustering):\n"
            f"BROAD (3): ev, electric car, electric vehicle\n"
            f"EXACT-MATCH (5): exact phrases people search for this topic\n"
            f"BRAND/MODEL (4): specific car brands or battery tech in topic\n"
            f"LONG-TAIL (6): 3-5 word phrases — e.g. 'tesla model y real range 2025'\n"
            f"YEAR (2): include '2025' or '2026' in some tags\n"
            f"CHANNEL (2): evcarix, EV data channel\n\n"
            f"Pre-selected seeds (include these): {', '.join(seed[:4])}\n"
            f"Brand tags detected: {', '.join(brand_tags) if brand_tags else 'none'}\n"
            f"Always include: ev, electric car, {', '.join(CHANNEL_CORE_TAGS[:3])}\n\n"
            f"CONSTRAINTS:\n"
            f"- Total joined length: under 490 characters\n"
            f"- Each tag: 2-30 chars, no # symbols\n"
            f"- USA/Europe/China brands ONLY — NEVER Turkey\n"
            f"- Include numeric tags where relevant: 100k miles, 800V, 10-80 percent\n"
            f"Return: tag1, tag2, tag3, ..."
        )

        raw = self._call_llm(system, user, max_tokens=350)
        if raw:
            raw = raw.replace("\n", "").replace("Tags:", "").replace("```", "").strip()
            if raw.startswith("[") and raw.endswith("]"):
                raw = raw[1:-1]
            tag_list = [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]

            valid = []
            for tag in tag_list:
                tag = tag.replace("#", "").strip()
                tag = ''.join(c for c in tag if c.isalnum() or c in (' ', '-')).strip()
                if 2 <= len(tag) <= 30:
                    valid.append(tag)

            # Önce brand + format tags ekle
            priority = brand_tags + format_tags
            for pt in priority:
                clean = ''.join(c for c in pt if c.isalnum() or c in (' ', '-')).strip()
                if 2 <= len(clean) <= 30 and clean not in valid:
                    valid.insert(0, clean)

            # Core tag'leri öne ekle
            for core in CHANNEL_CORE_TAGS[:3]:
                if core not in valid:
                    valid.insert(0, core)

            final, char_count = [], 0
            for tag in valid:
                addition = len(tag) + (1 if final else 0)
                if char_count + addition <= 490:
                    final.append(tag)
                    char_count += addition
                else:
                    break
            if final:
                return final

        return CHANNEL_CORE_TAGS + seed[:4] + brand_tags[:3] + [
            "EV range test 2025", "battery degradation", "EV charging speed"
        ]


if __name__ == "__main__":
    w = CreativeWriter()
    titles = w.generate_title("LFP vs NMC battery after 100k miles", category="battery_science", format_type="short")
    print("Titles (Short):", titles[:2])
    titles_long = w.generate_title("LFP vs NMC battery after 100k miles", category="battery_science", format_type="long")
    print("Titles (Long):", titles_long[:2])
    script = w.generate_script("LFP vs NMC battery", category="battery_science")
    print("Script:", script['script'][:100])
