import os
import re
import random
import requests
from src.voice_engine import VoiceEngine
from dotenv import load_dotenv

load_dotenv()



class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.voice_engine = VoiceEngine()

    async def generate_voiceover(self, text, output_path, voice_type="female", rate="+10%"):
        return await self.voice_engine.generate_voice(text, output_path, voice_type=voice_type, rate=rate)

    def _get_professional_query(self, topic):
        """Her çalışmada farklı bir arama sorgusu üretir."""
        clean_topic = topic.split(':')[0].split('?')[0].strip() if ':' in topic or '?' in topic else topic
        # Her çalışmada farklı strateji — 7 farklı çerçeve
        strategies = [
            f"{clean_topic} electric car 4k cinematic",
            f"{clean_topic} EV driving footage",
            f"electric vehicle {clean_topic} exterior",
            f"{clean_topic} car interior technology",
            f"modern electric car {clean_topic} driving",
            "electric car charging station cinematic 4k",
            "electric vehicle highway driving sunset",
            "EV battery technology laboratory",
            "electric car dashboard display tech",
            "sustainable transport electric vehicle city",
        ]
        return random.choice(strategies)

    # ─── Pexels Video İndirme ──────────────────────────────────────────────────
    def _download_from_pexels(self, query, output_dir, count, orientation):
        """Pexels API'den rastgele sayfa ve sorgu ile video indirir."""
        if not self.pexels_api_key:
            print("[Pexels] API key bulunamadı, atlanıyor.")
            return []

        optimized_query = self._get_professional_query(query)
        headers = {"Authorization": self.pexels_api_key}
        page = random.randint(1, 8)

        url = (
            f"https://api.pexels.com/videos/search"
            f"?query={optimized_query}"
            f"&per_page={count + 4}"
            f"&page={page}"
            f"&orientation={orientation}"
        )
        paths = []
        try:
            print(f"[Pexels] '{optimized_query}' (sayfa {page}) aranıyor...")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                videos = response.json().get('videos', [])
                if not videos:
                    url_p1 = url.replace(f"&page={page}", "&page=1")
                    response = requests.get(url_p1, headers=headers, timeout=15)
                    videos = response.json().get('videos', []) if response.status_code == 200 else []
                random.shuffle(videos)
                for i, video_data in enumerate(videos[:count]):
                    video_files = video_data.get('video_files', [])
                    if not video_files:
                        continue
                    sorted_files = sorted(video_files, key=lambda x: x.get('width', 0), reverse=True)
                    chosen = random.choice(sorted_files[:3]) if len(sorted_files) >= 3 else sorted_files[0]
                    video_url = chosen['link']
                    clean_q = re.sub(r'[^\w\s-]', '', query).strip().replace(' ', '_')[:30]
                    filename = f"pexels_{clean_q}_{page}_{i}.mp4"
                    out_path = os.path.join(output_dir, filename)
                    v_res = requests.get(video_url, stream=True, timeout=60)
                    if v_res.status_code == 200:
                        with open(out_path, 'wb') as f:
                            for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        paths.append(out_path)
                        print(f"[Pexels] ✅ İndirildi: {filename}")
            else:
                print(f"[Pexels] API hatası: {response.status_code}")
        except Exception as e:
            print(f"[Pexels] İndirme hatası: {e}")
        return paths

    # ─── Pixabay Video İndirme ─────────────────────────────────────────────────
    def _download_from_pixabay(self, query, output_dir, count, orientation):
        """Pixabay API'den video indirir. Ücretsiz & ticari kullanım serbest."""
        if not self.pixabay_api_key:
            print("[Pixabay] API key bulunamadı, atlanıyor.")
            return []

        pixabay_queries = [
            "electric car",
            "EV charging",
            "electric vehicle",
            "car technology",
            "sustainable energy car",
            "battery electric",
            "modern car driving",
            "car highway",
        ]
        optimized_query = random.choice(pixabay_queries)
        page = random.randint(1, 5)
        pix_orientation = "vertical" if orientation == "portrait" else "horizontal"

        url = "https://pixabay.com/api/videos/"
        params = {
            'key': self.pixabay_api_key,
            'q': optimized_query,
            'video_type': 'film',
            'orientation': pix_orientation,
            'order': 'popular',
            'per_page': count + 4,
            'page': page,
            'safesearch': 'true',
        }
        paths = []
        try:
            print(f"[Pixabay] '{optimized_query}' (sayfa {page}) aranıyor...")
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                hits = response.json().get('hits', [])
                if not hits:
                    params['page'] = 1
                    response = requests.get(url, params=params, timeout=15)
                    hits = response.json().get('hits', []) if response.status_code == 200 else []
                random.shuffle(hits)
                for i, hit in enumerate(hits[:count]):
                    videos_dict = hit.get('videos', {})
                    chosen_video = None
                    for quality in ['large', 'medium', 'small', 'tiny']:
                        if quality in videos_dict and videos_dict[quality].get('url'):
                            chosen_video = videos_dict[quality]
                            break
                    if not chosen_video:
                        continue
                    video_url = chosen_video['url']
                    clean_q = re.sub(r'[^\w\s-]', '', optimized_query).strip().replace(' ', '_')[:30]
                    filename = f"pixabay_{clean_q}_{page}_{i}.mp4"
                    out_path = os.path.join(output_dir, filename)
                    v_res = requests.get(video_url, stream=True, timeout=60)
                    if v_res.status_code == 200:
                        with open(out_path, 'wb') as f:
                            for chunk in v_res.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        paths.append(out_path)
                        print(f"[Pixabay] ✅ İndirildi: {filename}")
            else:
                print(f"[Pixabay] API hatası: {response.status_code}")
        except Exception as e:
            print(f"[Pixabay] İndirme hatası: {e}")
        return paths

    # ─── Ana İndirme Metodu — Pexels + Pixabay birleşik ──────────────────────
    def download_stock_videos(self, query, output_dir="assets/temp_videos", count=4, orientation="portrait"):
        """Pexels ve Pixabay'dan video indirir, birleştirir ve karıştırır."""
        os.makedirs(output_dir, exist_ok=True)

        pexels_count = (count + 1) // 2
        pixabay_count = count - pexels_count

        pexels_paths = self._download_from_pexels(query, output_dir, pexels_count, orientation)
        pixabay_paths = self._download_from_pixabay(query, output_dir, pixabay_count, orientation)

        all_paths = pexels_paths + pixabay_paths
        random.shuffle(all_paths)

        if not all_paths:
            print("[MediaEngine] Her iki kaynaktan da video alınamadı!")
            return []

        if len(all_paths) < count:
            extra_needed = count - len(all_paths)
            extra = self._download_from_pexels(query, output_dir, extra_needed, orientation)
            all_paths += extra

        print(f"[MediaEngine] Toplam {len(all_paths)} klip hazır ({len(pexels_paths)} Pexels + {len(pixabay_paths)} Pixabay)")
        return all_paths[:count]

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

            # Başlık çiz (Sarı & Siyah Glow + Kalın Stroke)
            y_start = (img.height // 2) - (len(lines) * 55)
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=title_font)
                x = (img.width - (bbox[2] - bbox[0])) // 2
                
                # Kalın Stroke (Outline)
                stroke_w = 6
                for dx in range(-stroke_w, stroke_w + 1):
                    for dy in range(-stroke_w, stroke_w + 1):
                        draw.text((x + dx, y_start + dy), line, font=title_font, fill=(0, 0, 0))
                
                # Ana metin
                draw.text((x, y_start), line, font=title_font, fill=(255, 235, 0))
                y_start += 120

            # Kanal & Misyon (Altta bant şeklinde)
            footer_h = 160
            footer_bg = Image.new("RGBA", (img.width, footer_h), (0, 0, 0, 220))
            img.paste(footer_bg, (0, img.height - footer_h), footer_bg)
            
            # Kanal adı (Vurgulu Yeşil)
            cb = draw.textbbox((0, 0), channel_name, font=ch_font)
            cx = (img.width - (cb[2] - cb[0])) // 2
            draw.text((cx, img.height - 130), channel_name, font=ch_font, fill=(50, 255, 100))

            # Slogan (Parlak Beyaz)
            sb = draw.textbbox((0, 0), slogan, font=sl_font)
            sx = (img.width - (sb[2] - sb[0])) // 2
            draw.text((sx, img.height - 65), slogan.upper(), font=sl_font, fill=(255, 255, 255))

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path, "JPEG", quality=98) 
            print(f"[MediaEngine] Premium Thumbnail kaydedildi: {output_path}")
            return output_path
        except Exception as e:
            print(f"[MediaEngine] Thumbnail hatası: {e}")
            return None
