import os
import json

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()


class CreativeWriter:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") if GEMINI_AVAILABLE else None
        if GEMINI_AVAILABLE and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = None
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
            except ImportError:
                print("Groq kütüphanesi yüklü değil.")

    def generate_title(self, topic):
        """5 adet tıklanabilir İngilizce başlık üretir. Liste döner."""
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                prompt = (
                    f"You are a professional YouTube headline writer specializing in electric vehicles. "
                    f"Given the topic below, return exactly 5 highly clickable English titles, "
                    f"each under 70 characters, no numbering, as a JSON array of strings only. "
                    f"American English, data-driven tone, no hype.\n\nTopic: {topic}"
                )
                resp = self.gemini_model.generate_content(prompt)
                text = resp.text.strip().replace("```json", "").replace("```", "").strip()
                titles = json.loads(text)
                if isinstance(titles, list) and titles:
                    return titles
            except Exception as e:
                print(f"[Writer] generate_title hatası: {e}")

        if self.groq_client:
            try:
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You generate YouTube titles as JSON arrays only."},
                        {"role": "user", "content": f"Return 5 clickable EV YouTube titles for: {topic}. JSON array only."}
                    ],
                    temperature=0.7, max_tokens=300,
                )
                text = completion.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
                titles = json.loads(text)
                if isinstance(titles, list) and titles:
                    return titles
            except Exception as e:
                print(f"[Writer] Groq title hatası: {e}")

        # Fallback
        return [
            f"{topic}: The Real Numbers",
            f"Is {topic} Worth It? Full Test",
            f"{topic} — What No One Tells You",
            f"We Tested {topic} (Shocking Results)",
            f"{topic}: Hype vs Reality"
        ]

    def generate_script(self, topic, format_type="short"):
        """Video senaryosu ve ses tercihi oluşturur."""
        prompt = self._get_prompt(topic, format_type)

        if self.groq_client:
            try:
                print("Groq (Llama 3) kullanılıyor...")
                return self._generate_with_groq(prompt)
            except Exception as e:
                print(f"Groq hatası: {e}")

        if GEMINI_AVAILABLE and self.gemini_api_key:
            print("Gemini kullanılıyor...")
            return self._generate_with_gemini(prompt)

        raise Exception("Hiçbir LLM API anahtarı bulunamadı!")

    def _get_prompt(self, topic, format_type):
        evcarix_mission = (
            "Evcarix is a data-driven electric vehicle channel focused on real-world EV performance and battery science. "
            "No hype. Just numbers. Focus on driving range, battery efficiency, winter range loss, charging speed, "
            "and technical EV technology (LFP vs NMC, degradation, etc.)."
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
        response = self.gemini_model.generate_content(prompt)
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

    def generate_description(self, topic, title, tags_list):
        tags_line = " ".join([f"#{t.replace(' ', '')}" for t in tags_list[:8]])
        channel_desc = (
            "Evcarix is a data-driven electric vehicle channel focused on real-world EV performance "
            "and battery science. We test electric cars beyond marketing claims — measuring true "
            "driving range, battery efficiency, winter range loss, cold weather performance, "
            "charging speed, charging costs, and long-term EV ownership experience.\n\n"
            "On this channel you’ll find:\n"
            "• Real-world EV range tests\n"
            "• Winter vs summer EV performance comparisons\n"
            "• EV battery degradation analysis\n"
            "• LFP vs NMC battery comparisons\n"
            "• Fast charging impact explained\n\n"
            "Our mission: No hype. Just numbers. ⚡"
        )
        
        # SEO-friendly description content
        seo_content = (
            f"In this video, we dive deep into {topic}. "
            f"We analyze the data, performance metrics, and technical specifications to see "
            f"how it performs in real-world conditions. Does the range match the claims? "
            f"Watch to find out the real numbers behind {title}."
        )

        return (
            f"{title}\n\n"
            f"{seo_content}\n\n"
            f"{tags_line}\n\n"
            f"{channel_desc}\n\n"
            f"#Evcarix #ElectricVehicles #EV #BatteryScience #Tech #Data"
        )

    def generate_tags(self, topic, title):
        """Generates a comma-separated string of high-SEO tags (up to 499 chars)."""
        prompt = (
            f"Generate a list of high-SEO YouTube tags for a video about '{topic}' with title '{title}'. "
            f"Focus on electric vehicles, battery tech, and performance. "
            f"Return ONLY a comma-separated list of tags, no numbering, no hashtags, maximum 490 characters total."
        )
        
        try:
            if self.groq_client:
                completion = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200
                )
                tags = completion.choices[0].message.content.strip()
            elif GEMINI_AVAILABLE and self.gemini_api_key:
                resp = self.gemini_model.generate_content(prompt)
                tags = resp.text.strip()
            else:
                tags = "ev, electric vehicle, battery, range test, charging, tesla, ev news"
            
            # Clean up tags
            tags = tags.replace("\n", "").replace("Tags:", "").strip()
            if tags.startswith("[") and tags.endswith("]"):
                tags = tags[1:-1]
            return [t.strip() for t in tags.split(",") if t.strip()][:20]
        except:
            return ["ev", "electric vehicle", "battery", "range test", "charging"]
