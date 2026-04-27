import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class CreativeWriter:
    def __init__(self):
        # Gemini setup
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Groq setup
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = None
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
            except ImportError:
                print("Groq kütüphanesi yüklü değil, Gemini kullanılacak.")

    def generate_script(self, topic, format_type="short"):
        """Verilen konu üzerine video senaryosu ve ses tercihi oluşturur."""
        prompt = self._get_prompt(topic, format_type)
        
        if self.groq_client:
            try:
                print("Metin üretimi için Groq (Llama 3) kullanılıyor...")
                return self._generate_with_groq(prompt)
            except Exception as e:
                print(f"Groq hatası: {str(e)}")
                import traceback
                traceback.print_exc()
                print("Gemini deneniyor...")
        
        if self.gemini_api_key:
            print("Metin üretimi için Gemini kullanılıyor...")
            return self._generate_with_gemini(prompt)
        
        raise Exception("Hiçbir LLM API anahtarı bulunamadı!")

    def _get_prompt(self, topic, format_type):
        if format_type == "short":
            return f"""
            Konu: {topic}
            Kanal Adı: Evcarix
            Format: YouTube Short (Maximum 60 seconds)
            Language: American English
            
            Requirements:
            1. Start with a catchy 'hook' sentence in the first 3 seconds.
            2. Use an energetic and informative tone.
            3. The text should only contain voiceover, specify scene descriptions in parentheses.
            4. End the video with a 'Subscribe' call to action.
            
            Please return in this format:
            SES: [male/female]
            SENARYO: [text]
            """
        else:
            return f"""
            Konu: {topic}
            Kanal Adı: Evcarix
            Format: Long Video (6-8 minutes)
            Language: American English
            
            Requirements:
            1. Include intro, body, and conclusion sections.
            2. Include technical details and market analysis.
            3. Add curiosity elements to keep the viewer until the end.
            
            Please return in this format:
            SES: [male/female]
            SENARYO: [text]
            """

    def _generate_with_groq(self, prompt):
        completion = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Sen global bir YouTube Shorts içerik üreticisisin. Dili akıcı, merak uyandırıcı ve enerjik bir Amerikan İngilizcesi olsun"},
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
            voice = "female" if any(word in voice_part for word in ["female", "kadın"]) else "male"
            if "SENARYO:" in text:
                script = text.split("SENARYO:")[1].strip()
        
        return {"voice": voice, "script": script}

if __name__ == "__main__":
    writer = CreativeWriter()
    # Not: API anahtarı olmadan çalışmaz
    # print(writer.generate_script("Tesla Model 2 Detayları", "short"))
