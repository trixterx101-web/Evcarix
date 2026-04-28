import os
import json

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


class CreativeWriter:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") if GEMINI_AVAILABLE else None
        if GEMINI_AVAILABLE and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_title(self, topic):
        """Generate 5 clickable English YouTube titles. Returns a list."""
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                prompt = (
                    f"You are a professional YouTube headline writer specializing in electric vehicles. "
                    f"Given the topic below, return exactly 5 highly clickable English titles, "
                    f"each under 70 characters, no numbering, as a JSON array of strings. "
                    f"Use American English only. No hype — data-driven tone.\n\nTopic: {topic}"
                )
                resp = self.gemini_model.generate_content(prompt)
                text = resp.text.strip().replace("```json", "").replace("```", "").strip()
                titles = json.loads(text)
                if isinstance(titles, list) and titles:
                    return titles
            except Exception as e:
                print(f"[Writer] generate_title Gemini error: {e}")

        # Fallback templates
        return [
            f"{topic}: The Real Numbers",
            f"Is {topic} Worth It? Full Test",
            f"{topic} — What No One Tells You",
            f"We Tested {topic} (Shocking Results)",
            f"{topic}: Hype vs Reality"
        ]

    def generate_script(self, topic, duration_seconds=58):
        """Generate a short YouTube Shorts script in English."""
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                prompt = (
                    f"You are a scriptwriter for an EV YouTube Shorts channel called Evcarix. "
                    f"Write a {duration_seconds}-second script about: {topic}\n\n"
                    f"Rules:\n"
                    f"- ONLY in American English\n"
                    f"- No hype, data-driven, factual\n"
                    f"- Hook in first 3 seconds\n"
                    f"- Clear, short sentences (spoken aloud)\n"
                    f"- End with a call to action (like/subscribe/comment)\n"
                    f"- Return ONLY the spoken script text, no stage directions"
                )
                resp = self.gemini_model.generate_content(prompt)
                return resp.text.strip()
            except Exception as e:
                print(f"[Writer] generate_script Gemini error: {e}")

        # Fallback script
        return (
            f"Today we're talking about {topic}. "
            f"Most people don't know the real numbers behind this. "
            f"We tested it so you don't have to. "
            f"The results might surprise you. "
            f"Stay tuned, like this video, and subscribe for more data-driven EV content."
        )

    def generate_description(self, topic, title):
        """Generate a YouTube video description."""
        channel_desc = (
            "Evcarix is a data-driven electric vehicle channel focused on real-world EV performance "
            "and battery science. We test electric cars beyond marketing claims — measuring true "
            "driving range, battery efficiency, winter range loss, cold weather performance, "
            "charging speed, charging costs, and long-term EV ownership experience.\n"
            "No hype. Just numbers."
        )
        return (
            f"{title}\n\n"
            f"{topic}\n\n"
            f"{channel_desc}\n\n"
            f"#ev #electriccar #electricvehicle #battery #tesla #evrange #Evcarix #shorts"
        )
