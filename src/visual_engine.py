import os
import random
import requests
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

class VisualEngine:
    def __init__(self, assets_dir="assets/visuals"):
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.fonts_dir = Path("fonts")
        self.fonts_dir.mkdir(exist_ok=True)
        
        # Default colors (Modern Dark Theme)
        self.bg_color = (15, 15, 20)
        self.accent_color = (50, 255, 100) # Evcarix Green
        self.text_color = (255, 255, 255)
        self.secondary_text = (180, 180, 190)

    def _get_font(self, size=40, bold=False):
        # Try to find a nice font, fallback to default
        font_names = ["Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf", "arial.ttf", "DejaVuSans.ttf"]
        for fn in font_names:
            path = self.fonts_dir / fn
            if path.exists():
                return ImageFont.truetype(str(path), size)
        return ImageFont.load_default()

    # ── INFOGRAPHIC / DATA CARD GENERATION ────────────────────────────
    def create_data_card(self, title, points, output_path=None):
        """
        Creates a sleek dark-mode data card for stats/info.
        points: list of tuples [("Label", "Value"), ...]
        """
        width, height = 1080, 1920 # Default to Portrait (Shorts)
        # If long video requested, we might need 1920x1080
        # For now, let's detect from name or assume portrait for diversification
        
        img = Image.new("RGB", (width, height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Add a subtle gradient or glow
        for i in range(height):
            r = int(15 + (i / height) * 10)
            g = int(15 + (i / height) * 15)
            b = int(20 + (i / height) * 20)
            draw.line([(0, i), (width, i)], fill=(r, g, b))

        # Title
        font_title = self._get_font(70, bold=True)
        draw.text((80, 200), title.upper(), font=font_title, fill=self.accent_color)
        
        # Decorative Line
        draw.rectangle([80, 290, 300, 300], fill=self.accent_color)
        
        # Data Points
        y_pos = 450
        font_label = self._get_font(45)
        font_value = self._get_font(55, bold=True)
        
        for label, value in points:
            # Box for each point
            draw.rectangle([80, y_pos, width-80, y_pos+160], fill=(30, 30, 40))
            draw.text((120, y_pos + 30), label, font=font_label, fill=self.secondary_text)
            draw.text((120, y_pos + 85), value, font=font_value, fill=self.text_color)
            y_pos += 200
            
        # Branding
        font_brand = self._get_font(35)
        draw.text((width//2 - 60, height - 150), "EVCARIX", font=font_brand, fill=(100, 100, 110))

        if not output_path:
            output_path = self.assets_dir / f"card_{int(random.random()*1000)}.png"
        
        img.save(output_path)
        return str(output_path)

    # ── AI IMAGE GENERATION (POLLINATIONS - FREE) ─────────────────────
    def generate_ai_image(self, prompt, width=1080, height=1920):
        """Fetches a free AI image from Pollinations.ai."""
        encoded_prompt = requests.utils.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true&seed={random.randint(1,99999)}"
        
        out_path = self.assets_dir / f"ai_img_{hash(prompt) % 10000}.jpg"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(r.content)
                return str(out_path)
        except Exception as e:
            print(f"[VisualEngine] AI Image Error: {e}")
        return None

    # ── IMAGE TO VIDEO (KEN BURNS EFFECT) ─────────────────────────────
    def image_to_video(self, image_path, output_path, duration=5, orientation="portrait"):
        """Converts a static image to a 5s video with a smooth zoom effect."""
        if not os.path.exists(image_path):
            return None
            
        # Determine dimensions
        if orientation == "portrait":
            w, h = 1080, 1920
        else:
            w, h = 1920, 1080

        # FFmpeg command for smooth zoom (Ken Burns)
        # zoompan filter: zoom in from 1.0 to 1.1 over the duration
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", f"zoompan=z='min(zoom+0.0005,1.1)':d={duration*25}:s={w}x{h}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except Exception as e:
            print(f"[VisualEngine] Ken Burns Error: {e}")
            return None

    # ── WIKIMEDIA COMMONS SEARCH ──────────────────────────────────────
    def search_wikimedia(self, query, count=3):
        """Searches Wikimedia Commons for CC images."""
        url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap|image {query}",
            "gsrnamespace": 6,
            "gsrlimit": count,
            "prop": "imageinfo",
            "iiprop": "url"
        }
        
        paths = []
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                pages = r.json().get("query", {}).get("pages", {})
                for page_id in pages:
                    info = pages[page_id].get("imageinfo", [{}])[0]
                    img_url = info.get("url")
                    if img_url:
                        # Download it
                        ext = img_url.split(".")[-1].lower()
                        if ext not in ["jpg", "jpeg", "png"]: continue
                        
                        out = self.assets_dir / f"wiki_{page_id}.{ext}"
                        dl = requests.get(img_url, timeout=20)
                        if dl.status_code == 200:
                            with open(out, "wb") as f:
                                f.write(dl.content)
                            paths.append(str(out))
        except Exception as e:
            print(f"[VisualEngine] Wikimedia Error: {e}")
        return paths

# ── TEST ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ve = VisualEngine()
    # Test Data Card
    card = ve.create_data_card("TESLA MODEL 3", [("Range", "629 km"), ("0-100", "4.4s"), ("Price", "$42,000")])
    print(f"Card created: {card}")
    
    # Test AI Image to Video
    img = ve.generate_ai_image("futuristic electric car battery cell glowing blue")
    if img:
        vid = ve.image_to_video(img, "assets/visuals/test_ai_video.mp4")
        print(f"AI Video created: {vid}")
