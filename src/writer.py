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
        if format_type == "short":
            return f"""
Topic: {topic}
Channel: Evcarix
Format: YouTube Short (Maximum 60 seconds)
Language: American English ONLY. Do NOT use any other language.

Requirements:
1. Start with a catchy hook in the first 3 seconds.
2. Energetic and informative tone.
3. Voiceover text only — no stage directions.
4. End with a Subscribe call to action.
5. Please respond ONLY in American English.

Return in this format:
SES: [male/female]
SENARYO: [script text]
"""
        else:
            return f"""
Topic: {topic}
Channel: Evcarix
Format: Long Video (6-8 minutes)
Language: American English ONLY. Do NOT use any other language.

Requirements:
1. Include intro, body, and conclusion.
2. Include technical details and market analysis.
3. Keep viewer engaged until the end.
4. Please respond ONLY in American English.

Return in this format:
SES: [male/female]
SENARYO: [script text]
"""

    def _generate_with_groq(self, prompt):
        completion = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a YouTube Shorts scriptwriter. Always write in fluent American English only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
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

    def generate_description(self, topic, title):
        channel_desc = (
            "Evcarix is a data-driven electric vehicle channel focused on real-world EV performance "
            "and battery science. We test electric cars beyond marketing claims — measuring true "
            "driving range, battery efficiency, winter range loss, cold weather performance, "
            "charging speed, charging costs, and long-term EV ownership experience.\n"
            "No hype. Just numbers."
        )
        return (
            f"{title}\n\n{topic}\n\n{channel_desc}\n\n"
            f"#ev #electriccar #electricvehicle #battery #tesla #evrange #Evcarix #shorts"
        )
