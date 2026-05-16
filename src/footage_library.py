import os
import json
import random
import subprocess
import logging
import hashlib
import requests
import re
from pathlib import Path

logger = logging.getLogger("FootageLibrary")

QUERY_POOL = {
    "electric_vehicle": [
        "electric car", "EV charging", "electric vehicle review",
        "tesla review", "electric car test drive", "EV range test",
        "highway driving", "night driving rain", "city traffic timelapse",
        "car dashboard interior", "road trip sunset", "tunnel driving",
        "car engine technology", "automotive engineering", "motor test",
        "charging cable plug", "battery pack", "power grid",
        "renewable energy car", "zero emission vehicle", "clean transport",
        "electric motor spinning", "drive test circuit", "acceleration test",
        "empty highway aerial", "city street cars", "parking lot cars",
        "traffic light intersection", "motorway timelapse", "car headlights night"
    ],
    "artificial_intelligence": [
        "machine learning explained", "AI technology demo",
        "neural network visualization", "data science tutorial",
        "computer screen code", "server room data center",
        "programmer coding", "software development",
        "digital screen technology", "futuristic interface",
        "binary code", "algorithm visualization",
        "typing keyboard closeup", "multiple monitors setup",
        "tech startup office", "innovation lab",
        "brain scan neuroscience", "network connections",
        "cloud computing", "cybersecurity"
    ],
    "robotics": [
        "robot technology", "industrial robot arm",
        "humanoid robot", "automation factory",
        "factory assembly line", "manufacturing plant",
        "welding sparks factory", "car manufacturing robot",
        "precision engineering", "CNC machine",
        "3D printer working", "laboratory technology",
        "mechanical engineering", "gear mechanism",
        "drone flying", "autonomous vehicle sensor"
    ],
    "battery_tech": [
        "battery technology", "solid state battery",
        "lithium battery", "energy storage",
        "solar panel installation", "wind turbine farm",
        "power plant aerial", "electricity grid",
        "laboratory chemistry", "scientific research",
        "mineral mining aerial", "semiconductor factory",
        "circuit board closeup", "electronic component",
        "energy cell microscope", "charging device"
    ],
    "future_tech": [
        "future technology", "innovation lab",
        "smart city", "space technology",
        "city aerial night lights", "skyscraper timelapse",
        "satellite orbit earth", "space station",
        "quantum physics lab", "particle accelerator",
        "nanotechnology research", "biotech laboratory",
        "augmented reality demo", "VR headset technology",
        "hyperloop concept", "autonomous drone fleet",
        "underwater technology", "deep sea research"
    ]
}

NASA_QUERIES = {
    "electric_vehicle": ["electric vehicle technology", "clean energy transport", "battery research"],
    "artificial_intelligence": ["artificial intelligence", "machine learning space", "autonomous systems"],
    "robotics": ["robotics", "robonaut", "autonomous robot", "mars rover"],
    "battery_tech": ["battery research", "energy storage", "solar power", "fuel cell"],
    "future_tech": ["future technology", "space exploration", "innovation", "orbital"],
}

ARCHIVE_COLLECTIONS = [
    "prelinger", "computersandtech", "nasa", "prelinger_auxiliary",
    "ephemera", "open_source_movies", "stock_footage", "Transportation",
    "SciFi_Horror", "feature_films"
]

class FootageLibrary:
    def __init__(self):
        self.output_dir = "assets/footage"
        os.makedirs(self.output_dir, exist_ok=True)
        self.used_clips_file = "used_clips.json"
        self.used_ids = self._load_used()

    def _load_used(self) -> set:
        if os.path.exists(self.used_clips_file):
            try:
                with open(self.used_clips_file, "r") as f:
                    return set(json.load(f).get("ids", []))
            except: pass
        return set()

    def _mark_used(self, file_path: str):
        try:
            with open(file_path, "rb") as f:
                clip_id = hashlib.md5(f.read(8192)).hexdigest()
            self.used_ids.add(clip_id)
            with open(self.used_clips_file, "w") as f:
                json.dump({"ids": list(self.used_ids)}, f)
        except: pass

    def get_fresh_clips(self, topic: str, count: int = 1, format: str = "shorts") -> list[str]:
        clips = []
        sources = [
            self._fetch_archive_org,
            self._fetch_nasa,
            self._fetch_youtube_cc,
            self._fetch_pexels,
            self._fetch_pixabay,
            self._fetch_wikimedia,
            self._fetch_coverr
        ]
        random.shuffle(sources)
        
        for source in sources:
            if len(clips) >= count: break
            try:
                new_clips = source(topic, count - len(clips), format)
                for c in new_clips:
                    if c and os.path.exists(c):
                        clips.append(c)
                        self._mark_used(c)
            except Exception as e:
                logger.error(f"Source {source.__name__} failed: {e}")
                
        return clips[:count]

    def _fetch_youtube_cc(self, topic: str, count: int, format: str) -> list[str]:
        from googleapiclient.discovery import build
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key: return []
        
        queries = QUERY_POOL.get(topic, QUERY_POOL["future_tech"])
        query = random.choice(queries)
        
        try:
            youtube = build("youtube", "v3", developerKey=api_key)
            request = youtube.search().list(
                part="snippet", q=query, type="video",
                videoLicense="creativeCommon", videoDuration="short",
                maxResults=count * 3, pageToken=None
            )
            res = request.execute()
            results = []
            for item in res.get("items", []):
                vid_id = item["id"]["videoId"]
                out = os.path.join(self.output_dir, f"yt_{vid_id}.mp4")
                if self._download_yt(vid_id, out):
                    results.append(out)
                if len(results) >= count: break
            return results
        except: return []

    def _download_yt(self, vid_id: str, out: str) -> bool:
        if os.path.exists(out): return True
        cmd = ["yt-dlp", "--format", "bestvideo[height<=1080][ext=mp4]", "--no-audio", "--output", out, f"https://youtube.com/watch?v={vid_id}"]
        return subprocess.run(cmd, capture_output=True).returncode == 0

    def _fetch_archive_org(self, topic: str, count: int, format: str) -> list[str]:
        collection = random.choice(ARCHIVE_COLLECTIONS)
        query = random.choice(QUERY_POOL.get(topic, ["technology"]))
        url = "https://advancedsearch.php" # Fake URL for logic, use archive.org
        params = {
            "q": f"({query}) AND mediatype:movies AND collection:{collection}",
            "fl[]": ["identifier", "format"], "rows": count * 5, "page": random.randint(1, 20), "output": "json"
        }
        try:
            r = requests.get("https://archive.org/advancedsearch.php", params=params, timeout=15)
            data = r.json().get("response", {}).get("docs", [])
            results = []
            for item in data:
                ident = item["identifier"]
                # Get files list
                f_url = f"https://archive.org/metadata/{ident}"
                fr = requests.get(f_url, timeout=10).json()
                def _safe_size(f):
                    s = f.get("size") or 0
                    try: return int(s)
                    except (ValueError, TypeError): return 0
                mp4s = [f for f in fr.get("files", []) if f["name"].endswith(".mp4") and _safe_size(f) < 50000000]
                if mp4s:
                    best = sorted(mp4s, key=lambda x: _safe_size(x), reverse=True)[0]
                    dl_url = f"https://archive.org/download/{ident}/{best['name']}"
                    out = os.path.join(self.output_dir, f"archive_{ident}.mp4")
                    if self._download_direct(dl_url, out):
                        results.append(out)
                if len(results) >= count: break
            return results
        except: return []

    def _fetch_nasa(self, topic: str, count: int, format: str) -> list[str]:
        query = random.choice(NASA_QUERIES.get(topic, ["technology"]))
        try:
            r = requests.get("https://images-api.nasa.gov/search", params={"q": query, "media_type": "video", "page": random.randint(1, 5)}, timeout=15)
            items = r.json().get("collection", {}).get("items", [])
            results = []
            for item in items:
                collection_url = item["href"]
                cr = requests.get(collection_url, timeout=10).json()
                mp4s = [u for u in cr if u.endswith("~orig.mp4") or u.endswith("~medium.mp4")]
                if mp4s:
                    out = os.path.join(self.output_dir, f"nasa_{item['data'][0]['nasa_id']}.mp4")
                    if self._download_direct(mp4s[0], out):
                        results.append(out)
                if len(results) >= count: break
            return results
        except: return []

    def _fetch_pexels(self, topic: str, count: int, format: str) -> list[str]:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key: return []
        query = random.choice(QUERY_POOL.get(topic, ["technology"]))
        orientation = "portrait" if format == "shorts" else "landscape"
        url = f"https://api.pexels.com/videos/search?query={query}&per_page=10&orientation={orientation}&page={random.randint(1,10)}"
        try:
            r = requests.get(url, headers={"Authorization": api_key}, timeout=15)
            videos = r.json().get("videos", [])
            results = []
            for v in videos:
                def _safe_width(f):
                    try: return int(f.get("width") or 0)
                    except (ValueError, TypeError): return 0
                files = [f for f in v["video_files"] if _safe_width(f) >= 720]
                if files:
                    out = os.path.join(self.output_dir, f"pexels_{v['id']}.mp4")
                    if self._download_direct(files[0]["link"], out):
                        results.append(out)
                if len(results) >= count: break
            return results
        except: return []

    def _fetch_pixabay(self, topic: str, count: int, format: str) -> list[str]:
        api_key = os.getenv("PIXABAY_API_KEY")
        if not api_key: return []
        query = random.choice(QUERY_POOL.get(topic, ["technology"]))
        url = f"https://pixabay.com/api/videos/?key={api_key}&q={query}&per_page=10&page={random.randint(1,10)}"
        try:
            r = requests.get(url, timeout=15)
            videos = r.json().get("hits", [])
            results = []
            for v in videos:
                # Pick large/medium
                f = v["videos"].get("large") or v["videos"].get("medium")
                if f:
                    out = os.path.join(self.output_dir, f"pixabay_{v['id']}.mp4")
                    if self._download_direct(f["url"], out):
                        results.append(out)
                if len(results) >= count: break
            return results
        except: return []

    def _fetch_wikimedia(self, topic: str, count: int, format: str) -> list[str]:
        query = random.choice(QUERY_POOL.get(topic, ["technology"]))
        params = {"action": "query", "list": "search", "srsearch": f"{query} filetype:video", "srnamespace": "6", "srlimit": count*3, "format": "json"}
        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php", params=params, timeout=15)
            hits = r.json().get("query", {}).get("search", [])
            results = []
            for hit in hits:
                title = hit["title"]
                # Get file info
                info_url = f"https://commons.wikimedia.org/w/api.php?action=query&titles={title}&prop=imageinfo&iiprop=url&format=json"
                ir = requests.get(info_url, timeout=10).json()
                pages = ir.get("query", {}).get("pages", {})
                for p in pages.values():
                    url = p.get("imageinfo", [{}])[0].get("url")
                    if url and url.endswith(".mp4"):
                        out = os.path.join(self.output_dir, f"wiki_{hit['pageid']}.mp4")
                        if self._download_direct(url, out):
                            results.append(out)
                if len(results) >= count: break
            return results
        except: return []

    def _fetch_coverr(self, topic: str, count: int, format: str) -> list[str]:
        query = random.choice(QUERY_POOL.get(topic, ["technology"]))
        try:
            r = requests.get("https://coverr.co/api/videos/search", params={"query": query, "per_page": 10, "page": random.randint(1,5)}, timeout=15)
            videos = r.json().get("videos", [])
            results = []
            for v in videos:
                dl = v.get("urls", {}).get("mp4")
                if dl:
                    out = os.path.join(self.output_dir, f"coverr_{v['id']}.mp4")
                    if self._download_direct(dl, out):
                        results.append(out)
                if len(results) >= count: break
            return results
        except: return []

    def _download_direct(self, url: str, out: str) -> bool:
        if os.path.exists(out): return True
        try:
            r = requests.get(url, timeout=30, stream=True)
            if r.status_code == 200:
                with open(out, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except: pass
        return False
