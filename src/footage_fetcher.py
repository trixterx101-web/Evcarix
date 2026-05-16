import os
import random
import subprocess
import logging
import requests
from pathlib import Path

logger = logging.getLogger("FootageFetcher")

YOUTUBE_CC_QUERIES = {
    "electric_vehicle": [
        "electric car review", "EV test drive", "electric vehicle explained",
        "Tesla review", "electric car charging", "EV range test"
    ],
    "artificial_intelligence": [
        "artificial intelligence explained", "machine learning tutorial",
        "AI technology", "neural network explained", "deep learning"
    ],
    "robotics": [
        "robot technology", "humanoid robot", "industrial automation",
        "Boston Dynamics robot", "robot explained"
    ],
    "battery_tech": [
        "battery technology explained", "solid state battery",
        "EV battery test", "lithium battery", "battery breakthrough"
    ],
    "future_tech": [
        "future technology", "tech innovation", "emerging technology",
        "quantum computing explained", "space technology"
    ],
    "default": ["technology", "innovation", "science", "future"]
}

class FootageFetcher:
    def __init__(self):
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_api_key = os.getenv("PIXABAY_API_KEY")
        self.output_dir = "assets/footage"
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_youtube_cc(self, query: str, count: int = 5) -> list[dict]:
        """Search YouTube for Creative Commons licensed videos only."""
        if not self.youtube_api_key:
            logger.error("[FootageFetcher] YOUTUBE_API_KEY missing")
            return []

        try:
            from googleapiclient.discovery import build
            youtube = build(
                "youtube", "v3",
                developerKey=self.youtube_api_key
            )
            
            request = youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                videoLicense="creativeCommon",
                videoDuration="short",
                maxResults=count,
                relevanceLanguage="en",
                safeSearch="strict"
            )
            results = request.execute()
            
            videos = []
            for item in results.get("items", []):
                videos.append({
                    "id": item["id"]["videoId"],
                    "title": item["snippet"]["title"]
                })
            return videos
        except Exception as e:
            logger.error(f"[FootageFetcher] YouTube API error: {e}")
            return []

    def download_video_only(self, video_id: str, output_path: str) -> str | None:
        """Download video WITHOUT audio using yt-dlp."""
        cmd = [
            "yt-dlp",
            "--format", "bestvideo[height<=1080][ext=mp4]/bestvideo[height<=1080]",
            "--no-audio",
            "--output", output_path,
            "--no-playlist",
            "--max-filesize", "100M",
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
            logger.error(f"[FootageFetcher] yt-dlp error: {result.stderr[-200:]}")
        except Exception as e:
            logger.error(f"[FootageFetcher] Download failed: {e}")
        return None

    def fetch_pexels(self, query: str, format: str = "shorts") -> str | None:
        """Fallback to Pexels."""
        if not self.pexels_api_key: return None
        orientation = "portrait" if format == "shorts" else "landscape"
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=5&orientation={orientation}"
        headers = {"Authorization": self.pexels_api_key}
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                videos = r.json().get("videos", [])
                if videos:
                    v = random.choice(videos)
                    files = [f for f in v["video_files"] if f["width"] >= 720]
                    if files:
                        f = files[0]
                        out = os.path.join(self.output_dir, f"pexels_{v['id']}.mp4")
                        resp = requests.get(f["link"], timeout=30)
                        with open(out, "wb") as file: file.write(resp.content)
                        return out
        except: pass
        return None

    def get_footage(self, topic_key: str, query: str, format: str = "shorts") -> str | None:
        """Main entry point to get a high-quality video clip."""
        yt_queries = YOUTUBE_CC_QUERIES.get(topic_key, YOUTUBE_CC_QUERIES["default"])
        search_query = f"{query} {random.choice(yt_queries)}"
        
        logger.info(f"[FootageFetcher] Searching YouTube CC for: {search_query}")
        yt_list = self.fetch_youtube_cc(search_query)
        if yt_list:
            vid = random.choice(yt_list)
            out_path = os.path.join(self.output_dir, f"yt_{vid['id']}.mp4")
            if os.path.exists(out_path): return out_path
            res = self.download_video_only(vid["id"], out_path)
            if res: return res

        logger.info(f"[FootageFetcher] Falling back to Pexels for: {query}")
        res = self.fetch_pexels(query, format)
        if res: return res
        
        return None
