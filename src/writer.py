import os
import json

try:
    from google import genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()


class CreativeWriter:
    def __init__(self):
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
                self.gemini_client = None

        self.groq_api_keys = []
        for i in range(1, 4):
            key = os.getenv(f"GROQ_API_KEY_{i}") if i > 1 else os.getenv("GROQ_API_KEY")
            if key:
                self.groq_api_keys.append(key)
        self.groq_client = None
        if self.groq_api_keys:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_keys[0])
            except ImportError:
                print("Groq kütüphanesi yüklü değil.")

    # ─────────────────────────────────────────────────────────────────
    # BAŞLIK — Viral CTR Optimizasyonu
    # ─────────────────────────────────────────────────────────────────
    def generate_title(self, topic, history_titles=None):
        """YouTube viral CTR optimizasyonlu başlık üretir (5 adet).
        history_titles: Önceki videolarda kullanılan başlıklar — tekrarı önlemek için.
        """
        history_block = ""
        if history_titles:
            recent = history_titles[-20:]  # Son 20 başlık yeterli
            history_block = (
                "\nCRITICAL: These titles were recently used on the channel. "
                "NEVER repeat these patterns, numbers, phrases, or formats. "
                "Create COMPLETELY DIFFERENT hooks, angles, and vocabulary:\n"
                + "\n".join(f"- {t}" for t in recent)
                + "\n"
            )

        prompt = (
            f"You are the #1 YouTube Shorts growth strategist for electric vehicle channels. "
            f"Your titles get 15%+ CTR. Write 5 viral, click-magnet titles for Evcarix.\n"
            f"Rules:\n"
            f"1. Each title MUST be under 70 characters\n"
            f"2. Use SPECIFIC numbers or shocking data points (NOT generic 'real data')\n"
            f"3. Hook types: myth-busting, hidden truth, unexpected comparison, shocking data reveal, common mistake\n"
            f"4. Power words: Exposed, Hidden, Cost, Savings, Failure, Why, Lie, Truth, Freeze, Burn, Drain, Broken\n"
            f"5. AVOID overused patterns like 'Real Data', 'Tested', 'vs' if they appear in history\n"
            f"6. English ONLY. American English ONLY. No hype words like 'amazing', 'incredible', 'insane'\n"
            f"7. CRITICAL: NEVER mention Turkey or Turkish-specific examples. Use USA, Europe, China examples only.\n"
            f"8. Return ONLY a JSON array of exactly 5 strings. No numbering\n"
            f"{history_block}\n"
            f"Topic: {topic}\n"
            f"Example format: [\"Title 1\", \"Title 2\", \"Title 3\", \"Title 4\", \"Title 5\"]"
        )

        if GEMINI_AVAILABLE and self.gemini_client:
            try:
                resp = self.gemini_client.models.generate_content(
                    model='gemini-2.0-flash', contents=prompt
                )
                text = resp.text.strip().replace("```json", "").replace("```", "").strip()
                titles = json.loads(text)
                if isinstance(titles, list) and titles:
                    return titles
            except Exception as e:
                print(f"[Writer] generate_title hatası (Gemini): {e}")

        def _is_duplicate(title, history_set):
            t = title.lower().strip()
            for h in history_set:
                # %30'dan fazla ortak kelime varsa duplicate
                t_words = set(t.split())
                h_words = set(h.lower().split())
                if len(t_words) > 0 and len(t_words & h_words) / len(t_words) > 0.3:
                    return True
            return False

        if self.groq_api_keys:
            try:
                from groq import Groq
                for key_idx, api_key in enumerate(self.groq_api_keys):
                    try:
                        client = Groq(api_key=api_key)
                        completion = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[
                                {"role": "system", "content": "You are a YouTube growth expert. Return only valid JSON arrays of title strings. American English only. Use numbers, data, and power words."},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.65, max_tokens=400,
                        )
                        text = completion.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
                        titles = json.loads(text)
                        if isinstance(titles, list) and titles:
                            history_set = set(h.lower() for h in (history_titles or []))
                            fresh = [t for t in titles if not _is_duplicate(t, history_set)]
                            if fresh:
                                return fresh[:5]
                            else:
                                print("[Writer] Tüm Groq title'ları history'de var, fallback kullanılıyor.")
                        break
                    except Exception as e:
                        error_str = str(e)
                        if "rate_limit" in error_str.lower() or "429" in error_str or "quota" in error_str.lower():
                            print(f"[Writer] Groq key {key_idx + 1}/{len(self.groq_api_keys)} quota exhausted (title), trying next...")
                            if key_idx < len(self.groq_api_keys) - 1:
                                continue
                            else:
                                print(f"[Writer] All Groq keys exhausted for title")
                                break
                        else:
                            raise
            except ImportError:
                print("Groq kütüphanesi yüklü değil.")
            except Exception as e:
                print(f"[Writer] generate_title hatası (Groq): {e}")

        # Fallback — data-driven format, topic'e göre dinamik, history'den kaçınan
        import random as _rand
        history_set = set(h.lower() for h in (history_titles or []))
        fallback_pool = [
            f"Hidden Truth About {topic}",
            f"{topic} Exposed: Real Data",
            f"Why {topic} Actually Matters",
            f"The Real Cost of {topic}",
            f"{topic}: Engineers Hate This Fact",
            f"Can {topic} Survive 200k Miles?",
            f"{topic} vs Reality (Tested)",
            f"Why {topic} Drains Range in Winter",
            f"The Dirty Secret Behind {topic}",
            f"{topic}: What Dealers Won't Say",
            f"Is {topic} Worth It? Real Math",
            f"{topic} After 5 Years: Brutal Truth",
        ]
        # Topic uzunsa kısalt
        short_topic = topic.split(":")[0].split("?")[0].strip()
        if len(short_topic) < len(topic):
            fallback_pool += [
                f"{short_topic}: Engineers Exposed",
                f"{short_topic} Winter Test Results",
                f"{short_topic} True Cost Revealed",
            ]
        # History'de olmayanları seç, yoksa rastgele 5
        fresh_fallback = [t for t in fallback_pool if not _is_duplicate(t, history_set)]
        pool = fresh_fallback if fresh_fallback else fallback_pool
        _rand.shuffle(pool)
        return pool[:5]

    # ─────────────────────────────────────────────────────────────────
    # SENARYO
    # ─────────────────────────────────────────────────────────────────
    def generate_script(self, topic, format_type="short", category=None):
        """Video senaryosu ve ses tercihi oluşturur. category: topic kategorisi."""
        prompt = self._get_prompt(topic, format_type, category)

        if self.groq_client:
            try:
                print("Groq (Llama 3) kullanılıyor...")
                return self._generate_with_groq(prompt)
            except Exception as e:
                print(f"Groq hatası: {e}")

        if GEMINI_AVAILABLE and self.gemini_client:
            print("Gemini kullanılıyor...")
            return self._generate_with_gemini(prompt)

        raise Exception("Hiçbir LLM API anahtarı bulunamadı!")

    def _get_prompt(self, topic, format_type, category=None):
        evcarix_mission = (
            "Evcarix is a data-driven electric vehicle channel focused on real-world EV performance and battery science. "
            "We test electric cars beyond marketing claims — measuring true driving range, battery efficiency, winter range loss, "
            "cold weather performance, charging speed, charging costs, and long-term EV ownership experience. "
            "Mission: No hype. Just numbers."
        )
        # Kategoriye göre özel talimatlar
        category_instructions = {
            "interactive_tools": (
                "This is an INTERACTIVE TOOL / CALCULATOR video. Structure the script as step-by-step calculations. "
                "Walk the viewer through each input, formula, and result. Use phrases like 'Enter this number', 'Multiply by', 'The result is'. "
                "Focus on practical utility — viewers should feel they just used a calculator."
            ),
            "cost_ownership": (
                "This is a COST & OWNERSHIP analysis video. Structure as a financial breakdown. "
                "Present real dollar or euro amounts. Compare 5-year total cost, maintenance, insurance, depreciation. "
                "Use phrases like 'Total cost of ownership', 'Annual savings', 'Break-even point'."
            ),
            "market_data": (
                "This is a MARKET & INDUSTRY DATA video. Present large-scale statistics and trends. "
                "Reference specific countries: USA, Europe, China. Use market share percentages, sales volumes, growth rates. "
                "Use phrases like 'Market share grew by X%', 'In 2025, China sold X million EVs'."
            ),
            "comparisons": (
                "This is a HEAD-TO-HEAD COMPARISON video. Structure as direct A vs B analysis. "
                "Present side-by-side specs: range, price, efficiency, charging speed, weight, motor power. "
                "Use phrases like 'Car A wins on range', 'But Car B charges faster', 'The winner depends on'."
            ),
            "education": (
                "This is a TECHNICAL EXPLAINER video. Explain HOW something works using simple analogies and visuals. "
                "Break down complex concepts into digestible steps. Use phrases like 'Imagine a pipe', 'Think of it like', 'Here's why'."
            ),
            "battery_science": (
                "This is BATTERY SCIENCE deep-dive. Reference specific chemistries: LFP, NMC, NCA, solid-state. "
                "Use degradation percentages, cycle counts, temperature effects, real lab test data. "
                "Use phrases like 'After 1000 cycles, capacity dropped to X%', 'LFP lasts longer but charges slower'."
            ),
            "range_tests": (
                "This is a REAL-WORLD RANGE TEST video. Reference specific speeds, temperatures, and road conditions. "
                "Compare advertised EPA/WLTP range vs actual measured range. Use kWh/100km or miles/kWh. "
                "Use phrases like 'We drove 300 miles at 70mph', 'Real range was 18% less than EPA'."
            ),
            "charging": (
                "This is a CHARGING TECHNOLOGY video. Reference kW speeds, charge curves, minutes to 80%. "
                "Compare 400V vs 800V, home vs DC fast charging, connector types. "
                "Use phrases like '10 to 80 percent in 18 minutes', 'Peak power lasted 5 minutes before tapering'."
            ),
            "infrastructure": (
                "This is an INFRASTRUCTURE & GRID video. Reference charger counts, reliability percentages, coverage maps. "
                "Discuss grid capacity, smart charging, apartment charging challenges. "
                "Use phrases like 'The network has 95% uptime', 'Apartment dwellers face a 3-year payback'."
            ),
        }
        cat_extra = category_instructions.get(category, "Focus on real data, numbers, and measurable facts. No marketing hype.")

        if format_type == "short":
            return f"""
Topic: {topic}
Category: {category or "general"}
Channel Concept: {evcarix_mission}
Format: YouTube Short (25-40 seconds)
Language: American English ONLY.

Category-specific instructions: {cat_extra}

Requirements:
1. Script length: 25-40 seconds (approximately 60-100 words for normal speaking speed).
2. Start with a data-driven hook that includes a specific number or shocking fact.
3. Focus on facts, numbers, and technical insights. No generic "amazing" or "incredible" hype.
4. Voiceover text only — no stage directions.
5. End with: "Subscribe to Evcarix for real EV data."
6. Please respond ONLY in American English.
7. CRITICAL: Use regions like USA, Europe, China ONLY. NEVER use Turkey or Turkish-specific examples.
8. Include real-world data points from Google research: battery percentages, range numbers, cost figures, kW charging speeds, market share stats.
9. Reference specific car brands and models from global markets (Tesla, BYD, BMW, Mercedes, VW, Ford, Hyundai, Kia, etc.).

Return in this format:
SES: [male/female]
SENARYO: [script text]
"""
        else:
            return f"""
Topic: {topic}
Category: {category or "general"}
Channel Concept: {evcarix_mission}
Format: Long Video (6-8 minutes)
Language: American English ONLY.

Category-specific instructions: {cat_extra}

Requirements:
1. Deep dive into technical details with specific numbers, percentages, and real-world data.
2. Maintain a professional, educational, and analytical tone.
3. Please respond ONLY in American English.
4. CRITICAL: Use regions like USA, Europe, China ONLY. NEVER use Turkey or Turkish-specific examples.
5. Include real-world data points from Google research: battery percentages, range numbers, cost figures, kW charging speeds, market share stats.
6. Reference specific car brands and models from global markets (Tesla, BYD, BMW, Mercedes, VW, Ford, Hyundai, Kia, etc.).

Return in this format:
SES: [male/female]
SENARYO: [script text]
"""

    def _generate_with_groq(self, prompt):
        from groq import Groq
        for key_idx, api_key in enumerate(self.groq_api_keys):
            try:
                client = Groq(api_key=api_key)
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": "You are a specialized technical EV analyst and scriptwriter for Evcarix. You focus on data, battery science, and real-world metrics without hype."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.6,
                    max_tokens=2048,
                )
                return self._parse_response(completion.choices[0].message.content)
            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str or "quota" in error_str.lower():
                    print(f"[Writer] Groq key {key_idx + 1}/{len(self.groq_api_keys)} quota exhausted (script), trying next...")
                    if key_idx < len(self.groq_api_keys) - 1:
                        continue
                    else:
                        raise Exception(f"All Groq API keys quota exhausted")
                else:
                    raise
        raise Exception("No valid Groq API keys available")

    def _generate_with_gemini(self, prompt):
        for key_idx, api_key in enumerate(self.gemini_api_keys):
            try:
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.0-flash', contents=prompt
                )
                return self._parse_response(response.text)
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                    print(f"[Writer] Gemini key {key_idx + 1}/{len(self.gemini_api_keys)} quota exhausted, trying next...")
                    if key_idx < len(self.gemini_api_keys) - 1:
                        continue  # Try next key
                    else:
                        raise Exception(f"All Gemini API keys quota exhausted")
                else:
                    raise  # Re-raise other errors
        raise Exception("No valid Gemini API keys available")

    def _parse_response(self, text):
        voice = "female"
        script = text
        if "SES:" in text:
            voice_part = text.split("SES:")[1].split("\n")[0].strip().lower()
            voice = "female" if any(w in voice_part for w in ["female"]) else "male"
            if "SENARYO:" in text:
                script = text.split("SENARYO:")[1].strip()
        return {"voice": voice, "script": script}

    # ─────────────────────────────────────────────────────────────────
    # AÇIKLAMA — AI Destekli SEO Optimizasyonu
    # ─────────────────────────────────────────────────────────────────
    def generate_description(self, topic, title, tags_list, cta_override=None, category=None):
        """YouTube SEO için optimize edilmiş, başlıkla bire bir örtüşen açıklama üretir."""
        hashtags = " ".join([f"#{t.replace(' ', '').replace('-', '')}" for t in tags_list[:10]])
        cta = cta_override or "Subscribe to Evcarix for real EV data every day."

        channel_about = (
            "\n🔋 About Evcarix:\n"
            "Evcarix is a data-driven electric vehicle channel focused on real-world EV performance and battery science.\n"
            "We test electric cars beyond marketing claims — measuring true driving range, battery efficiency, winter range loss,\n"
            "cold weather performance, charging speed, charging costs, and long-term EV ownership experience.\n"
            "On this channel you'll find real-world EV range tests, winter vs summer EV performance comparisons,\n"
            "EV battery degradation analysis, LFP vs NMC battery comparisons, fast charging impact explained,\n"
            "EV efficiency & consumption breakdowns, and electric vehicle technology explained clearly.\n"
            "Our mission is simple: No hype. Just numbers. ⚡\n"
            "If you care about real electric vehicle data, battery performance, and honest EV analysis — welcome to Evcarix."
        )

        cat_hint = {
            "interactive_tools": "This is an interactive calculator / tool video. Emphasize practical utility, step-by-step logic, and data-driven decision making.",
            "cost_ownership": "This is a cost and ownership analysis video. Emphasize dollar/euro amounts, total cost of ownership, savings, and financial breakdown.",
            "market_data": "This is a market and industry data video. Emphasize global statistics, market share percentages, sales volumes, and regional comparisons (USA, Europe, China).",
            "comparisons": "This is a head-to-head comparison video. Emphasize side-by-side specs, direct A vs B data, and clear winner logic.",
            "education": "This is a technical explainer video. Emphasize how-it-works logic, analogies, and educational value.",
            "battery_science": "This is a battery science deep-dive. Emphasize chemistry data, degradation percentages, cycle counts, and lab results.",
            "range_tests": "This is a real-world range test video. Emphasize measured miles/km, speed conditions, weather impact, and EPA vs real data.",
            "charging": "This is a charging technology video. Emphasize kW speeds, minutes to 80%, cost per kWh, and infrastructure data.",
            "infrastructure": "This is an infrastructure & grid video. Emphasize charger counts, uptime stats, coverage maps, and smart charging.",
        }.get(category, "Focus on real data, numbers, and measurable facts.")

        prompt = (
            f"Write a highly SEO-optimized YouTube description for a Shorts video.\n"
            f"Video title: '{title}'\n"
            f"Topic: {topic}\n"
            f"Content type: {category or 'general'}\n"
            f"Content guidance: {cat_hint}\n"
            f"Channel: Evcarix — data-driven electric vehicle channel focused on real-world EV performance and battery science. "
            f"We test electric cars beyond marketing claims — measuring true driving range, battery efficiency, winter range loss, "
            f"cold weather performance, charging speed, charging costs, and long-term EV ownership experience. "
            f"On this channel you'll find real-world EV range tests, winter vs summer EV performance comparisons, "
            f"EV battery degradation analysis, LFP vs NMC battery comparisons, fast charging impact explained, "
            f"EV efficiency and consumption breakdowns, and electric vehicle technology explained clearly. "
            f"Our mission is simple: No hype. Just numbers.\n\n"
            f"Requirements:\n"
            f"1. First 2 lines must be a strong hook matching the title (shown in search preview)\n"
            f"2. Add 'What you'll learn:' bullet list with 4-5 specific data-driven points aligned to the content type\n"
            f"3. Add a short 'Why Evcarix' paragraph with channel mission\n"
            f"4. Add a CTA: '{cta}'\n"
            f"5. Include naturally embedded long-tail keyword phrases (2-3 words each) related to the topic\n"
            f"6. Add 'Timestamps:' section with 3 estimated timestamps for key moments\n"
            f"7. Max 400 words. American English only.\n"
            f"8. CRITICAL: Use global examples ONLY (USA, Europe, China). NEVER mention Turkey or Turkish-specific examples.\n"
            f"9. Include real data points: battery percentages, range numbers, cost figures, kW speeds, market share stats.\n"
            f"Return only the description text, no extra formatting."
        )

        seo_body = ""
        try:
            if self.groq_api_keys:
                try:
                    from groq import Groq
                    for key_idx, api_key in enumerate(self.groq_api_keys):
                        try:
                            client = Groq(api_key=api_key)
                            completion = client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role": "user", "content": prompt}],
                                max_tokens=500
                            )
                            seo_body = completion.choices[0].message.content.strip()
                            break
                        except Exception as e:
                            error_str = str(e)
                            if "rate_limit" in error_str.lower() or "429" in error_str or "quota" in error_str.lower():
                                print(f"[Writer] Groq key {key_idx + 1}/{len(self.groq_api_keys)} quota exhausted (description), trying next...")
                                if key_idx < len(self.groq_api_keys) - 1:
                                    continue
                                else:
                                    print(f"[Writer] All Groq keys exhausted for description")
                                    break
                            else:
                                raise
                except ImportError:
                    pass
            elif GEMINI_AVAILABLE and self.gemini_api_keys:
                for key_idx, api_key in enumerate(self.gemini_api_keys):
                    try:
                        client = genai.Client(api_key=api_key)
                        resp = client.models.generate_content(
                            model='gemini-2.0-flash', contents=prompt
                        )
                        seo_body = resp.text.strip()
                        break
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                            print(f"[Writer] Gemini key {key_idx + 1}/{len(self.gemini_api_keys)} quota exhausted (description), trying next...")
                            if key_idx < len(self.gemini_api_keys) - 1:
                                continue
                            else:
                                print(f"[Writer] All Gemini keys exhausted for description")
                                break
                        else:
                            raise
        except Exception as e:
            print(f"[Writer] Description generation hatası: {e}")

        if not seo_body:
            seo_body = (
                f"{title}\n\n"
                f"We test {topic} beyond marketing claims — measuring true driving range, battery efficiency, "
                f"and real-world performance with no hype. Just numbers.\n\n"
                f"What you'll learn:\n"
                f"• Real-world range and efficiency data\n"
                f"• Battery degradation and chemistry insights\n"
                f"• True ownership cost breakdown\n"
                f"• How it compares to rivals in head-to-head tests\n\n"
                f"Timestamps:\n"
                f"0:00 Hook & Introduction\n"
                f"0:15 Key Data Points\n"
                f"0:35 Conclusion & Verdict\n\n"
                f"{cta}"
            )

        return (
            f"{seo_body}\n\n"
            f"{hashtags} #Shorts #EV #ElectricCar #Evcarix\n"
            f"{channel_about}"
        )

    # ─────────────────────────────────────────────────────────────────
    # ETİKETLER — YouTube 500 Karakter Limiti Gözetilerek
    # ─────────────────────────────────────────────────────────────────
    def generate_tags(self, topic, title, category=None):
        """YouTube SEO için optimize edilmiş etiket listesi üretir (maks. 500 karakter)."""
        cat_tags = {
            "interactive_tools": "interactive EV calculator, EV cost calculator, range calculator, EV tool, EV comparison tool, EV data tool",
            "cost_ownership": "EV total cost of ownership, EV vs gas cost, EV depreciation, EV insurance cost, EV maintenance cost, EV ownership cost 2026",
            "market_data": "EV market share 2025, EV sales data, EV industry statistics, EV adoption rate, global EV sales, EV market analysis",
            "comparisons": "EV comparison 2026, head to head EV test, EV specs compared, EV vs EV, electric car comparison",
            "education": "how EV works, EV explained, EV technology explained, electric vehicle tutorial, EV battery explained",
            "battery_science": "EV battery degradation, LFP vs NMC, EV battery chemistry, solid state battery, EV battery health, battery cycle life",
            "range_tests": "EV range test, real world EV range, EPA vs real range, EV efficiency test, EV winter range, EV highway range",
            "charging": "EV charging speed, DC fast charging, EV charging cost, EV charging curve, 800V charging, home charging vs fast charging",
            "infrastructure": "EV charging network, charging infrastructure, EV grid impact, smart charging, EV charging stations Europe",
        }.get(category, "EV data, real world EV test, electric vehicle analysis")

        prompt = (
            f"You are a YouTube SEO expert with 10 years experience ranking EV videos. "
            f"Generate the BEST possible tags for a YouTube Shorts video.\n"
            f"Video title: '{title}'\n"
            f"Topic: {topic}\n"
            f"Content category: {category or 'general'}\n"
            f"Channel niche: Electric vehicles, battery technology, EV performance data, real-world range tests\n"
            f"Category-specific tag suggestions (use some of these): {cat_tags}\n\n"
            f"Tag strategy:\n"
            f"1. 3 broad tags (ev, electric car, electric vehicle)\n"
            f"2. 6 medium-competition tags specific to the topic (model names, technologies)\n"
            f"3. 6 long-tail specific tags (e.g., 'tesla model 3 range test 2024', 'lfp battery degradation 100k miles')\n"
            f"4. 3 trending / search-volume tags (ev news 2025, electric vehicle comparison, ev battery test)\n"
            f"5. 2 niche tags for channel discovery (evcarix, no hype just numbers)\n"
            f"6. Total must be under 490 characters when joined with commas — prioritize long-tail for ranking\n"
            f"7. CRITICAL: Use global brands and regions ONLY (USA, Europe, China, Tesla, BYD, BMW, etc.). NEVER include Turkey-specific tags.\n"
            f"8. Include data-driven tags with numbers (100k miles, 800V, 10-80%, etc.)\n\n"
            f"Return ONLY a comma-separated list of tags. No hashtags. No numbering. American English only."
        )

        try:
            raw_tags = ""
            if self.groq_api_keys:
                try:
                    from groq import Groq
                    for key_idx, api_key in enumerate(self.groq_api_keys):
                        try:
                            client = Groq(api_key=api_key)
                            completion = client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[{"role": "user", "content": prompt}],
                                max_tokens=250
                            )
                            raw_tags = completion.choices[0].message.content.strip()
                            break
                        except Exception as e:
                            error_str = str(e)
                            if "rate_limit" in error_str.lower() or "429" in error_str or "quota" in error_str.lower():
                                print(f"[Writer] Groq key {key_idx + 1}/{len(self.groq_api_keys)} quota exhausted (tags), trying next...")
                                if key_idx < len(self.groq_api_keys) - 1:
                                    continue
                                else:
                                    print(f"[Writer] All Groq keys exhausted for tags")
                                    break
                            else:
                                raise
                except ImportError:
                    pass
            elif GEMINI_AVAILABLE and self.gemini_api_keys:
                for key_idx, api_key in enumerate(self.gemini_api_keys):
                    try:
                        client = genai.Client(api_key=api_key)
                        resp = client.models.generate_content(
                            model='gemini-2.0-flash', contents=prompt
                        )
                        raw_tags = resp.text.strip()
                        break
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                            print(f"[Writer] Gemini key {key_idx + 1}/{len(self.gemini_api_keys)} quota exhausted (tags), trying next...")
                            if key_idx < len(self.gemini_api_keys) - 1:
                                continue
                            else:
                                print(f"[Writer] All Gemini keys exhausted for tags")
                                break
                        else:
                            raise

            # Temizlik
            raw_tags = raw_tags.replace("\n", "").replace("Tags:", "").replace("```", "").strip()
            if raw_tags.startswith("[") and raw_tags.endswith("]"):
                raw_tags = raw_tags[1:-1]
            tag_list = [t.strip().strip('"').strip("'") for t in raw_tags.split(",") if t.strip()]

            # YouTube validasyon: hashtag'leri kaldır, geçersiz karakterleri temizle
            valid_tags = []
            for tag in tag_list:
                # Hashtag kaldır
                tag = tag.replace("#", "").strip()
                # Sadece harf, sayı, boşluk ve tire izin ver
                tag = ''.join(c for c in tag if c.isalnum() or c in (' ', '-')).strip()
                # Minimum 2 karakter, maksimum 30 karakter
                if len(tag) >= 2 and len(tag) <= 30:
                    valid_tags.append(tag)

            # YouTube 500 karakter limitini gözet
            final_tags, char_count = [], 0
            for tag in valid_tags:
                addition = len(tag) + (1 if final_tags else 0)  # +1 virgül için
                if char_count + addition <= 490:
                    final_tags.append(tag)
                    char_count += addition
                else:
                    break

            return final_tags if final_tags else ["ev", "electric vehicle", "battery", "range test", "charging"]

        except Exception as e:
            print(f"[Writer] Tag generation hatası: {e}")
            return ["ev", "electric vehicle", "battery", "EV range", "electric car", "EV news", "tesla", "charging speed"]
