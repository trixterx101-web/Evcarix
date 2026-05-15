"""
footage_fetcher.py — Evcarix (Sade Versiyon)
Sadece Pexels ve Pixabay'dan HD klip indirir.
Her klip ffmpeg ile 5 saniyeye kırpılır.
"""
import os
import time
import random
import hashlib
import logging
import subprocess
import requests
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("FootageFetcher")

FOOTAGE_DIR = "assets/footage"
Path(FOOTAGE_DIR).mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# EV konuları için arama sorguları
EV_QUERIES = [
    "electric car driving",
    "EV charging station",
    "electric vehicle technology",
    "tesla electric car",
    "electric motor",
    "battery technology",
    "sustainable transport",
    "electric car interior",
    "charging plug electric",
    "electric vehicle highway",
    "solar energy technology",
    "clean energy innovation",
    "futuristic car",
    "electric vehicle night",
    "lithium battery",
]


class FootageFetcher:
    """Pexels → Pixabay → Synthetic fallback zinciri."""

    def __init__(self):
        self.pexels_key  = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.session     = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, query: str, count: int = 6,
              is_short: bool = True, topic: str = None) -> List[str]:
        """
        count adet 5 saniyelik HD klip döndürür.
        Pexels → Pixabay → Synthetic fallback sırasıyla.
        """
        orientation = "portrait" if is_short else "landscape"
        clips: List[str] = []

        # Arama sorgularını çeşitlendir
        queries = self._build_queries(query)

        # ── 1. Pexels ────────────────────────────────────────────────────────
        if self.pexels_key:
            for q in queries:
                if len(clips) >= count:
                    break
                new = self._pexels(q, count - len(clips), orientation)
                clips.extend(new)
                if new:
                    logger.info(f"[Pexels] '{q}': +{len(new)} klip")
        else:
            logger.warning("[FootageFetcher] PEXELS_API_KEY yok")

        # ── 2. Pixabay ───────────────────────────────────────────────────────
        if self.pixabay_key and len(clips) < count:
            for q in queries:
                if len(clips) >= count:
                    break
                new = self._pixabay(q, count - len(clips), orientation)
                clips.extend(new)
                if new:
                    logger.info(f"[Pixabay] '{q}': +{len(new)} klip")
        elif not self.pixabay_key and len(clips) < count:
            logger.warning("[FootageFetcher] PIXABAY_API_KEY yok")

        # ── 3. Synthetic fallback ────────────────────────────────────────────
        if len(clips) < count:
            needed = count - len(clips)
            logger.warning(f"[FootageFetcher] Yetersiz klip ({len(clips)}/{count}), {needed} sentez üretiliyor.")
            clips.extend(self._synthetic(needed, is_short))

        logger.info(f"[FootageFetcher] ✅ Toplam: {len(clips)}/{count} klip hazır")
        return clips[:count]

    # ── Pexels ────────────────────────────────────────────────────────────────
    def _pexels(self, query: str, count: int, orientation: str) -> List[str]:
        clips = []
        page  = random.randint(1, 5)
        try:
            r = self.session.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={
                    "query":       query,
                    "orientation": orientation,
                    "size":        "medium",
                    "per_page":    min(count * 2, 20),
                    "page":        page,
                },
                timeout=15
            )
            if r.status_code != 200:
                logger.debug(f"[Pexels] HTTP {r.status_code}")
                return []

            videos = r.json().get("videos", [])
            random.shuffle(videos)

            for v in videos:
                if len(clips) >= count:
                    break
                # En yüksek kalite dosyayı seç
                files = sorted(
                    v.get("video_files", []),
                    key=lambda x: x.get("width", 0),
                    reverse=True
                )
                for vf in files:
                    if vf.get("width", 0) >= 720:
                        uid  = hashlib.md5(vf["link"].encode()).hexdigest()[:10]
                        path = self._download_and_trim(
                            vf["link"], f"pexels_{v['id']}_{uid}.mp4", orientation
                        )
                        if path:
                            clips.append(path)
                        break
        except Exception as e:
            logger.error(f"[Pexels] Hata: {e}")
        return clips

    # ── Pixabay ───────────────────────────────────────────────────────────────
    def _pixabay(self, query: str, count: int, orientation: str) -> List[str]:
        clips = []
        page  = random.randint(1, 8)
        try:
            r = self.session.get(
                "https://pixabay.com/api/videos/",
                params={
                    "key":        self.pixabay_key,
                    "q":          query,
                    "per_page":   min(count * 2, 20),
                    "page":       page,
                    "min_width":  720,
                    "safesearch": "true",
                },
                timeout=15
            )
            if r.status_code != 200:
                logger.debug(f"[Pixabay] HTTP {r.status_code}")
                return []

            hits = r.json().get("hits", [])
            random.shuffle(hits)

            for h in hits:
                if len(clips) >= count:
                    break
                videos = h.get("videos", {})
                url = (
                    videos.get("large",  {}).get("url") or
                    videos.get("medium", {}).get("url") or
                    videos.get("small",  {}).get("url")
                )
                if url:
                    uid  = hashlib.md5(url.encode()).hexdigest()[:10]
                    path = self._download_and_trim(
                        url, f"pixabay_{h['id']}_{uid}.mp4", orientation
                    )
                    if path:
                        clips.append(path)
        except Exception as e:
            logger.error(f"[Pixabay] Hata: {e}")
        return clips

    # ── Synthetic fallback ────────────────────────────────────────────────────
    def _synthetic(self, count: int, is_short: bool) -> List[str]:
        """FFmpeg lavfi ile hareketli arka plan klipleri — her zaman çalışır."""
        size   = "1080x1920" if is_short else "1920x1080"
        colors = [
            "0x001833", "0x0A0020", "0x001A00",
            "0x1A0000", "0x0D0D00", "0x001A1A",
        ]
        clips = []
        for i in range(count):
            c = random.choice(colors)
            uid = random.randint(10000, 99999)
            out = os.path.join(FOOTAGE_DIR, f"synthetic_{uid}.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", (
                    f"color=c={c}:size={size}:rate=30,"
                    f"geq="
                    f"r='128+100*sin(2*3.14*X/250+T*1.2)':"
                    f"g='100+80*cos(2*3.14*Y/350+T*0.8)':"
                    f"b='200+55*sin(2*3.14*(X+Y)/500+T*1.5)'"
                ),
                "-t", "5",
                "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
                "-an", out
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode == 0 and os.path.exists(out):
                    clips.append(out)
                    logger.info(f"[FootageFetcher] Sentez klip: {out}")
            except Exception as e:
                logger.warning(f"[FootageFetcher] Sentez hatası: {e}")
        return clips

    # ── İndirme + Kırpma ─────────────────────────────────────────────────────
    def _download_and_trim(self, url: str, filename: str,
                           orientation: str, clip_duration: int = 5) -> Optional[str]:
        """
        URL'den video indir, ffmpeg ile 5 saniyeye kırp ve ölçekle.
        Cache: aynı dosya daha önce indirildiyse yeniden indirilmez.
        """
        dest_raw  = os.path.join(FOOTAGE_DIR, "raw_" + filename)
        dest_trim = os.path.join(FOOTAGE_DIR, filename)

        # Kırpılmış dosya zaten varsa doğrudan döndür
        if os.path.exists(dest_trim) and os.path.getsize(dest_trim) > 50_000:
            return dest_trim

        # ── İndir ────────────────────────────────────────────────────────────
        try:
            r = self.session.get(url, stream=True, timeout=30)
            if r.status_code != 200:
                return None
            content_len = int(r.headers.get("content-length", 0))
            if content_len and content_len > 200_000_000:  # 200 MB limit
                return None
            downloaded = 0
            with open(dest_raw, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    downloaded += len(chunk)
                    if downloaded > 200_000_000:
                        break
                    f.write(chunk)
            if os.path.getsize(dest_raw) < 10_000:
                os.remove(dest_raw)
                return None
        except Exception as e:
            logger.debug(f"[Download] {filename}: {e}")
            _safe_remove(dest_raw)
            return None

        # ── ffmpeg ile kırp + ölçekle ────────────────────────────────────────
        if orientation == "portrait":
            vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        else:
            vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"

        cmd = [
            "ffmpeg", "-y",
            "-i", dest_raw,
            "-ss", "1",               # İlk 1 sn atla (intro geçişleri için)
            "-t", str(clip_duration),
            "-vf", vf,
            "-c:v", "libx264", "-crf", "23", "-preset", "fast",
            "-an",                    # Ses yok (editor ekleyecek)
            dest_trim
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
        except Exception as e:
            logger.warning(f"[Trim] {filename}: {e}")
            _safe_remove(dest_raw)
            return None
        finally:
            _safe_remove(dest_raw)

        if result.returncode == 0 and os.path.exists(dest_trim) and os.path.getsize(dest_trim) > 50_000:
            size_mb = os.path.getsize(dest_trim) / (1024 * 1024)
            logger.info(f"[FootageFetcher] ✅ {filename} ({size_mb:.1f} MB)")
            return dest_trim

        _safe_remove(dest_trim)
        return None

    # ── Sorgu çeşitlendirme ───────────────────────────────────────────────────
    def _build_queries(self, query: str) -> List[str]:
        """Konu bazlı anahtar kelimeler + rastgele EV sorguları."""
        queries = [query]
        # Konuya özel kelimeler ekle
        q_lower = query.lower()
        if "battery" in q_lower or "bms" in q_lower or "charge cycle" in q_lower:
            queries += ["battery technology", "lithium battery", "energy storage"]
        elif "charging" in q_lower:
            queries += ["EV charging station", "electric vehicle charging", "charging infrastructure"]
        elif "range" in q_lower:
            queries += ["electric car driving", "EV highway", "sustainable transport"]
        elif "market" in q_lower or "sales" in q_lower:
            queries += ["electric vehicle", "EV technology", "clean energy car"]
        else:
            queries += random.sample(EV_QUERIES, min(3, len(EV_QUERIES)))
        return queries


def _safe_remove(path: str):
    """Dosyayı sessizce sil."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
