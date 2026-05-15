"""
thumbnail_generator.py — Evcarix Global English
Automatically extracts a frame from the video and overlays a high-impact title.
"""
import os
import cv2
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path

OUTPUT_DIR = "assets/thumbnails"

class ThumbnailGenerator:
    def __init__(self, font_path="assets/fonts/Inter-Bold.ttf"):
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        self.font_path = font_path if os.path.exists(font_path) else None

    def generate(self, video_path: str, title: str, output_name: str = "thumb.jpg") -> str:
        """Video'dan kare çeker, efekt uygular ve başlık basar."""
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Videonun %30 civarındaki bir kareyi al (genelde en iyi kareler oradadır)
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(total_frames * 0.3))
            ret, frame = cap.read()
            cap.release()
            
            if not ret: return ""

            # BGR to RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img = img.resize((1280, 720)) # Standard YouTube Thumb Size

            # Efektler: Hafif Kontrast ve Parlaklık
            from PIL import ImageEnhance
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Brightness(img).enhance(1.1)

            draw = ImageDraw.Draw(img)
            
            # Yazı Fontu (Font yoksa default kullan)
            font_size = 80
            if self.font_path:
                font = ImageFont.truetype(self.font_path, font_size)
            else:
                font = ImageFont.load_default()

            # Başlığı böl (max 2-3 kelime per line)
            words = title.upper().split()
            lines = [" ".join(words[i:i+2]) for i in range(0, len(words), 2)]
            
            # Yazı Arka Planı (Hafif karartma)
            overlay = Image.new('RGBA', img.size, (0,0,0,0))
            draw_ov = ImageDraw.Draw(overlay)
            
            y_text = 150
            for line in lines[:3]:
                # Draw black shadow/outline
                for offset in [(2,2), (-2,-2), (2,-2), (-2,2)]:
                    draw_ov.text((100+offset[0], y_text+offset[1]), line, font=font, fill=(0,0,0,200))
                
                # Draw main yellow text (High visibility)
                draw_ov.text((100, y_text), line, font=font, fill=(255, 230, 0, 255))
                y_text += 100

            img = Image.alpha_composite(img.convert('RGBA'), overlay)
            
            final_path = os.path.join(OUTPUT_DIR, output_name)
            img.convert('RGB').save(final_path, "JPEG", quality=95)
            return final_path
        except Exception as e:
            print(f"Thumbnail Error: {e}")
            return ""
