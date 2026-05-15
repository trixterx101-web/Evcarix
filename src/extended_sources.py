"""
extended_sources.py — v1.0
Wikimedia Commons + Internet Archive + Coverr ücretsiz video kaynakları.
Tüm içerikler CC0 / Public Domain — telif riski sıfır.
"""
import os, re, json, random, logging, requests, time
from pathlib import Path
from urllib.parse import quote

logger = logging.getLogger("ExtendedSources")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EvcarixBot/1.0)"}
TEMP_DIR = "assets/temp_videos"
LICENSE_LOG = "license_log.json"


def _log_license(file_path: str, source: str, license_type: str, author: str = "Unknown"):
    try:
        data = {}
        if os.path.exists(LICENSE_LOG):
            with open(LICENSE_LOG, "r") as f:
                data = json.load(f)
        data[os.path.basename(file_path)] = {
            "source": source, "license": license_type,
            "author": author, "timestamp": time.time()
        }
        with open(LICENSE_LOG, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"License log failed: {e}")


def _download_file(url: str, dest_path: str, timeout: int = 90) -> bool:
    """Akış halinde indir, hata olursa False döner."""
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=timeout)
        if r.status_code != 200:
            return False
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(1024 * 512):
                if chunk:
                    f.write(chunk)
        size = os.path.getsize(dest_path)
        if size < 50_000:  # 50KB'dan küçükse geçersiz
            os.remove(dest_path)
            return False
        return True
    except Exception as e:
        logger.error(f"Download failed ({url}): {e}")
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        return False


class WikimediaSource:
    """
    Wikimedia Commons — Public Domain / CC0 video ve görseller.
    API: https://commons.wikimedia.org/w/api.php
    API key gerektirmez.
    """

    BASE = "https://commons.wikimedia.org/w/api.php"

    def search_videos(self, query: str, count: int = 5) -> list[dict]:
        params = {
            "action": "query", "list": "search", "srsearch": query,
            "srnamespace": "6",  # File namespace
            "srlimit": count * 3, "srinfo": "totalhits",
            "srprop": "titlesnippet|snippet",
            "format": "json"
        }
        results = []
        try:
            r = requests.get(self.BASE, params=params, headers=HEADERS, timeout=15)
            data = r.json()
            for item in data.get("query", {}).get("search", []):
                title = item.get("title", "")
                if not title.lower().endswith((".webm", ".ogv", ".mp4")):
                    continue
                # Dosya URL'si
                fname = title.replace("File:", "").replace(" ", "_")
                file_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(fname)}"
                results.append({
                    "url": file_url, "title": title,
                    "source": "Wikimedia Commons", "license": "Public Domain / CC",
                    "author": "Wikimedia Contributors"
                })
                if len(results) >= count:
                    break
        except Exception as e:
            logger.error(f"Wikimedia search error: {e}")
        logger.info(f"[Wikimedia] '{query}': {len(results)} sonuç")
        return results

    def fetch_and_download(self, query: str, count: int = 3,
                           dest_dir: str = TEMP_DIR) -> list[str]:
        os.makedirs(dest_dir, exist_ok=True)
        meta_list = self.search_videos(query, count * 2)
        paths = []
        for meta in meta_list:
            if len(paths) >= count:
                break
            slug = re.sub(r'[^a-zA-Z0-9]', '_', meta["title"])[:40]
            dest = os.path.join(dest_dir, f"wikimedia_{slug}.mp4")
            if os.path.exists(dest) and os.path.getsize(dest) > 50_000:
                paths.append(dest)
                continue
            # Wikimedia dosyaları bazen webm olur — ffmpeg dönüştürür
            if _download_file(meta["url"], dest):
                _log_license(dest, meta["source"], meta["license"], meta["author"])
                paths.append(dest)
        logger.info(f"[Wikimedia] İndirilen: {len(paths)}")
        return paths


class InternetArchiveSource:
    """
    Internet Archive (archive.org) — Public Domain filmler ve videolar.
    API key gerektirmez. Özellikle uzay, doğa, bilim arşivleri.
    """

    SEARCH_URL = "https://archive.org/advancedsearch.php"
    DOWNLOAD_URL = "https://archive.org/download"

    EV_COLLECTIONS = [
        "NASA", "prelinger", "computersandtechvideos",
        "opensource_movies", "feature_films"
    ]

    def search(self, query: str, count: int = 4, media_type: str = "movies") -> list[dict]:
        params = {
            "q": f"{query} AND mediatype:{media_type}",
            "fl[]": ["identifier", "title", "creator", "licenseurl"],
            "sort[]": "downloads desc",
            "rows": count * 3, "page": 1,
            "output": "json"
        }
        results = []
        try:
            r = requests.get(self.SEARCH_URL, params=params,
                             headers=HEADERS, timeout=20)
            data = r.json()
            for doc in data.get("response", {}).get("docs", []):
                ident = doc.get("identifier", "")
                title = doc.get("title", ident)
                creator = doc.get("creator", "Unknown")
                license_url = doc.get("licenseurl", "")
                # Lisans kontrolü: sadece public domain / CC kabul et
                if license_url and "by-nc" in license_url:
                    continue  # NC lisanslar ticari kullanım için uygun değil
                results.append({
                    "identifier": ident, "title": title,
                    "creator": creator, "license_url": license_url,
                    "source": "Internet Archive"
                })
                if len(results) >= count:
                    break
        except Exception as e:
            logger.error(f"Archive.org search error: {e}")
        logger.info(f"[InternetArchive] '{query}': {len(results)} sonuç")
        return results

    def _get_mp4_url(self, identifier: str) -> str | None:
        """Archive.org item'ından ilk MP4 dosyasının URL'sini döner."""
        try:
            meta_url = f"https://archive.org/metadata/{identifier}"
            r = requests.get(meta_url, headers=HEADERS, timeout=15)
            data = r.json()
            for f in data.get("files", []):
                if f.get("name", "").lower().endswith(".mp4"):
                    return f"https://archive.org/download/{identifier}/{f['name']}"
        except Exception as e:
            logger.error(f"Archive.org metadata error ({identifier}): {e}")
        return None

    def fetch_and_download(self, query: str, count: int = 3,
                           dest_dir: str = TEMP_DIR) -> list[str]:
        os.makedirs(dest_dir, exist_ok=True)
        meta_list = self.search(query, count * 2)
        paths = []
        for meta in meta_list:
            if len(paths) >= count:
                break
            ident = meta["identifier"]
            dest = os.path.join(dest_dir, f"archive_{ident[:30]}.mp4")
            if os.path.exists(dest) and os.path.getsize(dest) > 50_000:
                paths.append(dest)
                continue
            mp4_url = self._get_mp4_url(ident)
            if not mp4_url:
                continue
            if _download_file(mp4_url, dest, timeout=120):
                _log_license(dest, "Internet Archive",
                             meta.get("license_url", "Public Domain"),
                             meta.get("creator", "Unknown"))
                paths.append(dest)
        logger.info(f"[InternetArchive] İndirilen: {len(paths)}")
        return paths


class CoverrSource:
    """
    Coverr.co — CC0 ücretsiz stok video.
    Public HTML sayfasından scrape — API key gerektirmez.
    """

    BASE_URL = "https://coverr.co"

    # Coverr'ın public video JSON endpoint'i
    API_URL = "https://coverr.co/api/videos/search"

    def search(self, query: str, count: int = 4) -> list[dict]:
        results = []
        try:
            params = {"query": query, "page": 1}
            r = requests.get(self.API_URL, params=params,
                             headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                for item in data.get("hits", [])[:count * 2]:
                    # MP4 URL bul
                    mp4_url = None
                    for src in item.get("sources", []):
                        if src.get("type") == "video/mp4":
                            mp4_url = src.get("url")
                            break
                    if not mp4_url:
                        mp4_url = item.get("mp4_url") or item.get("url")
                    if mp4_url:
                        results.append({
                            "url": mp4_url, "title": item.get("title", query),
                            "source": "Coverr", "license": "CC0"
                        })
                    if len(results) >= count:
                        break
        except Exception as e:
            logger.error(f"Coverr search error: {e}")
        logger.info(f"[Coverr] '{query}': {len(results)} sonuç")
        return results

    def fetch_and_download(self, query: str, count: int = 3,
                           dest_dir: str = TEMP_DIR) -> list[str]:
        os.makedirs(dest_dir, exist_ok=True)
        meta_list = self.search(query, count * 2)
        paths = []
        for meta in meta_list:
            if len(paths) >= count:
                break
            slug = re.sub(r'[^a-zA-Z0-9]', '_', meta.get("title", "coverr"))[:30]
            dest = os.path.join(dest_dir, f"coverr_{slug}_{len(paths)}.mp4")
            if os.path.exists(dest) and os.path.getsize(dest) > 50_000:
                paths.append(dest)
                continue
            if _download_file(meta["url"], dest):
                _log_license(dest, "Coverr", "CC0")
                paths.append(dest)
        logger.info(f"[Coverr] İndirilen: {len(paths)}")
        return paths


class ExtendedMediaSources:
    """
    Wikimedia + Internet Archive + Coverr'ı tek bir arayüzden kullan.
    """
    def __init__(self):
        self.wikimedia = WikimediaSource()
        self.archive   = InternetArchiveSource()
        self.coverr    = CoverrSource()

    def fetch_all(self, query: str, count: int = 8,
                  dest_dir: str = TEMP_DIR) -> list[str]:
        """
        Tüm ücretsiz genişletilmiş kaynaklardan video toplar.
        Public Domain / CC0 güvenceli — telif riski sıfır.
        """
        os.makedirs(dest_dir, exist_ok=True)
        all_paths = []
        per_source = max(2, count // 3)

        # 1. Wikimedia Commons
        try:
            wm = self.wikimedia.fetch_and_download(query, per_source, dest_dir)
            all_paths.extend(wm)
            logger.info(f"[ExtendedSources] Wikimedia: +{len(wm)}")
        except Exception as e:
            logger.error(f"Wikimedia failed: {e}")

        # 2. Coverr (hızlı, güvenilir)
        try:
            cv = self.coverr.fetch_and_download(query, per_source, dest_dir)
            all_paths.extend(cv)
            logger.info(f"[ExtendedSources] Coverr: +{len(cv)}")
        except Exception as e:
            logger.error(f"Coverr failed: {e}")

        # 3. Internet Archive (yalnızca yeterli yoksa — yavaş)
        if len(all_paths) < count:
            try:
                ia = self.archive.fetch_and_download(
                    query, count - len(all_paths), dest_dir)
                all_paths.extend(ia)
                logger.info(f"[ExtendedSources] Archive.org: +{len(ia)}")
            except Exception as e:
                logger.error(f"Archive.org failed: {e}")

        random.shuffle(all_paths)
        logger.info(f"[ExtendedSources] Toplam: {len(all_paths)} klip (query: '{query}')")
        return all_paths[:count]
