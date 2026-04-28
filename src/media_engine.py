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

            # Koyu gradient overlay
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            for y in range(img.height // 2, img.height):
                alpha = int(190 * (y - img.height // 2) / (img.height // 2))
                ov_draw.rectangle([(0, y), (img.width, y + 1)], fill=(0, 0, 0, alpha))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Font yükle
            try:
                title_font = ImageFont.truetype("fonts/Roboto-Bold.ttf", 72)
                ch_font = ImageFont.truetype("fonts/Roboto-Bold.ttf", 40)
                sl_font = ImageFont.truetype("fonts/Roboto-Regular.ttf", 30)
            except Exception:
                try:
                    title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
                    ch_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
                    sl_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
                except Exception:
                    title_font = ch_font = sl_font = ImageFont.load_default()

            # Başlık satırlarına böl
            words = title.split()
            lines, current = [], ""
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

            # Başlık çiz (sarı)
            y_start = img.height - 70 - (len(lines) * 88) - 70
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                x = (img.width - (bbox[2] - bbox[0])) // 2
                draw.text((x + 3, y_start + 3), line, font=title_font, fill=(0, 0, 0))
                draw.text((x, y_start), line, font=title_font, fill=(255, 220, 0))
                y_start += 88

            # Kanal adı (yeşil)
            cb = draw.textbbox((0, 0), channel_name, font=ch_font)
            cx = (img.width - (cb[2] - cb[0])) // 2
            draw.text((cx, img.height - 110), channel_name, font=ch_font, fill=(0, 230, 100))

            # Slogan (beyaz)
            sb = draw.textbbox((0, 0), slogan, font=sl_font)
            sx = (img.width - (sb[2] - sb[0])) // 2
            draw.text((sx, img.height - 60), slogan, font=sl_font, fill=(210, 210, 210))

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "JPEG", quality=95)
            print(f"[MediaEngine] Thumbnail kaydedildi: {output_path}")
            return output_path
        except Exception as e:
            print(f"[MediaEngine] Thumbnail hatası: {e}")
            return None
