import os
import json
import re
from PIL import Image, ImageDraw, ImageFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
OUTPUT_DIR = "output/thumbnails"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TOPIC_STYLES = {
    "electric_vehicle":        ("#001833", "#00D4FF"),
    "artificial_intelligence": ("#0D001A", "#8B00FF"),
    "robotics":                ("#001A00", "#00FF88"),
    "battery_tech":            ("#1A0800", "#FF6B00"),
    "future_tech":             ("#0A0A1E", "#FF00FF"),
    "default":                 ("#000510", "#00D4FF"),
}

TOPIC_LABELS = {
    "electric_vehicle":        "EV DATA",
    "artificial_intelligence": "AI TECH",
    "robotics":                "ROBOTICS",
    "battery_tech":            "BATTERY",
    "future_tech":             "FUTURE TECH",
    "default":                 "EV TECH",
}

class ThumbnailGenerator:

    def __init__(self):
        self.W = 1280
        self.H = 720

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        h = hex_color.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _get_style(self, topic: str):
        return TOPIC_STYLES.get(topic, TOPIC_STYLES["default"])

    def _draw_background(self, img: Image.Image, bg_hex: str, acc_hex: str):
        draw = ImageDraw.Draw(img)
        bg   = self._hex_to_rgb(bg_hex)
        acc  = self._hex_to_rgb(acc_hex)

        # Base background
        draw.rectangle([0, 0, self.W, self.H], fill=bg)

        # Gradient from top to bottom (simulate dark gradient)
        for y in range(self.H):
            ratio = y / self.H
            r = int(bg[0] + (bg[0] * 0.3) * (1 - ratio))
            g = int(bg[1] + (bg[1] * 0.3) * (1 - ratio))
            b = int(bg[2] + (acc[2] * 0.15) * ratio)
            r = min(255, max(0, r))
            g = min(255, max(0, g))
            b = min(255, max(0, b))
            draw.line([(0, y), (self.W, y)], fill=(r, g, b))

        # Radial glow bottom center
        glow_cx = self.W // 2
        glow_cy = self.H
        for radius in range(400, 0, -20):
            alpha = int(30 * (1 - radius / 400))
            color = (acc[0], acc[1], acc[2], alpha)
            glow_img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_img)
            gd.ellipse([
                glow_cx - radius, glow_cy - radius,
                glow_cx + radius, glow_cy + radius
            ], fill=color)
            img.paste(Image.alpha_composite(
                Image.new("RGBA", img.size, (0, 0, 0, 0)),
                glow_img
            ), mask=glow_img.split()[3])

        # Left accent stripe
        draw.rectangle([0, 0, 7, self.H], fill=acc)

        return draw

    def _split_title(self, title: str) -> list:
        # Remove special chars
        title = re.sub(r"[^\w\s%\-\+\?!.,]", "", title)
        words = title.upper().split()

        # Remove filler words if too many
        fillers = {"IN", "THE", "A", "AN", "AND", "OR", "OF", "FOR", "TO", "IS", "ARE", "WAS"}
        if len(words) > 9:
            words = [w for w in words if w not in fillers]

        # Split into lines of max 3 words
        lines = []
        chunk = []
        for word in words:
            chunk.append(word)
            if len(chunk) == 3:
                lines.append(" ".join(chunk))
                chunk = []
                if len(lines) == 3:
                    break
        if chunk and len(lines) < 3:
            lines.append(" ".join(chunk))

        return lines[:3]

    def _draw_title(self, draw: ImageDraw.Draw, lines: list, acc_hex: str):
        acc = self._hex_to_rgb(acc_hex)

        sizes = [140, 110, 90]
        colors = [acc, (255, 255, 255), (220, 220, 220)]

        # Calculate total height
        total_h = 0
        fonts = []
        for i, line in enumerate(lines):
            sz = sizes[i] if i < len(sizes) else 90
            try:
                font = ImageFont.truetype(FONT_BOLD, sz)
            except:
                font = ImageFont.load_default()
            fonts.append(font)
            bbox = draw.textbbox((0, 0), line, font=font)
            total_h += (bbox[3] - bbox[1]) + 20

        # Start Y — center in upper 80% of image
        start_y = max(80, (self.H * 0.75 - total_h) // 2)

        y = start_y
        for i, line in enumerate(lines):
            font  = fonts[i]
            color = colors[i] if i < len(colors) else (255, 255, 255)
            bbox  = draw.textbbox((0, 0), line, font=font)
            w     = bbox[2] - bbox[0]
            x     = (self.W - w) // 2

            # Shadow
            draw.text((x + 5, y + 5), line, font=font, fill=(0, 0, 0))
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 180))

            # Glow for first line
            if i == 0:
                for offset in [6, 4, 2]:
                    glow_color = (
                        min(255, acc[0] + 50),
                        min(255, acc[1] + 50),
                        min(255, acc[2] + 50)
                    )
                    draw.text((x - offset, y - offset), line, font=font, fill=glow_color)
                    draw.text((x + offset, y + offset), line, font=font, fill=glow_color)

            draw.text((x, y), line, font=font, fill=color)
            bbox2 = draw.textbbox((0, 0), line, font=font)
            y += (bbox2[3] - bbox2[1]) + 24

    def _draw_bottom_bar(self, draw: ImageDraw.Draw, topic: str, acc_hex: str):
        acc   = self._hex_to_rgb(acc_hex)
        bar_y = self.H - 72

        # Bar background
        draw.rectangle([0, bar_y, self.W, self.H], fill=(0, 0, 0, 230))

        # Top border line
        draw.rectangle([0, bar_y, self.W, bar_y + 3], fill=acc)

        # Left: EVCARIX
        try:
            font_brand = ImageFont.truetype(FONT_BOLD, 34)
        except:
            font_brand = ImageFont.load_default()

        draw.text((30, bar_y + 18), "⚡ EVCARIX", font=font_brand, fill=acc)

        # Right: topic label
        try:
            font_tag = ImageFont.truetype(FONT_REG, 24)
        except:
            font_tag = ImageFont.load_default()

        label = TOPIC_LABELS.get(topic, "EV TECH")
        bbox  = draw.textbbox((0, 0), label, font=font_tag)
        w     = bbox[2] - bbox[0]
        draw.text((self.W - w - 30, bar_y + 22), label,
                  font=font_tag, fill=(160, 160, 160))

    def _draw_corners(self, draw: ImageDraw.Draw, acc_hex: str):
        acc  = self._hex_to_rgb(acc_hex)
        size = 50
        thick = 5
        pad  = 18
        bar_y = self.H - 80

        corners = [
            # top-left
            [(pad, pad, pad + size, pad + thick),
             (pad, pad, pad + thick, pad + size)],
            # top-right
            [(self.W - pad - size, pad, self.W - pad, pad + thick),
             (self.W - pad - thick, pad, self.W - pad, pad + size)],
            # bottom-left
            [(pad, bar_y - size, pad + thick, bar_y),
             (pad, bar_y - thick, pad + size, bar_y)],
            # bottom-right
            [(self.W - pad - thick, bar_y - size, self.W - pad, bar_y),
             (self.W - pad - size, bar_y - thick, self.W - pad, bar_y)],
        ]

        for rects in corners:
            for rect in rects:
                draw.rectangle(rect, fill=acc)

    def create(self, title: str, topic: str) -> str:
        try:
            bg_hex, acc_hex = self._get_style(topic)

            # RGBA for glow support
            img  = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 255))
            draw = self._draw_background(img, bg_hex, acc_hex)

            lines = self._split_title(title)
            self._draw_title(draw, lines, acc_hex)
            self._draw_bottom_bar(draw, topic, acc_hex)
            self._draw_corners(draw, acc_hex)

            # Convert to RGB for JPEG
            final = img.convert("RGB")

            safe_title = re.sub(r"[^\w]", "_", title[:30])
            out_path   = os.path.join(OUTPUT_DIR, f"thumb_{safe_title}.jpg")
            final.save(out_path, "JPEG", quality=95)
            print(f"[Thumbnail] ✅ Created: {out_path}")
            return out_path

        except Exception as e:
            print(f"[Thumbnail] ❌ create() failed: {e}")
            return None

    def upload_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        try:
            token_json  = os.getenv("YOUTUBE_TOKEN_JSON")
            secret_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")

            if not token_json or not secret_json:
                print("[Thumbnail] Missing YouTube credentials")
                return False

            token_data  = json.loads(token_json)
            secret_data = json.loads(secret_json)

            client_id     = secret_data["installed"]["client_id"]
            client_secret = secret_data["installed"]["client_secret"]

            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=["https://www.googleapis.com/auth/youtube.force-ssl"]
            )

            youtube = build("youtube", "v3", credentials=creds)
            media   = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            ).execute()

            print(f"[Thumbnail] ✅ Uploaded to YouTube: {video_id}")
            return True

        except Exception as e:
            print(f"[Thumbnail] ❌ Upload failed: {e}")
            return False


def generate_and_upload(video_id: str, title: str, topic: str) -> bool:
    gen  = ThumbnailGenerator()
    path = gen.create(title, topic)
    if path and os.path.exists(path):
        return gen.upload_thumbnail(video_id, path)
    return False
