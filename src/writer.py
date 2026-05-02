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

    # ── Başlık ─────────────────────────────────────────────────────
    def generate_title(self, topic, history_titles=None, category=None):
        history_block = ""
        if history_titles:
            recent = history_titles[-20:]
            history_block = (
                "\nCRITICAL — NEVER repeat these used titles (no similar patterns or hooks):\n"
                + "\n".join(f"- {t}" for t in recent) + "\n"
            )

        template_hint = ""
        if category and category in VIRAL_TITLE_TEMPLATES:
            samples = random.sample(VIRAL_TITLE_TEMPLATES[category],
                                    min(2, len(VIRAL_TITLE_TEMPLATES[category])))
            template_hint = "\nViral patterns for this category:\n" + "\n".join(f"- {s}" for s in samples)

        system = (
            "You are YouTube's #1 Shorts growth strategist for EV content. "
            "Titles get 15-25% CTR. American English only. "
            "Return ONLY a valid JSON array of exactly 5 strings. No extra text."
        )
        user = (
            f"Write 5 viral YouTube Shorts titles for Evcarix (EV data channel).\n"
            f"Topic: {topic}\nCategory: {category or 'general'}\n\n"
            f"REQUIREMENTS:\n"
            f"1. 50-65 characters each\n"
            f"2. MUST contain specific number: %, $, kWh, miles, km, kW, or minutes\n"
            f"3. Power words: exposed, hidden, real, truth, cost, drain, fail, freeze, beats\n"
            f"4. Hook types: myth-busting, shocking data, hidden truth, unexpected comparison\n"
            f"5. NO generic: 'Real Data', 'You Won't Believe', 'Amazing', 'Incredible'\n"
            f"6. USA/Europe/China examples ONLY — NEVER Turkey\n"
            f"{template_hint}\n"
            f"{history_block}\n"
            f'Return: ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"]'
        )

        raw = self._call_llm(system, user, max_tokens=400)
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
        templates = VIRAL_TITLE_TEMPLATES.get(category, [
            f"Real {topic[:30]} Data: {random.randint(10,40)}% Gap Exposed",
            f"Why {topic[:25]} Costs ${random.randint(200,800)} More",
            f"{topic[:30]}: {random.randint(15,45)}% Worse Than Claimed",
            f"The Hidden Truth About {topic[:25]}",
            f"{topic[:30]} After {random.randint(50,200)}k Miles: Brutal Truth",
        ])
        return [t[:65] for t in templates[:5]]

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
Write a 60-second YouTube Shorts narration script for Evcarix channel.
Topic: {topic}
Category: {category or 'general'}
Category guide: {cat_extra}
REQUIRED word count: {MIN_WORDS_SHORT} to {MAX_WORDS_SHORT} words (this is mandatory — do not write fewer)

Structure (write ALL sections as continuous spoken text):
- Hook (0-5s): One shocking data point to stop the scroll
- Problem (5-20s): What people believe vs real data
- Data reveal (20-45s): The actual numbers and what they mean
- Takeaway (45-55s): One clear conclusion
- CTA (55-60s): Subscribe to Ev-Car-ix for real EV data, no hype

Tone: Data-driven, punchy, no hype.
Language: English.
Channel name: always write "Ev-Car-ix" (not Evcarix).
First sentence MUST have a specific % or $ or kWh or miles number
Real brands: Tesla, BYD, Hyundai, Kia, BMW, Mercedes, VW, Rivian, Lucid
Regions: USA, Europe, China ONLY — NEVER Turkey
No hype: amazing, incredible, insane, unbelievable

Return ONLY the spoken words. No section labels. No formatting.
Write between {MIN_WORDS_SHORT} and {MAX_WORDS_SHORT} words total — count carefully.

Return:
SES: [male or female]
SENARYO: [script]
"""
        else:
            # Long-form script with explicit word count and structure
            target_duration = 360  # 6 minutes for long-form
            min_words = int(target_duration * 2.0)  # 720 words minimum
            max_words = int(target_duration * 2.8)  # 1008 words maximum
            
            system = (
                "You are Evcarix's senior analyst. Write data-rich EV scripts. "
                "American English only. Return: SES: [male/female]\nSENARYO: [script]"
            )
            user = f"""
Write a full YouTube video narration script for Evcarix channel.
Topic: {topic}
Duration: {target_duration} seconds ({target_duration // 60} minutes)
Word count: {min_words} to {max_words} words
(at ~130 words/minute speaking pace this fills {target_duration}s exactly)

CRITICAL: Write the COMPLETE script from start to finish.
Do NOT write a summary. Do NOT write section headings only.
Write every single sentence that will be spoken.

Structure (write all sections in full):
[INTRO - 30s]: Hook question + what we will cover today
[SECTION 1 - 60s]: Background and common misconceptions
[SECTION 2 - 60s]: Real-world data and test results
[SECTION 3 - 60s]: Comparison with alternatives
[DATA REVEAL - 60s]: The key numbers and what they mean
[CONCLUSION - 30s]: Main takeaway
[CTA - 20s]: Subscribe to Evcarix for real EV data, no hype

Channel name pronunciation note: spell it as "Ev-CAR-ix" in the script.
Tone: Data-driven, no hype, factual, slightly dramatic on data reveals.
Language: English.
Category: {category or 'general'}
Category guide: {cat_extra}
Regions: USA, Europe, China ONLY — NEVER Turkey

Return ONLY the spoken script text, no section headers, no stage
directions, no formatting — just the words to be spoken continuously.

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
    def generate_description(self, topic, title, tags_list, cta_override=None, category=None):
        cta = cta_override or "Subscribe to Evcarix for real EV data every day."

        hashtag_str = " ".join(TOP_SHORTS_HASHTAGS[:8])
        topic_hashtags = " ".join(
            [f"#{w.capitalize()}" for w in topic.split() if len(w) > 3][:5]
        )
        tag_hashtags = " ".join(
            [f"#{t.replace(' ', '').replace('-', '')}" for t in tags_list[:8]]
        )

        channel_about = (
            "\n🔋 About Evcarix:\n"
            "Data-driven EV channel. No hype. Just numbers. ⚡\n"
            "Real-world range tests | Battery degradation | LFP vs NMC | "
            "Fast charging impact | EV efficiency breakdowns.\n"
            "If you care about real EV data — welcome to Evcarix."
        )

        system = (
            "You are a YouTube SEO expert for viral Shorts. "
            "American English only. Write descriptions that rank on YouTube search AND suggested feed."
        )
        user = (
            f"Write a YouTube Shorts description for Evcarix.\n"
            f"Title: '{title}'\nTopic: {topic}\nCategory: {category or 'general'}\n\n"
            f"STRUCTURE:\n"
            f"Line 1-2: HOOK — strong statement with specific number (shows in search preview)\n\n"
            f"What you'll learn:\n"
            f"— [4 data-driven bullets, each with a real number]\n\n"
            f"[2-sentence 'Why Evcarix' paragraph]\n\n"
            f"CTA: {cta}\n\n"
            f"Timestamps:\n0:00 Hook\n0:10 Key Data\n0:25 Takeaway\n\n"
            f"RULES:\n"
            f"- Max 350 words\n"
            f"- 5-7 long-tail keywords naturally embedded\n"
            f"- USA/Europe/China ONLY — NEVER Turkey\n"
            f"- Real numbers: %, $, kWh, miles, kW, minutes\n"
            f"Return only description text."
        )

        seo_body = self._call_llm(system, user, max_tokens=500)

        if not seo_body:
            seo_body = (
                f"{title}\n\n"
                f"Real data on {topic} — no marketing spin, no hype. Just numbers.\n\n"
                f"What you'll learn:\n"
                f"— Real-world performance vs manufacturer claims\n"
                f"— Battery efficiency and degradation data with real percentages\n"
                f"— True ownership cost breakdown in dollars\n"
                f"— Head-to-head comparison with real-world numbers\n\n"
                f"{cta}\n\n"
                f"Timestamps:\n0:00 Hook\n0:10 Key Data\n0:25 Takeaway"
            )

        return (
            f"{seo_body}\n\n"
            f"{hashtag_str}\n"
            f"{topic_hashtags}\n"
            f"{tag_hashtags}\n"
            f"{channel_about}"
        )

    # ── Etiketler ──────────────────────────────────────────────────
    def generate_tags(self, topic, title, category=None):
        cat_seed = {
            "battery_science": ["LFP battery", "NMC battery", "EV battery degradation",
                                 "solid state battery", "battery cycle life", "battery chemistry"],
            "range_tests":     ["EV range test", "real world EV range", "EPA vs real range",
                                 "EV winter range", "electric car range 2025"],
            "charging":        ["EV charging speed", "DC fast charging", "800V charging",
                                 "EV charging cost", "home charging vs fast charging"],
            "comparisons":     ["EV comparison 2025", "electric car comparison",
                                 "EV head to head", "best electric car 2025"],
            "cost_ownership":  ["EV total cost", "electric car ownership cost",
                                 "EV vs gas cost", "EV depreciation", "EV insurance"],
            "market_data":     ["EV market share", "electric car sales 2025",
                                 "EV adoption rate", "global EV sales", "BYD vs Tesla"],
            "education":       ["how EV works", "EV explained", "heat pump EV",
                                 "EV efficiency explained", "electric motor explained"],
            "infrastructure":  ["EV charging network", "charging infrastructure",
                                 "EV grid impact", "smart charging"],
        }
        seed = cat_seed.get(category, ["EV data", "electric vehicle test", "battery technology"])

        system = (
            "You are a YouTube SEO specialist. "
            "Return ONLY a comma-separated tag list. No hashtags. No numbering. American English."
        )
        user = (
            f"Generate YouTube tags.\nTitle: '{title}'\nTopic: {topic}\nCategory: {category or 'general'}\n\n"
            f"Strategy:\n"
            f"BROAD (3): ev, electric car, electric vehicle\n"
            f"MEDIUM (8): specific to topic — models, technologies, brands\n"
            f"LONG-TAIL (7): 3-5 word phrases people search (e.g., 'tesla model 3 real range test 2025')\n"
            f"TRENDING (4): current EV news terms (ev news 2025, EV market 2025)\n"
            f"CHANNEL (2): evcarix, no hype just numbers\n\n"
            f"Seed tags: {', '.join(seed)}\n"
            f"Always include: {', '.join(CHANNEL_CORE_TAGS[:4])}\n\n"
            f"CONSTRAINTS:\n"
            f"- Total under 490 characters when joined with commas\n"
            f"- Each tag: 2-30 chars, no hashtags\n"
            f"- USA/Europe/China brands ONLY — NEVER Turkey\n"
            f"- Include data tags with numbers (100k miles, 800V, 10-80%)\n\n"
            f"Return: tag1, tag2, tag3, ..."
        )

        raw = self._call_llm(system, user, max_tokens=300)
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

        return CHANNEL_CORE_TAGS + [
            "EV range test", "battery degradation", "charging speed",
            "electric car review 2025", "EV data analysis"
        ]


if __name__ == "__main__":
    w = CreativeWriter()
    titles = w.generate_title("LFP vs NMC battery after 100k miles", category="battery_science")
    print("Titles:", titles[:2])
    script = w.generate_script("LFP vs NMC battery", category="battery_science")
    print("Script:", script['script'][:100])
