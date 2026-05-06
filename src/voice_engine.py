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
        import re

        # ── TELAFFUZ DÜZELTİCİ ─────────────────────────────────────────────────
        # Edge TTS "Evcarix" kelimesini yanlış okuyor.
        # "EV car icks" → TTS bunu doğal olarak [EV-kar-iks] şeklinde okur.
        # Tüm varyasyonlar (büyük/küçük harf, tireli, kaçış karakterli) yakalanır.
        pronunciation_map = [
            # Evcarix ve tüm varyasyonları → "EV car icks"
            (r"(?i)\bEv[-\s]?car[-\s]?ix\b", "EV car icks"),
            (r"(?i)\bEvcarix\b",              "EV car icks"),
            (r"(?i)\bEVCARIX\b",              "EV car icks"),
            (r"(?i)\bEvCARix\b",              "EV car icks"),
            (r"(?i)\bEvCarIx\b",              "EV car icks"),
            (r"(?i)\bEv-CAR-ix\b",            "EV car icks"),
            (r"(?i)\bEvcaris\b",              "EV car icks"),
            (r"(?i)\bEverix\b",               "EV car icks"),
            # Cümle içi (apostrophe, possessive vb.)
            (r"(?i)\bEvcarix's\b",            "EV car icks"),
            (r"(?i)\bEvcarix'te\b",           "EV car icks"),
            (r"(?i)\bEvcarix'in\b",           "EV car icks"),
        ]
        for pattern, replacement in pronunciation_map:
            text = re.sub(pattern, replacement, text)

        # Videonun sonunda sesin aniden kesilmemesi için 0.5 saniyelik sessizlik tamponu
        text += " . . ."
        
        voice = self.voices.get(voice_type, self.default_voice)
        print(f"[VoiceEngine] Ses kullanılıyor: {voice}")

        communicate = edge_tts.Communicate(text, voice, rate=rate)
        subs = []

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Stream and save simultaneously to ensure word boundaries are captured
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # FIX: offset/duration are in 100-nanosecond units
                    start_sec = chunk["offset"] / 10_000_000
                    dur_sec = chunk["duration"] / 10_000_000
                    subs.append({
                        "text": chunk["text"],
                        "start": start_sec,
                        "duration": dur_sec,
                    })

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"[VoiceEngine] Ses dosyası oluşturulamadı: {output_path}")

        print(f"[VoiceEngine] [OK] Ses hazir: {output_path} | {len(subs)} kelime zamanlamasi")
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
