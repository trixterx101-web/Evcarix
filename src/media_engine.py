import os
import requests
<<<<<<< HEAD
import asyncio
import edge_tts
from src.voice_engine import VoiceEngine
from dotenv import load_dotenv

load_dotenv()
=======
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip

>>>>>>> d0b04483447cc004bbce9fb8f096e62cafafcaca

class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
<<<<<<< HEAD
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
=======
        self.output_dir = "output"
        self.thumbnail_dir = os.path.join(self.output_dir, "thumbnails")
        os.makedirs(self.thumbnail_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def search_videos(self, query, per_page=5):
        """Search Pexels for videos matching query."""
        if not self.pexels_api_key:
            print("[MediaEngine] PEXELS_API_KEY not set.")
            return []
        headers = {"Authorization": self.pexels_api_key}
        url = "https://api.pexels.com/videos/search"
        params = {"query": query, "per_page": per_page, "orientation": "portrait"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=15)
            r.raise_for_status()
            videos = r.json().get("videos", [])
            return videos
        except Exception as e:
            print(f"[MediaEngine] Pexels search error: {e}")
            return []

    def download_video(self, video_data, filename):
        """Download a Pexels video file."""
        try:
            files = video_data.get("video_files", [])
            # Prefer HD portrait
            hd = [f for f in files if f.get("quality") in ("hd", "sd")]
            if not hd:
                return None
            url = hd[0]["link"]
            path = os.path.join(self.output_dir, filename)
            r = requests.get(url, stream=True, timeout=60)
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[MediaEngine] Downloaded: {path}")
            return path
        except Exception as e:
            print(f"[MediaEngine] Download error: {e}")
            return None

    def get_video_clips(self, topic, num_clips=4):
        """Search and download video clips for a topic."""
        videos = self.search_videos(topic, per_page=num_clips + 2)
        paths = []
        for i, v in enumerate(videos[:num_clips]):
            path = self.download_video(v, f"clip_{i}.mp4")
            if path:
                paths.append(path)
        return paths

    def generate_thumbnail(self, video_path, title, output_path,
                           channel_name="EVCARIX", slogan="No hype. Just numbers."):
        """Generate a striking thumbnail from a video frame."""
        try:
            # Extract frame from video
            clip = VideoFileClip(video_path)
            frame_time = min(2.0, clip.duration * 0.1)
            frame = clip.get_frame(frame_time)
            clip.close()

            img = Image.fromarray(frame).resize((1280, 720))
            draw = ImageDraw.Draw(img)

            # Dark gradient overlay (bottom half)
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            for y in range(img.height // 2, img.height):
                alpha = int(180 * (y - img.height // 2) / (img.height // 2))
                ov_draw.rectangle([(0, y), (img.width, y + 1)], fill=(0, 0, 0, alpha))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Load fonts
            font_path_bold = "fonts/Roboto-Bold.ttf"
            font_path_regular = "fonts/Roboto-Regular.ttf"

            try:
                title_font = ImageFont.truetype(font_path_bold, 72)
                channel_font = ImageFont.truetype(font_path_bold, 40)
                slogan_font = ImageFont.truetype(font_path_regular, 32)
            except Exception:
                title_font = ImageFont.load_default()
                channel_font = ImageFont.load_default()
                slogan_font = ImageFont.load_default()

            # Wrap title text
            words = title.split()
            lines = []
            current = ""
            for w in words:
                test = (current + " " + w).strip()
                bbox = draw.textbbox((0, 0), test, font=title_font)
                if bbox[2] - bbox[0] > 1200:
                    lines.append(current)
                    current = w
                else:
                    current = test
            if current:
                lines.append(current)

            # Draw title (yellow, bottom area)
            y_start = img.height - 60 - (len(lines) * 85) - 80
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                x = (img.width - (bbox[2] - bbox[0])) // 2
                # Shadow
                draw.text((x + 3, y_start + 3), line, font=title_font, fill=(0, 0, 0))
                # Main text
                draw.text((x, y_start), line, font=title_font, fill=(255, 220, 0))
                y_start += 85

            # Draw channel name (green)
            ch_bbox = draw.textbbox((0, 0), channel_name, font=channel_font)
            ch_x = (img.width - (ch_bbox[2] - ch_bbox[0])) // 2
            draw.text((ch_x, img.height - 110), channel_name,
                      font=channel_font, fill=(0, 230, 100))

            # Draw slogan (white, smaller)
            sl_bbox = draw.textbbox((0, 0), slogan, font=slogan_font)
            sl_x = (img.width - (sl_bbox[2] - sl_bbox[0])) // 2
            draw.text((sl_x, img.height - 65), slogan,
                      font=slogan_font, fill=(220, 220, 220))

            img.save(output_path, "JPEG", quality=95)
            print(f"[MediaEngine] Thumbnail saved: {output_path}")
            return output_path

        except Exception as e:
            print(f"[MediaEngine] Thumbnail error: {e}")
            return None
>>>>>>> d0b04483447cc004bbce9fb8f096e62cafafcaca
