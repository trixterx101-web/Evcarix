import os
import requests
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoFileClip


class MediaEngine:
    def __init__(self):
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
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
