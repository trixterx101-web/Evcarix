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
        edge-tts >= 6.1.9 ile uyumlu.
        """
        # Pronunciation normalization — apply BEFORE tts call
        text = text.replace("Evcarix", "Ev-Car-ix")
        text = text.replace("EVCARIX", "Ev-Car-ix")
        text = text.replace("evcarix", "Ev-Car-ix")
        
        voice = self.voices.get(voice_type, self.default_voice)
        print(f"[VoiceEngine] Ses kullanılıyor: {voice}")

        communicate = edge_tts.Communicate(text, voice, rate=rate)
        subs = []

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Önce audio dosyasını kaydet
        await communicate.save(output_path)

        # Sonra ayrı bir communicate instance ile word boundary al
        communicate2 = edge_tts.Communicate(text, voice, rate=rate)
        async for chunk in communicate2.stream():
            if chunk["type"] == "WordBoundary":
                # FIX: offset/duration artık int (100-nanosecond ticks)
                start_sec = chunk["offset"] / 10_000_000
                dur_sec = chunk["duration"] / 10_000_000
                subs.append({
                    "text": chunk["text"],
                    "start": start_sec,
                    "duration": dur_sec,
                })

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"[VoiceEngine] Ses dosyası oluşturulamadı: {output_path}")

        print(f"[VoiceEngine] ✅ Ses hazır: {output_path} | {len(subs)} kelime zamanlaması")
        return {"audio_path": output_path, "word_timings": subs}

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
