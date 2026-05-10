import os
import requests
import random
import logging
from pathlib import Path

# Logger
logger = logging.getLogger("Pixabay")

# PIXABAY API KEY
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "").strip()
if not PIXABAY_API_KEY:
    logger.warning("[Pixabay] API key bulunamadı.")

def search_pixabay_videos(query: str, max_results: int = 10, orientation: str = "vertical") -> list[str]:
    """
    Pixabay video API çağrısı yap, belirtilen orientation'a göre videoları indir.
    orientation: "vertical" (portrait) veya "horizontal" (landscape)
    """
    if not PIXABAY_API_KEY:
        return []

    downloaded_files = []
    output_dir = Path("assets/videos")
    output_dir.mkdir(parents=True, exist_ok=True)

    url = "https://pixabay.com/api/videos/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": 30,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            logger.error(f"[Pixabay] API hatası: {response.status_code}")
            return []

        data = response.json()
        hits = data.get("hits", [])
        
        random.shuffle(hits)
        
        index = 0
        for hit in hits:
            if len(downloaded_files) >= max_results:
                break

            videos = hit.get("videos", {})
            chosen_video = None
            
            # Belirtilen orientation'a uygun video seç
            for size in ["large", "medium", "small"]:
                v = videos.get(size)
                if v and v.get("url"):
                    w, h = v.get("width", 0), v.get("height", 0)
                    if orientation == "vertical":
                        if h > w: # Portrait
                            chosen_video = v
                            break
                    else:
                        if w > h: # Landscape
                            chosen_video = v
                            break
            
            # Fallback: orientation uygun değilse bile HD olanı al
            if not chosen_video:
                for size in ["large", "medium"]:
                    v = videos.get(size)
                    if v and v.get("url"):
                        if v.get("height", 0) >= 720:
                            chosen_video = v
                            break

            if chosen_video:
                video_url = chosen_video["url"]
                safe_query = "".join(x for x in query if x.isalnum())
                file_name = f"pixabay_{safe_query}_{index}.mp4"
                file_path = output_dir / file_name
                
                # Duplicate atla
                if file_path.exists():
                    downloaded_files.append(str(file_path))
                    index += 1
                    continue

                try:
                    logger.info(f"[Pixabay] İndiriliyor: {file_name}")
                    r = requests.get(video_url, stream=True, timeout=60)
                    if r.status_code == 200:
                        with open(file_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                f.write(chunk)
                        
                        if file_path.stat().st_size > 100000: # Minimum 100kb
                            downloaded_files.append(str(file_path))
                            index += 1
                except Exception as e:
                    logger.error(f"[Pixabay] Download hatası: {e}")

        logger.info(f"[Pixabay] ✅ {len(downloaded_files)} video indirildi")
        return downloaded_files

    except Exception as e:
        logger.error(f"[Pixabay] Hata: {e}")
        return []
