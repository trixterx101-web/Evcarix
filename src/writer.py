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
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") if GEMINI_AVAILABLE else None
        self.gemini_client = None
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                print(f"[Writer] Gemini init hatası: {e}")
                self.gemini_client = None

        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = None
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
            except ImportError:
                print("Groq kütüphanesi yüklü değil.")

    # ─────────────────────────────────────────────────────────────────
    # BAŞLIK — Viral CTR Optimizasyonu
    # ─────────────────────────────────────────────────────────────────
    def generate_title(self, topic):
        """YouTube viral CTR optimizasyonlu başlık üretir (5 adet)."""
        prompt = (
            f"You are a top YouTube growth strategist specializing in electric vehicles. "
            f"Write viral, high click-through-rate YouTube Shorts titles.\n"
            f"Rules:\n"
            f"1. Each title must be under 70 characters\n"
            f"2. Use specific numbers/stats when possible (e.g. '347 miles', '80% in 18 min')\n"
            f"3. Create curiosity gap or tension (surprising facts, comparisons, shocking results)\n"
            f"4. Use power words: Real, Tested, Proven, Exposed, Shocking, Hidden, vs, Miles, Range\n"
            f"5. American English ONLY. No hype words like 'amazing' or 'incredible'\n"
            f"6. Return ONLY a JSON array of exactly 5 strings, no numbering\n\n"
            f"Topic: {topic}\n"
            f"Example format: [\"Title 1\", \"Title 2\", ...]"
        )

        if GEMINI_AVAILABLE and self.gemini_client:
            try:
                resp = self.gemini_client.models.generate_content(
                    model='gemini-1.5-flash', contents=prompt
                )
                text = resp.text.strip().replace("```json", "").replace("```", "").strip()
                titles = json.loads(text)
                if isinstance(titles, list) and titles:
                    return titles
            except Exception as e:
                print(f"[Writer] generate_title hatası (Gemini): {e}")

        if self.groq_client:
            try:
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a YouTube growth expert. Return only valid JSON arrays of title strings. American English only. Use numbers, data, and power words."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.85, max_tokens=400,
                )
                text = completion.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
                titles = json.loads(text)
                if isinstance(titles, list) and titles:
                    return titles
            except Exception as e:
                print(f"[Writer] generate_title hatası (Groq): {e}")

        # Fallback — data-driven format
        return [
            f"We Tested {topic}: The Real Numbers",
            f"{topic}: What They Don't Tell You",
            f"Shocking {topic} Data After 100k Miles",
            f"{topic} vs The Competition (Real Test)",
            f"{topic}: Is The Hype Real?"
        ]

    # ─────────────────────────────────────────────────────────────────
    # SENARYO
    # ─────────────────────────────────────────────────────────────────
    def generate_script(self, topic, format_type="short"):
        """Video senaryosu ve ses tercihi oluşturur."""
        prompt = self._get_prompt(topic, format_type)

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

    def _get_prompt(self, topic, format_type):
        evcarix_mission = (
            "Evcarix is a data-driven electric vehicle channel focused on real-world EV performance and battery science. "
            "We test electric cars beyond marketing claims — measuring true driving range, battery efficiency, winter range loss, "
            "cold weather performance, charging speed, charging costs, and long-term EV ownership experience. "
            "Mission: No hype. Just numbers."
        )
        if format_type == "short":
            return f"""
Topic: {topic}
Channel Concept: {evcarix_mission}
Format: YouTube Short (Maximum 55 seconds)
Language: American English ONLY.

Requirements:
1. Start with a data-driven hook (e.g., "The real range of {topic} will surprise you").
2. Focus on facts, numbers, and technical insights. No generic "amazing" or "incredible" hype.
3. Voiceover text only — no stage directions.
4. End with: "Subscribe to Evcarix for real EV data."
5. Please respond ONLY in American English.

Return in this format:
SES: [male/female]
SENARYO: [script text]
"""
        else:
            return f"""
Topic: {topic}
Channel Concept: {evcarix_mission}
Format: Long Video (6-8 minutes)
Language: American English ONLY.

Requirements:
1. Deep dive into technical details, battery chemistry, or real-world performance metrics.
2. Maintain a professional, educational, and analytical tone.
3. Please respond ONLY in American English.

Return in this format:
SES: [male/female]
SENARYO: [script text]
"""

    def _generate_with_groq(self, prompt):
        completion = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a specialized technical EV analyst and scriptwriter for Evcarix. You focus on data, battery science, and real-world metrics without hype."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=2048,
        )
        return self._parse_response(completion.choices[0].message.content)

    def _generate_with_gemini(self, prompt):
        response = self.gemini_client.models.generate_content(
            model='gemini-1.5-flash', contents=prompt
        )
        return self._parse_response(response.text)

    def _parse_response(self, text):
        voice = "female"
        script = text
        if "SES:" in text:
            voice_part = text.split("SES:")[1].split("\n")[0].strip().lower()
            voice = "female" if any(w in voice_part for w in ["female", "kadın"]) else "male"
            if "SENARYO:" in text:
                script = text.split("SENARYO:")[1].strip()
        return {"voice": voice, "script": script}

    # ─────────────────────────────────────────────────────────────────
    # AÇIKLAMA — AI Destekli SEO Optimizasyonu
    # ─────────────────────────────────────────────────────────────────
    def generate_description(self, topic, title, tags_list):
        """YouTube SEO için optimize edilmiş, başlıkla bire bir örtüşen açıklama üretir."""
        hashtags = " ".join([f"#{t.replace(' ', '').replace('-', '')}" for t in tags_list[:10]])

        channel_about = (
            "\n🔋 About Evcarix:\n"
            "Data-driven electric vehicle channel. Real-world range tests, battery degradation,\n"
            "winter EV performance, charging speed analysis, and true ownership costs.\n"
            "Mission: No hype. Just numbers. ⚡\n"
            "Subscribe for honest EV data every day."
        )

        prompt = (
            f"Write a highly SEO-optimized YouTube description for a Shorts video.\n"
            f"Video title: '{title}'\n"
            f"Topic: {topic}\n"
            f"Channel: Evcarix — data-driven EV channel, no hype, just numbers\n\n"
            f"Requirements:\n"
            f"1. First 2 lines must be a strong hook matching the title (shown in search preview)\n"
            f"2. Add 'What you'll learn:' bullet list with 4 specific data-driven points\n"
            f"3. Add a CTA: 'Subscribe to Evcarix for real EV data every day'\n"
            f"4. Include naturally embedded keyword phrases related to the topic\n"
            f"5. Max 350 words. American English only.\n"
            f"Return only the description text, no extra formatting."
        )

        seo_body = ""
        try:
            if self.groq_client:
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )
                seo_body = completion.choices[0].message.content.strip()
            elif GEMINI_AVAILABLE and self.gemini_client:
                resp = self.gemini_client.models.generate_content(
                    model='gemini-1.5-flash', contents=prompt
                )
                seo_body = resp.text.strip()
        except Exception as e:
            print(f"[Writer] Description generation hatası: {e}")

        if not seo_body:
            seo_body = (
                f"{title}\n\n"
                f"We test {topic} beyond marketing claims — real numbers only.\n\n"
                f"What you'll learn:\n"
                f"• Real-world range data\n"
                f"• Battery efficiency metrics\n"
                f"• True ownership cost breakdown\n"
                f"• How it compares to rivals\n\n"
                f"Subscribe to Evcarix for real EV data every day."
            )

        return (
            f"{seo_body}\n\n"
            f"{hashtags} #Shorts #EV #ElectricCar #Evcarix\n"
            f"{channel_about}"
        )

    # ─────────────────────────────────────────────────────────────────
    # ETİKETLER — YouTube 500 Karakter Limiti Gözetilerek
    # ─────────────────────────────────────────────────────────────────
    def generate_tags(self, topic, title):
        """YouTube SEO için optimize edilmiş etiket listesi üretir (maks. 500 karakter)."""
        prompt = (
            f"You are a YouTube SEO expert. Generate the BEST possible tags for a YouTube Shorts video.\n"
            f"Video title: '{title}'\n"
            f"Topic: {topic}\n"
            f"Channel niche: Electric vehicles, battery technology, EV performance data\n\n"
            f"Tag strategy:\n"
            f"1. Start with 3 broad tags (ev, electric car, electric vehicle)\n"
            f"2. Add 5 medium-competition tags specific to the topic\n"
            f"3. Add 4 long-tail specific tags (e.g., 'tesla model 3 range test 2024')\n"
            f"4. Add 2 trending tags (ev news, electric car 2024)\n"
            f"5. Total must be under 490 characters when joined with commas\n\n"
            f"Return ONLY a comma-separated list of tags. No hashtags. No numbering. American English only."
        )

        try:
            raw_tags = ""
            if self.groq_client:
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=250
                )
                raw_tags = completion.choices[0].message.content.strip()
            elif GEMINI_AVAILABLE and self.gemini_client:
                resp = self.gemini_client.models.generate_content(
                    model='gemini-1.5-flash', contents=prompt
                )
                raw_tags = resp.text.strip()

            # Temizlik
            raw_tags = raw_tags.replace("\n", "").replace("Tags:", "").replace("```", "").strip()
            if raw_tags.startswith("[") and raw_tags.endswith("]"):
                raw_tags = raw_tags[1:-1]
            tag_list = [t.strip().strip('"').strip("'") for t in raw_tags.split(",") if t.strip()]

            # YouTube 500 karakter limitini gözet
            final_tags, char_count = [], 0
            for tag in tag_list:
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
