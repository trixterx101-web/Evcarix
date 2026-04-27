import asyncio
from src.voice_engine import VoiceEngine

async def main():
    engine = VoiceEngine()
    text = "Welcome to Evcarix, your global weather assistant"
    output = "test_audio.mp3"
    await engine.generate_voice(text, output, voice_type="male")
    print(f"Test bitti. Dosya: {output}")

if __name__ == "__main__":
    asyncio.run(main())
