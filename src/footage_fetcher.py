import os
import requests
import random
import logging
import hashlib
import time
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("FootageFetcher")
TEMP_DIR = "assets/footage"

class FootageFetcher:
    def __init__(self):
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        self.headers = {"User-Agent": "EvcarixBot/2.0 (Global English Tech Channel)"}

    def fetch(self, query: str, count: int = 4, is_short: bool = True) -> List[str]:
        """Sırasıyla kaynakları tarayarak klip toplar. YouTube CC'yi devreden çıkardık."""
        clips = []
        logger.info(f"[FootageFetcher] Searching for: {query} (Target: {count})")

        # 1. Pexels (Primary)
        if self.pexels_key and len(clips) < count:
            logger.info("[FootageFetcher] Trying Pexels...")
            clips += self._pexels(query, count - len(clips), is_short)

        # 2. Pixabay
        if self.pixabay_key and len(clips) < count:
            logger.info("[FootageFetcher] Trying Pixabay...")
            clips += self._pixabay(query, count - len(clips))

        # 3. NASA (Otorite)
        if len(clips) < count:
            logger.info("[FootageFetcher] Trying NASA...")
            clips += self._nasa(query, count - len(clips))

        # 4. Wikimedia (Fallback)
        if len(clips) < count:
            logger.info("[FootageFetcher] Trying Wikimedia...")
            clips += self._wikimedia(query, count - len(clips))
            
        # 5. Archive.org
        if len(clips) < count:
            logger.info("[FootageFetcher] Trying Archive.org...")
            clips += self._archive_org(query, count - len(clips))

        logger.info(f"[FootageFetcher] Total clips found: {len(clips)}")
        return clips[:count]

    def _pexels(self, query: str, count: int, is_short: bool) -> List[str]:
        paths = []
        try:
            url = f"https://api.pexels.com/videos/search"
            orientation = "portrait" if is_short else "landscape"
            params = {"query": query, "per_page": count * 2, "orientation": orientation}
            headers = {"Authorization": self.pexels_key}
            
            r = requests.get(url, params=params, headers=headers, timeout=15)
            if r.status_code == 200:
                videos = r.json().get("videos", [])
                for v in videos:
                    if len(paths) >= count: break
                    v_files = sorted(v.get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
                    if v_files:
                        dl_url = v_files[0]["link"]
                        path = self._download(dl_url, "pexels")
                        if path: paths.append(path)
        except Exception as e: logger.error(f"[FootageFetcher] Pexels error: {e}")
        return paths

    def _pixabay(self, query: str, count: int) -> List[str]:
        paths = []
        try:
            url = "https://pixabay.com/api/videos/"
            params = {"key": self.pixabay_key, "q": query, "per_page": count * 2, "min_width": 1280}
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                hits = r.json().get("hits", [])
                for h in hits:
                    if len(paths) >= count: break
                    dl_url = h.get("videos", {}).get("large", {}).get("url") or h.get("videos", {}).get("medium", {}).get("url")
                    if dl_url:
                        path = self._download(dl_url, "pixabay")
                        if path: paths.append(path)
        except Exception as e: logger.error(f"[FootageFetcher] Pixabay error: {e}")
        return paths

    def _nasa(self, query: str, count: int) -> List[str]:
        paths = []
        try:
            url = "https://images-api.nasa.gov/search"
            params = {"q": query, "media_type": "video"}
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                items = r.json().get("collection", {}).get("items", [])
                for item in items:
                    if len(paths) >= count: break
                    data = item.get("data", [{}])[0]
                    nasa_id = data.get("nasa_id")
                    if not nasa_id: continue
                    asset_url = f"https://images-api.nasa.gov/asset/{nasa_id}"
                    ar = requests.get(asset_url, timeout=10)
                    if ar.status_code == 200:
                        links = [v["href"] for v in ar.json()["collection"]["items"] if v["href"].endswith(".mp4")]
                        if links:
                            path = self._download(links[0], "nasa")
                            if path: paths.append(path)
        except Exception as e: logger.error(f"[FootageFetcher] NASA error: {e}")
        return paths

    def _wikimedia(self, query: str, count: int) -> List[str]:
        paths = []
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query", "generator": "search", "gsrnamespace": 6,
                "gsrsearch": f"filetype:video {query}", "gsrlimit": count * 2,
                "prop": "videoinfo", "viprop": "url", "format": "json"
            }
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                pages = r.json().get("query", {}).get("pages", {})
                for p in pages.values():
                    if len(paths) >= count: break
                    vinfo = p.get("videoinfo", [{}])
                    if not vinfo: continue
                    v_url = vinfo[0].get("url")
                    if v_url and v_url.lower().endswith((".mp4", ".webm")):
                        path = self._download(v_url, "wikimedia")
                        if path: paths.append(path)
        except Exception as e: logger.error(f"[FootageFetcher] Wikimedia error: {e}")
        return paths

    def _archive_org(self, query: str, count: int) -> List[str]:
        paths = []
        try:
            # Simple archive.org search for videos
            url = "https://archive.org/advancedsearch.php"
            params = {
                "q": f"mediatype:movies AND {query}",
                "fl[]": "identifier",
                "sort[]": "downloads desc",
                "rows": count * 2,
                "output": "json"
            }
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                docs = r.json().get("response", {}).get("docs", [])
                for doc in docs:
                    if len(paths) >= count: break
                    ident = doc.get("identifier")
                    # Try to get metadata for mp4 files
                    meta_url = f"https://archive.org/metadata/{ident}"
                    mr = requests.get(meta_url, timeout=10)
                    if mr.status_code == 200:
                        files = mr.json().get("files", [])
                        mp4s = [f["name"] for f in files if f["name"].endswith(".mp4")]
                        if mp4s:
                            dl_url = f"https://archive.org/download/{ident}/{mp4s[0]}"
                            path = self._download(dl_url, "archive")
                            if path: paths.append(path)
        except Exception as e: logger.error(f"[FootageFetcher] Archive.org error: {e}")
        return paths

    def _download(self, url: str, source: str) -> Optional[str]:
        try:
            uid = hashlib.md5(url.encode()).hexdigest()[:10]
            ext = ".mp4" if ".mp4" in url.lower() else ".webm"
            dest = os.path.join(TEMP_DIR, f"{source}_{uid}{ext}")
            
            # Check cache
            if os.path.exists(dest) and os.path.getsize(dest) > 1000:
                return dest
            
            for i in range(3): # 3 retries
                try:
                    r = requests.get(url, headers=self.headers, timeout=45, stream=True)
                    if r.status_code == 200:
                        with open(dest, "wb") as f:
                            for chunk in r.iter_content(1024*128):
                                if chunk: f.write(chunk)
                        return dest
                except:
                    time.sleep(2)
        except: pass
        return None
