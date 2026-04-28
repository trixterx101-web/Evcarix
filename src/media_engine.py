import os
import requests
from src.voice_engine import VoiceEngine
from dotenv import load_dotenv

load_dotenv()


class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.voice_engine = VoiceEngine()

    async def generate_voiceover(self, text, output_path, voice_type="female", rate="+10%"):
        return await self.voice_engine.generate_voice(text, output_path, voice_type=voice_type, rate=rate)

    def download_stock_videos(self, query, output_dir="assets/temp_videos", count=4, orientation="portrait"):
        if not self.pexels_api_key:
            print("Hata: PEXELS_API_KEY bulunamadı!")
            return []
        os.makedirs(output_dir, exist_ok=True)

        headers = {"Authorization": self.pexels_api_key}
        url = f"https://api.pexels.com/videos/search?query={query}&per_page={count}&orientation={orientation}"
        paths = []
        try:
            print(f"Pexels: '{query}' aranıyor...")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                videos = response.json().get('videos', [])
                if not videos:
                    print(f"'{query}' için video bulunamadı.")
                    return []
                for i, video_data in enumerate(videos):
                    video_files = video_data.get('video_files', [])
                    if not video_files:
                        continue
                    video_url = video_files[0]['link']
                    filename = f"pexels_{query.replace(' ', '_')}_{i}.mp4"
                    output_path = os.path.join(output_dir, filename)
                    print(f"İndiriliyor ({i+1}/{len(videos)}): {filename}")
                    v_res = requests.get(video_url, stream=True, timeout=60)
                    if v_res.status_code == 200:
                        with open(output_path, 'wb') as f:
                            for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        paths.append(output_path)
            else:
                print(f"Pexels API Hatası: {response.status_code}")
        except Exception as e:
            print(f"Video indirme hatası: {e}")

        print(f"{len(paths)} video indirildi.")
        return paths

    def generate_thumbnail(self, video_path, title, output_path,
                           channel_name="EVCARIX", slogan="No hype. Just numbers."):
        """Çarpıcı thumbnail oluşturur."""
        from PIL import Image, ImageDraw, ImageFont
        from moviepy.editor import VideoFileClip
        try:
            clip = VideoFileClip(video_path)
            frame_time = min(2.0, clip.duration * 0.1)
            frame = clip.get_frame(frame_time)
            clip.close()

            img = Image.fromarray(frame).resize((1280, 720))

            # Premium Gradient Overlay (Darker & Smoother)
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            for y in range(img.height):
                alpha = int(220 * (y / img.height)**1.5) # Non-linear for better look
                ov_draw.rectangle([(0, y), (img.width, y + 1)], fill=(0, 0, 0, alpha))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Font yükle
            def get_font(font_name, size):
                possible_paths = [
                    f"fonts/{font_name}.ttf",
                    f"C:/Windows/Fonts/{font_name}.ttf",
                    f"C:/Windows/Fonts/{font_name.replace('Bold', 'bd')}.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        return ImageFont.truetype(p, size)
                return ImageFont.load_default()

            title_font = get_font("Roboto-Bold", 85) # Larger hook
            ch_font = get_font("Roboto-Bold", 45)
            sl_font = get_font("Roboto-Regular", 32)

            # Başlık satırlarına böl
            words = title.split()
            lines, current = [], ""
            for w in words:
                test = (current + " " + w).strip()
                bbox = draw.textbbox((0, 0), test, font=title_font)
                if bbox[2] - bbox[0] > 1100:
                    lines.append(current)
                    current = w
                else:
                    current = test
            if current:
                lines.append(current)

            # Başlık çiz (Sarı & Siyah Glow)
            y_start = (img.height // 2) - (len(lines) * 50)
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                x = (img.width - (bbox[2] - bbox[0])) // 2
                # Glow/Shadow layers
                for offset in range(1, 6):
                    draw.text((x + offset, y_start + offset), line, font=title_font, fill=(0, 0, 0, 100))
                # Ana metin
                draw.text((x, y_start), line, font=title_font, fill=(255, 235, 0)) # Vibrant Yellow
                y_start += 110

            # Kanal & Misyon (Altta bant şeklinde)
            footer_h = 160
            footer_bg = Image.new("RGBA", (img.width, footer_h), (0, 0, 0, 200))
            img.paste(footer_bg, (0, img.height - footer_h), footer_bg)
            
            # Kanal adı (Canlı Yeşil)
            cb = draw.textbbox((0, 0), channel_name, font=ch_font)
            cx = (img.width - (cb[2] - cb[0])) // 2
            draw.text((cx, img.height - 130), channel_name, font=ch_font, fill=(0, 255, 150))

            # Slogan (Parlak Beyaz)
            sb = draw.textbbox((0, 0), slogan, font=sl_font)
            sx = (img.width - (sb[2] - sb[0])) // 2
            draw.text((sx, img.height - 65), slogan.upper(), font=sl_font, fill=(255, 255, 255))

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "JPEG", quality=98) # Ultra quality
            print(f"[MediaEngine] Thumbnail kaydedildi: {output_path}")
            return output_path
        except Exception as e:
            print(f"[MediaEngine] Thumbnail hatası: {e}")
            return None
