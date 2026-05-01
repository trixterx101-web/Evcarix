"""
Lip-sync Video Generator
Uses Wav2Lip to generate talking character videos
"""

import os
import subprocess
import requests
import json
from pathlib import Path
from dotenv import load_dotenv
from src.writer import CreativeWriter

load_dotenv()


class LipSyncGenerator:
    def __init__(self):
        self.wav2lip_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Wav2Lip")
        self.writer = CreativeWriter()  # Use existing CreativeWriter for script generation
        from src.media_engine import MediaEngine
        self.media_engine = MediaEngine()  # Use existing voice engine
        
    def generate_script(self, topic, lang="en"):
        """Generate script using existing Writer (Gemini/Groq)"""
        try:
            # Use Writer's generate_title to get a short script-like title
            title = self.writer.generate_title(topic)
            
            # Generate a short script based on the topic
            script_prompt = f"Write a short YouTube Shorts script about {topic}. Max 80 words. Conversational style."
            
            # Use Groq for quick script generation
            from groq import Groq
            groq_api_keys = [
                os.getenv("GROQ_API_KEY"),
                os.getenv("GROQ_API_KEY_2"),
                os.getenv("GROQ_API_KEY_3")
            ]
            groq_api_keys = [k for k in groq_api_keys if k]
            
            for api_key in groq_api_keys:
                try:
                    client = Groq(api_key=api_key)
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": "You are a YouTube Shorts script writer. Keep it under 80 words, engaging and punchy."},
                            {"role": "user", "content": script_prompt}
                        ],
                        max_tokens=200
                    )
                    script = response.choices[0].message.content.strip()
                    
                    return {
                        "script": script,
                        "title": title[:60],
                        "subtitle": topic[:30],
                        "stat": "95%",
                        "accent_color": "#FF0000"
                    }
                except Exception as e:
                    print(f"[LipSync] Groq hatası: {e}")
                    continue
            
            return self._default_script(topic, lang)
        except Exception as e:
            print(f"[LipSync] Script generation hatası: {e}")
            return self._default_script(topic, lang)
    
    def _default_script(self, topic, lang="en"):
        """Fallback script when API fails"""
        if lang == "tr":
            return {
                "script": f"{topic} hakkında şok edici bir gerçek. Bu veriler, endüstride büyük bir değişimi işaret ediyor. Evcarix'te gerçek rakamları takip etmeye devam edin.",
                "title": "ŞOK EDİCİ VERİ",
                "subtitle": topic[:30],
                "stat": "95%",
                "accent_color": "#FF0000"
            }
        else:
            return {
                "script": f"Here's a shocking fact about {topic}. This data signals a major shift in the industry. Stay tuned to Evcarix for real numbers.",
                "title": "SHOCKING DATA",
                "subtitle": topic[:30],
                "stat": "95%",
                "accent_color": "#FF0000"
            }
    
    async def text_to_speech(self, text, output_path, lang="en"):
        """Convert text to speech using edge-tts VoiceEngine"""
        try:
            import edge_tts
            
            voice = "tr-TR-AhmetNeural" if lang == "tr" else "en-US-AvaNeural"
            communicate = edge_tts.Communicate(text, voice)
            
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            with open(output_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"[LipSync] ✅ TTS tamamlandı (edge-tts)")
                return True
            else:
                print(f"[LipSync] ❌ TTS başarısız - dosya boş")
                return False
        except ImportError:
            print("[LipSync] edge-tts yüklü değil")
            return False
        except Exception as e:
            print(f"[LipSync] TTS hatası: {e}")
            return False
    
    async def run_wav2lip(self, face_image, audio_path, output_path):
        """Run Wav2Lip inference"""
        inference_path = os.path.join(self.wav2lip_path, "inference.py")
        checkpoint_path = os.path.join(self.wav2lip_path, "checkpoints", "wav2lip_gan.pth")
        
        if not os.path.exists(inference_path):
            print(f"[LipSync] Wav2Lip inference.py bulunamadı: {inference_path}")
            return False
        
        if not os.path.exists(checkpoint_path):
            print(f"[LipSync] Wav2Lip checkpoint bulunamadı: {checkpoint_path}")
            print(f"[LipSync] Lütfen modeli indirin ve checkpoints/ klasörüne koyun")
            return False
        
        try:
            cmd = [
                "python",
                inference_path,
                "--checkpoint_path", checkpoint_path,
                "--face", face_image,
                "--audio", audio_path,
                "--outfile", output_path,
                "--resize_factor", "1"
            ]
            
            print(f"[LipSync] Wav2Lip çalıştırılıyor...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"[LipSync] ✅ Lip-sync tamamlandı: {output_path}")
                return True
            else:
                print(f"[LipSync] Wav2Lip hatası: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("[LipSync] Wav2Lip zaman aşımı (5 dakika)")
            return False
        except Exception as e:
            print(f"[LipSync] Wav2Lip çalıştırma hatası: {e}")
            return False
    
    def compose_final_video(self, lipsync_video, script_data, audio_path, output_path):
        """Compose final 9:16 video using FFmpeg"""
        try:
            # Create dark gradient background
            bg_path = output_path.replace(".mp4", "_bg.png")
            self._create_gradient_background(bg_path)
            
            # Get audio duration
            import subprocess
            duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path]
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
            duration = float(duration_result.stdout.strip()) if duration_result.returncode == 0 else 30
            
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-y",
                "-i", bg_path,
                "-i", lipsync_video,
                "-i", audio_path,
                "-filter_complex",
                f"[1:v]scale=1080:1152[scaled];[0:v][scaled]overlay=(W-w)/2:50[v];[v]drawtext=text='{script_data['title']}':fontcolor=white:fontsize=48:x=(W-text_w)/2:y=1250:fontfile=C\\:/Windows/Fonts/arialbd.ttf",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-shortest",
                "-pix_fmt", "yuv420p",
                output_path
            ]
            
            print(f"[LipSync] Final video oluşturuluyor...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"[LipSync] ✅ Final video hazır: {output_path}")
                
                # Cleanup temp files
                if os.path.exists(bg_path):
                    os.remove(bg_path)
                
                return True
            else:
                print(f"[LipSync] FFmpeg hatası: {result.stderr}")
                return False
        except Exception as e:
            print(f"[LipSync] Video kompozisyon hatası: {e}")
            return False
    
    def _create_gradient_background(self, output_path):
        """Create dark gradient background (1080x1920)"""
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1080, 1920), (10, 10, 20))
        draw = ImageDraw.Draw(img)
        
        # Simple gradient
        for y in range(1920):
            r = int(10 + (y / 1920) * 20)
            g = int(10 + (y / 1920) * 10)
            b = int(20 + (y / 1920) * 30)
            draw.line([(0, y), (1080, y)], fill=(r, g, b))
        
        img.save(output_path)
    
    async def generate_lipsync_video(self, topic, character_image, output_dir, lang="en"):
        """Complete pipeline to generate lip-sync video"""
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"  Lip-sync Video Generator")
        print(f"  Topic: {topic}")
        print(f"  Character: {character_image}")
        print(f"{'='*60}\n")
        
        # Step 1: Generate script
        print("[1/5] Script oluşturuluyor...")
        script_data = self.generate_script(topic, lang)
        print(f"      Script: {script_data['script'][:50]}...")
        
        # Step 2: Text-to-speech
        print("\n[2/5] Seslendirme yapılıyor...")
        audio_path = os.path.join(output_dir, "audio.wav")
        tts_success = await self.text_to_speech(script_data['script'], audio_path, lang)
        if not tts_success:
            print("[LipSync] ❌ TTS başarısız")
            return None
        
        # Step 3: Lip-sync
        print("\n[3/5] Lip-sync işlemi yapılıyor...")
        lipsync_path = os.path.join(output_dir, "lipsync.mp4")
        lipsync_success = await self.run_wav2lip(character_image, audio_path, lipsync_path)
        if not lipsync_success:
            print("[LipSync] ❌ Lip-sync başarısız, fallback kullanılıyor...")
            return None
        
        # Step 4: Compose final video
        print("\n[4/5] Final video oluşturuluyor...")
        final_path = os.path.join(output_dir, "final_short.mp4")
        compose_success = self.compose_final_video(lipsync_path, script_data, audio_path, final_path)
        if not compose_success:
            print("[LipSync] ❌ Video kompozisyon başarısız")
            return None
        
        # Step 5: Thumbnail
        print("\n[5/5] Thumbnail oluşturuluyor...")
        thumbnail_path = os.path.join(output_dir, "thumbnail.png")
        # Use existing thumbnail generator if available
        print(f"      Thumbnail: {thumbnail_path}")
        
        print(f"\n{'='*60}")
        print(f"  ✅ TAMAMLANDI!")
        print(f"  Video: {final_path}")
        print(f"  Thumbnail: {thumbnail_path}")
        print(f"  Script: {script_data['script']}")
        print(f"{'='*60}\n")
        
        return {
            "video": final_path,
            "thumbnail": thumbnail_path,
            "script": script_data['script'],
            "title": script_data['title'],
            "subtitle": script_data['subtitle'],
            "stat": script_data['stat'],
            "accent_color": script_data['accent_color']
        }
