import os
import requests
import random
import logging
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import quote

logger = logging.getLogger("FreeMediaAggregator")

class FreeMediaAggregator:
    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.license_log = "license_log.json"
        self.temp_dir = "assets/temp_videos"
        os.makedirs(self.temp_dir, exist_ok=True)

    def log_license(self, file_path, source, license_type, author="Unknown"):
        try:
            log_data = {}
            if os.path.exists(self.license_log):
                with open(self.license_log, "r") as f:
                    log_data = json.load(f)
            log_data[os.path.basename(file_path)] = {
                "source": source,
                "license": license_type,
                "author": author,
                "timestamp": time.time()
            }
            with open(self.license_log, "w") as f:
                json.dump(log_data, f, indent=4)
        except Exception as e:
            logger.error(f"License logging failed: {e}")

    def fetch_pexels(self, query, count=5, orientation="portrait"):
        if not self.pexels_key: return []
        logger.info(f"[Aggregator] Fetching {count} videos from Pexels for: {query}")
        url = f"https://api.pexels.com/videos/search?query={quote(query)}&per_page={count*2}&orientation={orientation}"
        headers = {"Authorization": self.pexels_key}
        try:
            r = requests.get(url, headers=headers, timeout=15)
            data = r.json()
            results = []
            for v in data.get("videos", []):
                v_url = None
                # Try to get HD first
                for f in v.get("video_files", []):
                    if f.get("quality") == "hd":
                        v_url = f.get("link")
                        break
                if not v_url and v.get("video_files"):
                    v_url = v["video_files"][0]["link"]
                
                if v_url:
                    results.append({
                        "url": v_url, 
                        "source": "Pexels", 
                        "license": "Pexels License", 
                        "author": v.get("user", {}).get("name", "Unknown")
                    })
            return results[:count]
        except Exception as e:
            logger.error(f"Pexels fetch failed: {e}")
            return []

    def fetch_pixabay(self, query, count=5, orientation="vertical"):
        if not self.pixabay_key: return []
        logger.info(f"[Aggregator] Fetching {count} videos from Pixabay for: {query}")
        # orientation in pixabay is "all", "horizontal", "vertical"
        url = f"https://pixabay.com/api/videos/?key={self.pixabay_key}&q={quote(query)}&per_page={count*2}&orientation={orientation}"
        try:
            r = requests.get(url, timeout=15)
            data = r.json()
            results = []
            for v in data.get("hits", []):
                v_url = v.get("videos", {}).get("medium", {}).get("url")
                if v_url:
                    results.append({
                        "url": v_url, 
                        "source": "Pixabay", 
                        "license": "Pixabay License", 
                        "author": v.get("user", "Unknown")
                    })
            return results[:count]
        except Exception as e:
            logger.error(f"Pixabay fetch failed: {e}")
            return []

    def fetch_nasa(self, query, count=3):
        logger.info(f"[Aggregator] Fetching {count} videos from NASA for: {query}")
        url = f"https://images-api.nasa.gov/search?q={quote(query)}&media_type=video"
        try:
            r = requests.get(url, timeout=15).json()
            results = []
            items = r.get("collection", {}).get("items", [])
            for item in items:
                try:
                    nasa_id = item['data'][0]['nasa_id']
                    asset_url = f"https://images-api.nasa.gov/asset/{nasa_id}"
                    v_data = requests.get(asset_url, timeout=10).json()
                    # Find highest quality mp4
                    mp4s = [v["href"] for v in v_data.get("collection", {}).get("items", []) if v["href"].endswith("~medium.mp4") or v["href"].endswith("~orig.mp4")]
                    if mp4s:
                        results.append({
                            "url": mp4s[0], 
                            "source": "NASA", 
                            "license": "Public Domain", 
                            "author": "NASA"
                        })
                except: continue
                if len(results) >= count: break
            return results
        except Exception as e:
            logger.error(f"NASA fetch failed: {e}")
            return []

    def fetch_mixkit(self, query, count=3):
        # Mixkit scraping (Publicly accessible search)
        logger.info(f"[Aggregator] Scraping Mixkit for: {query}")
        url = f"https://mixkit.co/free-stock-video/{quote(query).replace('%20', '-')}/"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            # This is a bit fragile as it depends on their DOM
            video_nodes = soup.find_all('video')
            results = []
            for node in video_nodes:
                src = node.get('src')
                if src and src.startswith('http'):
                    results.append({
                        "url": src,
                        "source": "Mixkit",
                        "license": "Mixkit License (Free)",
                        "author": "Mixkit"
                    })
                if len(results) >= count: break
            return results
        except Exception as e:
            logger.error(f"Mixkit scraping failed: {e}")
            return []

    async def get_all_media(self, query, count=15, video_type="short"):
        """Exhaustive sequential fetching from multiple free sources."""
        orientation_pexels = "portrait" if video_type == "short" else "landscape"
        orientation_pixabay = "vertical" if video_type == "short" else "horizontal"
        
        sources = [
            lambda q, c: self.fetch_pexels(q, c, orientation_pexels),
            lambda q, c: self.fetch_pixabay(q, c, orientation_pixabay),
            lambda q, c: self.fetch_nasa(q, c),
            lambda q, c: self.fetch_mixkit(q, c),
        ]
        
        all_meta = []
        # Calculate how many per source to aim for a healthy mix
        per_source = max(5, count // len(sources) + 2)
        
        for source_fn in sources:
            try:
                new_meta = source_fn(query, per_source)
                all_meta.extend(new_meta)
                if len(all_meta) >= count * 1.5: # Get a buffer
                    break
            except Exception as e:
                logger.error(f"Source function failed: {e}")

        # Download process
        final_paths = []
        for meta in all_meta:
            try:
                # Use hash or unique ID to avoid duplicates
                url_hash = str(abs(hash(meta["url"])))[:8]
                fname = f"{meta['source'].lower()}_{url_hash}.mp4"
                fpath = os.path.join(self.temp_dir, fname)
                
                if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
                    final_paths.append(fpath)
                else:
                    logger.info(f"[Aggregator] Downloading: {meta['url']}")
                    r = requests.get(meta["url"], stream=True, timeout=60)
                    if r.status_code == 200:
                        with open(fpath, "wb") as f:
                            for chunk in r.iter_content(1024*1024):
                                if chunk: f.write(chunk)
                        
                        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
                            self.log_license(fpath, meta["source"], meta["license"], meta["author"])
                            final_paths.append(fpath)
                
                if len(final_paths) >= count:
                    break
            except Exception as e:
                logger.error(f"Download failed for {meta['url']}: {e}")
                continue
                
        logger.info(f"[Aggregator] Successfully acquired {len(final_paths)} unique clips.")
        return final_paths
