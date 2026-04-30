import os
import re
import random
import requests
import urllib.parse
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

    # Kelimeler EV ile ilgisi olmayan stok videolari elemek icin
    _IRRELEVANT_TAGS = {
        "fireplace", "fire", "flame", "christmas", "xmas", "flower", "flowers",
        "nature", "forest", "mountain", "beach", "ocean", "sea", "cooking",
        "food", "kitchen", "coffee", "cat", "dog", "animal", "baby", "wedding",
        "yoga", "meditation", "fitness", "gym", "rain", "snow", "storm",
        "abstract", "background", "texture", "pattern", "paint", "art",
        "waterfall", "sunrise", "timelapse", "stars", "space", "sky",
    }
    _RELEVANT_TAGS = {
        "electric", "ev", "tesla", "battery", "charging", "car", "vehicle",
        "automobile", "auto", "automotive", "transport", "technology", "drive",
        "highway", "road", "traffic", "city", "urban", "motor", "energy",
        "green", "eco", "future", "innovation", "speed", "dashboard",
    }

    def _is_ev_related(self, video_data):
        """Pexels video tags'ine bakarak EV ile ilgili olup olmadigini kontrol eder."""
        tags = video_data.get("tags", []) or []
        tag_set = {t.lower() for t in tags if isinstance(t, str)}
        # Ilgisiz tag varsa reddet
        if tag_set & self._IRRELEVANT_TAGS:
            return False
        # En az bir EV-ilgili tag varsa kabul et
        if tag_set & self._RELEVANT_TAGS:
            return True
        # User adi bazen ipucu verir
        user_name = (video_data.get("user", {}) or {}).get("name", "").lower()
        if any(w in user_name for w in ["ev", "tesla", "electric", "auto", "car"]):
            return True
        # Varsayilan olarak kabul et (cok agresif filtreleme yapma)
        return True

    def _get_professional_query(self, topic, category=None):
        """Her çalışmada farklı bir arama sorgusu üretir — kategoriye gore EV odakli."""
        clean_topic = topic.split(':')[0].split('?')[0].strip() if ':' in topic or '?' in topic else topic
        clean_topic = clean_topic.replace("electric", "").replace("car", "").strip()

        # Kategoriye gore spesifik EV arama stratejileri
        category_strategies = {
            "battery_science": [
                "lithium battery cell technology laboratory close up",
                "EV battery pack assembly manufacturing 4k",
                "battery chemistry research scientist lab",
                "solid state battery futuristic technology",
                "battery management system BMS circuit board",
            ],
            "range_tests": [
                "electric car driving highway aerial view 4k",
                "Tesla driving on road winter snow",
                "EV dashboard speedometer range display",
                "electric vehicle on open road cinematic",
                "car driving city night lights 4k",
            ],
            "charging": [
                "electric car charging station night 4k",
                "EV fast charging plug cable close up",
                "Tesla supercharger station cars charging",
                "charging station technology futuristic",
                "electric vehicle charging port detail",
            ],
            "cost_ownership": [
                "electric car showroom dealership interior",
                "EV repair shop mechanic working",
                "car insurance documents calculator business",
                "money savings finance calculator digital",
                "family buying car dealer handshake",
            ],
            "comparisons": [
                "two electric cars side by side showroom",
                "car comparison test track racing",
                "EV lineup multiple cars parked",
                "car specifications chart display screen",
                "electric vehicles parked row modern",
            ],
            "market_data": [
                "global business data analytics screen",
                "stock market chart graph rising",
                "world map digital connections network",
                "factory production line cars manufacturing",
                "business meeting presentation data charts",
            ],
            "infrastructure": [
                "electric car charging network city",
                "power grid electricity transmission tower",
                "solar panels renewable energy field",
                "smart city technology traffic lights",
                "apartment building parking garage night",
            ],
            "education": [
                "electric motor engine technology close up",
                "heat pump HVAC system technology",
                "car aerodynamics wind tunnel test",
                "thermal imaging heat visualization technology",
                "engineering blueprint technical drawing",
            ],
            "interactive_tools": [
                "smartphone calculator app close up",
                "digital screen data visualization charts",
                "mobile app interface modern design",
                "computer screen analytics dashboard",
                "technology user interface futuristic",
            ],
        }

        if category and category in category_strategies:
            return random.choice(category_strategies[category])

        # Varsayilan genel EV sorgulari
        strategies = [
            f"{clean_topic} EV driving 4k",
            f"Tesla {clean_topic} exterior 4k",
            f"electric vehicle {clean_topic} test",
            f"EV battery {clean_topic} technology",
            f"electric car charging station 4k",
            f"Tesla Model 3 {clean_topic} driving",
            f"EV dashboard display technology",
            f"electric vehicle production line",
            f"lithium battery cell technology",
            f"BYD electric car driving",
        ]
        return random.choice(strategies)

    # ─── Pexels Video İndirme ──────────────────────────────────────────────────
    def _download_from_pexels(self, query, output_dir, count, orientation, category=None):
        """Pexels API'den rastgele sayfa ve sorgu ile video indirir."""
        if not self.pexels_api_key:
            print("[Pexels] API key bulunamadı, atlanıyor.")
            return []

        optimized_query = self._get_professional_query(query, category=category)
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
                for i, video_data in enumerate(videos):
                    if len(paths) >= count:
                        break
                    # EV ile ilgisi olmayan videolari atla (somin, cicek, doga...)
                    if not self._is_ev_related(video_data):
                        tags = video_data.get("tags", [])
                        print(f"[Pexels] ⚠️ EV ile ilgisiz video atlandi (tags: {tags[:3]})")
                        continue
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
    def _download_from_pixabay(self, query, output_dir, count, orientation, category=None):
        """Pixabay API'den video indirir. Ücretsiz & ticari kullanım serbest."""
        if not self.pixabay_api_key:
            print("[Pixabay] API key bulunamadı, atlanıyor.")
            return []

        pixabay_queries_map = {
            "battery_science": ["lithium battery cell", "battery laboratory", "battery technology", "battery factory production"],
            "range_tests": ["electric car highway driving", "winter road driving", "dashboard speedometer", "electric vehicle test"],
            "charging": ["EV charging station", "Tesla supercharger", "electric car charging", "DC fast charging"],
            "cost_ownership": ["car dealership", "car insurance", "money calculator", "business finance"],
            "comparisons": ["electric vehicles comparison", "car showroom", "car comparison test", "cars parked"],
            "market_data": ["business analytics", "stock market", "factory production", "global network"],
            "infrastructure": ["power grid", "solar panels", "smart city", "charging network"],
            "education": ["electric motor", "heat pump", "engineering technology", "wind tunnel"],
            "interactive_tools": ["smartphone app", "data visualization", "digital screen", "technology interface"],
        }
        default_queries = [
            "electric car",
            "EV charging",
            "electric vehicle",
            "tesla car",
            "EV battery technology",
            "electric car charging station",
            "EV production factory",
            "electric car dashboard",
        ]
        pixabay_queries = pixabay_queries_map.get(category, default_queries)
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
    def download_stock_videos(self, query, output_dir="assets/temp_videos", count=4, orientation="portrait", category=None):
        """Pexels ve Pixabay'dan video indirir, birleştirir ve karıştırır."""
        os.makedirs(output_dir, exist_ok=True)

        pexels_count = (count + 1) // 2
        pixabay_count = count - pexels_count

        pexels_paths = self._download_from_pexels(query, output_dir, pexels_count, orientation, category=category)
        pixabay_paths = self._download_from_pixabay(query, output_dir, pixabay_count, orientation, category=category)

        all_paths = pexels_paths + pixabay_paths
        random.shuffle(all_paths)

        if not all_paths:
            print("[MediaEngine] Her iki kaynaktan da video alınamadı!")
            return []

        if len(all_paths) < count:
            extra_needed = count - len(all_paths)
            extra = self._download_from_pexels(query, output_dir, extra_needed, orientation, category=category)
            all_paths += extra

        print(f"[MediaEngine] Toplam {len(all_paths)} klip hazır ({len(pexels_paths)} Pexels + {len(pixabay_paths)} Pixabay)")
        return all_paths[:count]

    def generate_ai_fallback_images(self, topic, count=3, output_dir="assets/ai_fallback"):
        """Stok video bulunamazsa Pollinations.ai'dan EV temalı görüntü üretir."""
        os.makedirs(output_dir, exist_ok=True)
        paths = []
        prompts = [
            f"futuristic electric car driving on highway at sunset, cinematic 4k, dramatic lighting, no text, no watermark, {topic}",
            f"EV battery technology close up, laboratory, lithium cells, futuristic, blue glow, high detail, no text, no watermark",
            f"electric vehicle charging station at night, city lights, cyberpunk aesthetic, cinematic, no text, no watermark",
            f"Tesla or modern EV dashboard display, holographic interface, technology, dark background, no text, no watermark",
            f"aerial view of electric car on winding road, mountains, golden hour, cinematic, no text, no watermark",
        ]
        for i in range(min(count, len(prompts))):
            prompt = prompts[i]
            encoded = urllib.parse.quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&seed={random.randint(1,999999)}&nologo=true&negative=blurry,text,watermark,low%20quality"
            out_path = os.path.join(output_dir, f"ai_fallback_{i}.jpg")
            try:
                print(f"[Pollinations] AI görüntü üretiliyor ({i+1}/{count})...")
                r = requests.get(url, timeout=60)
                if r.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(r.content)
                    paths.append(out_path)
                    print(f"[Pollinations] ✅ Kaydedildi: {out_path}")
                else:
                    print(f"[Pollinations] HTTP {r.status_code}")
            except Exception as e:
                print(f"[Pollinations] Hata: {e}")
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
