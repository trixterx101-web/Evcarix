import os
import requests
import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger("MusicFetcher")
MUSIC_DIR = "assets/music"

# Verified working links from FMA and ccMixter
MUSIC_LIBRARY = {
    "tech_upbeat": [
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Broke_For_Free/Directionless_EP/Broke_For_Free_-_01_-_Night_Owl.mp3",
        "https://ccmixter.org/content/texasradiofish/texasradiofish_-_Deep_Dive.mp3",
    ],
    "ambient_calm": [
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/ccCommunity/Kai_Engel/Satin/Kai_Engel_-_07_-_Interlude.mp3",
    ],
    "dramatic_epic": [
        "https://files.freemusicarchive.org/storage-freemusicarchive-org/music/WFMU/Broke_For_Free/Layers_EP/Broke_For_Free_-_01_-_As_Colorful_As_Ever.mp3",
    ]
}

class MusicFetcher:
    def __init__(self):
        Path(MUSIC_DIR).mkdir(parents=True, exist_ok=True)
        self.headers = {"User-Agent": "EvcarixBot/2.0"}

    def get_track(self, mood: str = "tech_upbeat") -> str:
        """Download and cache a music track. Returns local path."""
        tracks = MUSIC_LIBRARY.get(mood, MUSIC_LIBRARY["tech_upbeat"])
        
        for url in tracks:
            try:
                # Use filename from URL as cache key
                fname = url.split("/")[-1].replace(" ", "_")
                local_path = os.path.join(MUSIC_DIR, fname)
                
                if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
                    return local_path
                
                logger.info(f"[MusicFetcher] Downloading track: {url}")
                r = requests.get(url, headers=self.headers, timeout=25, stream=True)
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        for chunk in r.iter_content(65536):
                            if chunk: f.write(chunk)
                    return local_path
            except Exception as e:
                logger.warning(f"[MusicFetcher] Download failed for {url}: {e}")
                continue
        
        # Ultimate fallback: generate silence
        logger.warning("[MusicFetcher] All downloads failed. Generating silence.")
        return self._generate_silence(duration=60)
    
    def _generate_silence(self, duration: int) -> str:
        """Generate silent audio with FFmpeg as last resort."""
        dest = os.path.join(MUSIC_DIR, "silence_fallback.mp3")
        if os.path.exists(dest): return dest
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-c:a", "libmp3lame",
            dest
        ]
        subprocess.run(cmd, capture_output=True)
        return dest
