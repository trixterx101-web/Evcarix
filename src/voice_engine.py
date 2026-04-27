import edge_tts
import asyncio
import os

class VoiceEngine:
    def __init__(self):
        # Varsayılan sesler (İngilizce ABD)
        self.voices = {
            "male": "en-US-GuyNeural",
            "female": "en-US-AriaNeural"
        }
        self.default_voice = "en-US-AriaNeural"

    async def generate_voice(self, text, output_path, voice_type="female", rate="+10%"):
        """
        Metni ses dosyasına dönüştürür (edge-tts kullanarak).
        :param text: Seslendirilecek metin
        :param output_path: Kaydedilecek dosya yolu (.mp3)
        :param voice_type: 'male' veya 'female'
        :param rate: Konuşma hızı (örn: '+10%', '-5%')
        """
        voice = self.voices.get(voice_type, self.default_voice)
        
        print(f"Seslendirme yapılıyor: {voice} (Hız: {rate})...")
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(output_path)
        
        if os.path.exists(output_path):
            print(f"Ses dosyası başarıyla oluşturuldu: {output_path}")
            return output_path
        else:
            raise Exception("Ses dosyası oluşturulamadı!")

    async def list_available_voices(self):
        """Kullanılabilir tüm sesleri listeler (Opsiyonel)."""
        voices = await edge_tts.VoicesManager.create()
        return voices.find(Locale="en-US")

if __name__ == "__main__":
    # Test bloğu
    async def test():
        engine = VoiceEngine()
        test_text = "Hello, this is a test for Evcarix Auto-Studio voice engine using Aria voice and 10 percent increased rate."
        test_output = "test_voice_aria.mp3"
        await engine.generate_voice(test_text, test_output) # Will use female/Aria and +10% by default

    asyncio.run(test())
