import os
import requests
import asyncio
import edge_tts
from src.voice_engine import VoiceEngine
from dotenv import load_dotenv

load_dotenv()

class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.voice_engine = VoiceEngine()

    async def generate_voiceover(self, text, output_path, voice_type="female", rate="+10%"):
        """Metni ses dosyasına dönüştürür (VoiceEngine kullanarak)."""
        return await self.voice_engine.generate_voice(text, output_path, voice_type=voice_type, rate=rate)

    def download_stock_videos(self, query, output_dir="assets/temp_videos", count=4, orientation="portrait"):
        """
        Pexels üzerinden birden fazla stok video indirir.
        :param query: Arama terimi (İngilizce)
        :param output_dir: Videoların kaydedileceği klasör
        :param count: İndirilecek video sayısı
        :param orientation: 'portrait', 'landscape' veya 'square'
        """
        if not self.pexels_api_key:
            print("Hata: PEXELS_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")
            return []

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Klasör oluşturuldu: {output_dir}")
        
        headers = {"Authorization": self.pexels_api_key}
        url = f"https://api.pexels.com/videos/search?query={query}&per_page={count}&orientation={orientation}"
        
        paths = []
        try:
            print(f"Pexels araması yapılıyor: '{query}' ({orientation})...")
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                videos = data.get('videos', [])
                
                if not videos:
                    print(f"Uyarı: '{query}' için video bulunamadı.")
                    return []

                for i, video_data in enumerate(videos):
                    # En iyi kalite yerine genellikle mobil uyumlu bir dosya seçmek mantıklı
                    # link listesinde HD veya SD olanı bulmaya çalışalım
                    video_files = video_data.get('video_files', [])
                    if not video_files:
                        continue
                        
                    # Genellikle ilk link en yüksek kalitedir, ama Shorts için çok büyük dosyalardan kaçınabiliriz
                    video_url = video_files[0]['link']
                    
                    filename = f"pexels_{query.replace(' ', '_')}_{i}.mp4"
                    output_path = os.path.join(output_dir, filename)
                    
                    print(f"İndiriliyor ({i+1}/{len(videos)}): {filename}...")
                    v_res = requests.get(video_url, stream=True)
                    if v_res.status_code == 200:
                        with open(output_path, 'wb') as f:
                            for chunk in v_res.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    f.write(chunk)
                        paths.append(output_path)
                    else:
                        print(f"Hata: Video indirilemedi ({v_res.status_code})")
            else:
                print(f"Pexels API Hatası: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Beklenmedik bir hata oluştu: {e}")
        
        print(f"Toplam {len(paths)} video başarıyla indirildi.")
        return paths

    def generate_thumbnail(self, video_path, title, output_path):
        """Video için kapak fotoğrafı oluşturur."""
        from PIL import Image, ImageDraw, ImageFont
        from moviepy.editor import VideoFileClip
        try:
            # Videodan bir kare al (ilk saniye)
            clip = VideoFileClip(video_path)
            frame_path = output_path.replace(".jpg", "_temp.jpg")
            clip.save_frame(frame_path, t=1.0) # 1. saniyeden kare al
            clip.close()
            
            img = Image.open(frame_path).convert("RGBA")
            img = img.resize((1280, 720))
            
            # Üzerine koyu bir katman ekle
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 100))
            img = Image.alpha_composite(img, overlay)
            
            draw = ImageDraw.Draw(img)
            try:
                font_title = ImageFont.truetype("arial.ttf", 80)
            except:
                font_title = ImageFont.load_default()
            
            # Metni böl (Eğer çok uzunsa)
            lines = [title[i:i+20] for i in range(0, len(title), 20)]
            y_text = 200
            for line in lines:
                text_bbox = draw.textbbox((0, 0), line, font=font_title)
                text_w = text_bbox[2] - text_bbox[0]
                draw.text(((1280-text_w)/2, y_text), line, fill="white", font=font_title, stroke_width=2, stroke_fill="black")
                y_text += 100
            
            # Evcarix logosu
            try:
                font_logo = ImageFont.truetype("arial.ttf", 30)
            except:
                font_logo = ImageFont.load_default()
            draw.text((50, 50), "EVCARIX", fill="#00ff00", font=font_logo)
            
            img.convert("RGB").save(output_path)
            
            # Geçici dosyayı sil
            if os.path.exists(frame_path):
                os.remove(frame_path)
                
            return output_path
        except Exception as e:
            print(f"Thumbnail oluşturulamadı: {e}")
            return None

if __name__ == "__main__":
    # Test bloğu
    engine = MediaEngine()
    
    # Video indirme testi
    test_query = "cyberpunk coffee"
    print(f"\n--- {test_query} için video indirme testi başlatılıyor ---")
    downloaded_files = engine.download_stock_videos(test_query, count=3)
    
    if downloaded_files:
        print(f"İndirilen dosyalar: {downloaded_files}")
    else:
        print("Test başarısız: Video indirilemedi.")
