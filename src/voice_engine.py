import edge_tts
import asyncio
import os

class VoiceEngine:
    def __init__(self):
        # Premium voices (Microsoft Edge Neural)
        self.voices = {
            "male": "en-US-AndrewNeural",
            "female": "en-US-AvaNeural"
        }
        self.default_voice = "en-US-AvaNeural"

    async def generate_voice(self, text, output_path, voice_type="female", rate="+0%"):
        """
        Metni ses dosyasına dönüştürür ve kelime zamanlamalarını döner.
        """
        voice = self.voices.get(voice_type, self.default_voice)
        print(f"[VoiceEngine] Premium ses kullanılıyor: {voice}")
        
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        subs = []
        
        # Sesi kaydet ve kelime zamanlamalarını topla
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    subs.append({
                        "text": chunk["text"],
                        "start": chunk["offset"] / 10**7, # Saniyeye çevir
                        "duration": chunk["duration"] / 10**7
                    })
        
        if os.path.exists(output_path):
            print(f"[VoiceEngine] Premium ses dosyası ve {len(subs)} kelime zamanlaması hazır.")
            return {"audio_path": output_path, "word_timings": subs}
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
