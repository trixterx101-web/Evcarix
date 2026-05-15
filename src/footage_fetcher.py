"""
footage_fetcher.py — Evcarix v3
8 kaynaklı çeşitli footage toplama motoru.
ClipRegistry ile run'lar arası tekrar önleme.
"""
import os
import json
import time
import random
import hashlib
import logging
import subprocess
import requests
from pathlib import Path
from typing import List, Optional

from src.clip_registry import ClipRegistry

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

# Konu → arama anahtar kelimeleri
TOPIC_KEYWORDS = {
    "battery": [
        "battery technology", "electric battery cells", "energy storage",
        "lithium ion battery", "battery charging station", "power cells laboratory",
        "battery pack technology", "cell degradation research", "renewable energy storage",
    ],
    "charging": [
        "EV charging station", "electric vehicle charging", "fast charging technology",
        "charging infrastructure", "supercharger station", "wireless charging",
    ],
    "electric_vehicle": [
        "electric car driving", "EV on highway", "electric vehicle interior",
        "zero emission vehicle", "sustainable transport", "electric motor technology",
    ],
    "ai": [
        "artificial intelligence visualization", "neural network", "machine learning",
        "data center servers", "digital technology", "computer algorithm",
    ],
    "robotics": [
        "industrial robot arm", "robot factory", "automated manufacturing",
        "humanoid robot", "robotic technology", "mechanical engineering",
    ],
    "future_tech": [
        "future technology innovation", "smart city", "renewable energy",
        "solar panel installation", "wind turbine farm", "quantum computing",
    ],
}

# CI'de sentez klip renk paleti
SYNTHETIC_COLORS = [
    ("0x001833", "0x00D4FF"),  # Derin mavi → cyan
    ("0x0A0020", "0x6600FF"),  # Koyu mor → neon mor
    ("0x001A00", "0x00FF88"),  # Koyu yeşil → neon yeşil
    ("0x1A0000", "0xFF4400"),  # Koyu kırmızı → turuncu
    ("0x0D0D00", "0xFFCC00"),  # Koyu sarı → altın
]


def _pick_keywords(query: str, topic: str = None) -> List[str]:
    """Konu ve sorguya göre çeşitli arama anahtar kelimeleri döndürür."""
    keywords = [query]
    for key, kws in TOPIC_KEYWORDS.items():
        if key in (topic or "").lower() or key in query.lower():
            keywords.extend(kws)
            break
    if len(keywords) < 4:
        # Genel EV anahtar kelimeleri ekle
        keywords.extend([
            "electric vehicle technology", "EV innovation",
            "clean energy", "sustainable mobility",
        ])
    random.shuffle(keywords)
    return list(dict.fromkeys(keywords))  # Deduplikasyon koruyarak karıştır


class FootageFetcher:
    """8 kaynaklı, registry tabanlı, tekrar önleyen footage toplayıcı."""

    def __init__(self):
        self.pexels_key  = os.getenv("PEXELS_API_KEY")
        self.pixabay_key = os.getenv("PIXABAY_API_KEY")
        self.registry    = ClipRegistry()
        self.session     = requests.Session()
        self.session.headers.update(HEADERS)
        logger.info(self.registry.stats())

    # ── Ana giriş noktası ─────────────────────────────────────────────────────
    def fetch(self, query: str, count: int = 6,
              is_short: bool = True, topic: str = None) -> List[str]:
        """
        Birden fazla kaynaktan klip topla, registry ile tekrarı önle.
        Her zaman geçerli bir liste döndürür (boş bile olsa crash yok).
        """
        self.registry.reset_if_exhausted(threshold=500)
        orientation = "portrait" if is_short else "landscape"
        keywords    = _pick_keywords(query, topic)
        clips: List[str] = []

        # Kaynak zinciri — sırayla dene
        sources = [
            ("Pexels",    self._pexels),
            ("Pixabay",   self._pixabay),
            ("NASA",      self._nasa),
            ("Wikimedia", self._wikimedia),
            ("Archive",   self._archive_org),
            ("Coverr",    self._coverr),
            ("NREL",      self._nrel),
            ("Synthetic", self._synthetic),
        ]

        kw_idx = 0
        for src_name, src_fn in sources:
            if len(clips) >= count:
                break
            needed = count - len(clips)
            kw = keywords[kw_idx % len(keywords)]
            kw_idx += 1
            try:
                new = src_fn(kw, needed, orientation)
                added = 0
                for p in new:
                    if not p:
                        continue
                    if self.registry.is_file_duplicate(p):
                        logger.info(f"[FootageFetcher] Tekrar klip atlandı: {os.path.basename(p)}")
                        continue
                    clips.append(p)
                    self.registry.mark_used(kw, p)
                    added += 1
                    if len(clips) >= count:
                        break
                logger.info(f"[FootageFetcher] {src_name}: +{added} klip (toplam: {len(clips)}/{count})")
            except Exception as e:
                logger.warning(f"[FootageFetcher] {src_name} hatası: {e}")

        if not clips:
            logger.warning("[FootageFetcher] Hiç klip bulunamadı, sentez üretiliyor.")
            clips = self._synthetic(query, count, orientation)

        logger.info(f"[FootageFetcher] ✅ Toplam: {len(clips)} klip")
        return clips[:count]

    # ── KAYNAK 1: Pexels ─────────────────────────────────────────────────────
    def _pexels(self, query: str, count: int, orientation: str = "portrait") -> List[str]:
        if not self.pexels_key:
            return []
        clips = []
        page = random.randint(1, 8)
        try:
            r = self.session.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": self.pexels_key},
                params={"query": query, "orientation": orientation,
                        "size": "medium", "per_page": count * 3, "page": page},
                timeout=15
            )
            if r.status_code != 200:
                return []
            videos = r.json().get("videos", [])
            random.shuffle(videos)
            for v in videos:
                if len(clips) >= count:
                    break
                vid_key = f"pexels_{v['id']}"
                if self.registry.is_used(vid_key):
                    continue
                files = sorted(v.get("video_files", []),
                               key=lambda x: x.get("width", 0), reverse=True)
                for vf in files:
                    if vf.get("width", 0) >= 720:
                        p = self._download(vf["link"], f"pexels_{v['id']}.mp4")
                        if p:
                            self.registry.mark_used(vid_key, p)
                            clips.append(p)
                            break
        except Exception as e:
            logger.error(f"[Pexels] {e}")
        return clips

    # ── KAYNAK 2: Pixabay ────────────────────────────────────────────────────
    def _pixabay(self, query: str, count: int, orientation: str = "portrait") -> List[str]:
        if not self.pixabay_key:
            return []
        clips = []
        page = random.randint(1, 10)
        try:
            r = self.session.get(
                "https://pixabay.com/api/videos/",
                params={"key": self.pixabay_key, "q": query,
                        "per_page": count * 3, "page": page,
                        "min_width": 720, "safesearch": "true"},
                timeout=15
            )
            if r.status_code != 200:
                return []
            hits = r.json().get("hits", [])
            random.shuffle(hits)
            for h in hits:
                if len(clips) >= count:
                    break
                key = f"pixabay_{h['id']}"
                if self.registry.is_used(key):
                    continue
                videos = h.get("videos", {})
                for q_level in ["large", "medium", "small", "tiny"]:
                    url = videos.get(q_level, {}).get("url", "")
                    if url:
                        p = self._download(url, f"pixabay_{h['id']}.mp4")
                        if p:
                            self.registry.mark_used(key, p)
                            clips.append(p)
                            break
        except Exception as e:
            logger.error(f"[Pixabay] {e}")
        return clips

    # ── KAYNAK 3: NASA ───────────────────────────────────────────────────────
    def _nasa(self, query: str, count: int, *_) -> List[str]:
        clips = []
        nasa_queries = [
            query,
            "electric vehicle technology",
            "energy storage research",
            "clean energy innovation",
            "solar technology laboratory",
            "battery research science",
        ]
        random.shuffle(nasa_queries)
        try:
            for nq in nasa_queries:
                if len(clips) >= count:
                    break
                r = self.session.get(
                    "https://images-api.nasa.gov/search",
                    params={"q": nq, "media_type": "video", "page_size": 20},
                    timeout=15
                )
                if r.status_code != 200:
                    continue
                items = r.json().get("collection", {}).get("items", [])
                random.shuffle(items)
                for item in items:
                    if len(clips) >= count:
                        break
                    nasa_id = item.get("data", [{}])[0].get("nasa_id", "")
                    if not nasa_id or self.registry.is_used(f"nasa_{nasa_id}"):
                        continue
                    try:
                        ar = self.session.get(
                            f"https://images-api.nasa.gov/asset/{nasa_id}", timeout=10)
                        if ar.status_code != 200:
                            continue
                        links = [a["href"] for a in ar.json()["collection"]["items"]
                                 if a["href"].endswith(".mp4")]
                        if links:
                            p = self._download(links[0], f"nasa_{nasa_id}.mp4")
                            if p:
                                self.registry.mark_used(f"nasa_{nasa_id}", p)
                                clips.append(p)
                    except Exception:
                        continue
                time.sleep(0.3)
        except Exception as e:
            logger.error(f"[NASA] {e}")
        return clips

    # ── KAYNAK 4: Wikimedia Commons ──────────────────────────────────────────
    def _wikimedia(self, query: str, count: int, *_) -> List[str]:
        clips = []
        offset = random.randint(0, 80)
        try:
            r = self.session.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "list": "search",
                    "srsearch": f"{query} filetype:video",
                    "srnamespace": "6",
                    "srlimit": count * 4,
                    "format": "json",
                    "sroffset": offset
                },
                timeout=15
            )
            if r.status_code != 200:
                return []
            results = r.json().get("query", {}).get("search", [])
            random.shuffle(results)
            for result in results:
                if len(clips) >= count:
                    break
                title = result.get("title", "")
                if not title or self.registry.is_used(f"wiki_{title}"):
                    continue
                if not any(title.lower().endswith(e) for e in [".ogv", ".webm", ".mp4"]):
                    continue
                try:
                    info = self.session.get(
                        "https://commons.wikimedia.org/w/api.php",
                        params={"action": "query", "titles": title,
                                "prop": "videoinfo", "viprop": "url|size",
                                "format": "json"},
                        timeout=10
                    )
                    pages = info.json().get("query", {}).get("pages", {})
                    for page in pages.values():
                        vi = page.get("videoinfo", [{}])[0]
                        url = vi.get("url", "")
                        size = int(vi.get("size", 0))
                        if url and 0 < size < 50_000_000:
                            fname = f"wiki_{hashlib.md5(url.encode()).hexdigest()[:10]}.mp4"
                            p = self._download(url, fname)
                            if p:
                                self.registry.mark_used(f"wiki_{title}", p)
                                clips.append(p)
                            break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"[Wikimedia] {e}")
        return clips

    # ── KAYNAK 5: Archive.org (geliştirilmiş) ────────────────────────────────
    def _archive_org(self, query: str, count: int, *_) -> List[str]:
        clips = []
        # Her seferinde farklı koleksiyon ve sayfa
        collection = random.choice([
            "prelinger", "computersandtech",
            "opensource_movies", "stock_footage", "nasa",
        ])
        page = random.randint(1, 15)
        try:
            r = self.session.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": f"({query}) AND mediatype:movies AND collection:{collection}",
                    "fl[]": ["identifier"],
                    "rows": count * 4,
                    "page": page,
                    "output": "json",
                    "sort[]": "random",
                },
                timeout=15
            )
            if r.status_code != 200:
                # Koleksiyonsuz fallback
                r = self.session.get(
                    "https://archive.org/advancedsearch.php",
                    params={"q": f"({query}) AND mediatype:movies",
                            "fl[]": ["identifier"],
                            "rows": count * 4, "page": page,
                            "output": "json", "sort[]": "random"},
                    timeout=15
                )
            if r.status_code != 200:
                return []
            docs = r.json().get("response", {}).get("docs", [])
            random.shuffle(docs)
            for doc in docs:
                if len(clips) >= count:
                    break
                ident = doc.get("identifier", "")
                if not ident or self.registry.is_used(f"ia_{ident}"):
                    continue
                try:
                    meta = self.session.get(
                        f"https://archive.org/metadata/{ident}", timeout=10)
                    if meta.status_code != 200:
                        continue
                    files = meta.json().get("files", [])
                    mp4s = [
                        f for f in files
                        if f.get("name", "").lower().endswith(".mp4")
                        and 100_000 < int(f.get("size", 0)) < 30_000_000
                    ]
                    if not mp4s:
                        continue
                    chosen = random.choice(mp4s)
                    url = f"https://archive.org/download/{ident}/{chosen['name']}"
                    p = self._download(url, f"ia_{ident[:20]}_{chosen['name'][-10:]}")
                    if p:
                        self.registry.mark_used(f"ia_{ident}", p)
                        clips.append(p)
                except Exception:
                    continue
                time.sleep(0.4)
        except Exception as e:
            logger.error(f"[Archive.org] {e}")
        return clips

    # ── KAYNAK 6: Coverr ─────────────────────────────────────────────────────
    def _coverr(self, query: str, count: int, *_) -> List[str]:
        clips = []
        try:
            r = self.session.get(
                "https://coverr.co/api/videos/search",
                params={"query": query, "per_page": count * 3,
                        "page": random.randint(1, 5)},
                timeout=15
            )
            if r.status_code != 200:
                return []
            videos = r.json().get("hits", [])
            random.shuffle(videos)
            for v in videos:
                if len(clips) >= count:
                    break
                vid_id = v.get("id", "")
                key = f"coverr_{vid_id}"
                if self.registry.is_used(key):
                    continue
                url = v.get("urls", {}).get("mp4_720", "")
                if url:
                    p = self._download(url, f"coverr_{vid_id}.mp4")
                    if p:
                        self.registry.mark_used(key, p)
                        clips.append(p)
        except Exception as e:
            logger.error(f"[Coverr] {e}")
        return clips

    # ── KAYNAK 7: NREL / DOE Enerji Araştırma Videoları ─────────────────────
    def _nrel(self, query: str, count: int, *_) -> List[str]:
        clips = []
        # Sabit, doğrulanmış enerji araştırma URL'leri
        energy_urls = [
            # DOE EV B-roll
            "https://www.energy.gov/sites/default/files/2022-07/ev-charging-broll.mp4",
            # AFDC EV charging
            "https://afdc.energy.gov/files/vehicles/electric_charging_broll.mp4",
            # DOE grid modernization
            "https://www.energy.gov/sites/default/files/2023-01/grid-modernization-broll.mp4",
            # DOE EV Everywhere
            "https://www.energy.gov/sites/default/files/2021-06/EV-everywhere.mp4",
            # Archive.org NASA EV sabit
            "https://archive.org/download/gov.energy.doe.ev_broll/ev_charging.mp4",
        ]
        random.shuffle(energy_urls)
        for url in energy_urls:
            if len(clips) >= count:
                break
            if self.registry.is_used(url):
                continue
            fname = f"nrel_{hashlib.md5(url.encode()).hexdigest()[:10]}.mp4"
            p = self._download(url, fname)
            if p:
                self.registry.mark_used(url, p)
                clips.append(p)
        return clips

    # ── KAYNAK 8: FFmpeg Sentez (son çare) ───────────────────────────────────
    def _synthetic(self, query: str, count: int, orientation: str = "portrait") -> List[str]:
        """
        FFmpeg lavfi ile hareketli arka plan klipleri üretir.
        Dış bağımlılık yok — her zaman çalışır.
        """
        clips = []
        if orientation == "portrait":
            size = "1080x1920"
        else:
            size = "1920x1080"

        for i in range(count):
            c1, c2 = random.choice(SYNTHETIC_COLORS)
            uid = random.randint(10000, 99999)
            out = os.path.join(FOOTAGE_DIR, f"synthetic_{uid}.mp4")
            duration = random.randint(5, 8)

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                # Gradient animasyon
                "-i", (
                    f"color=c={c1}:size={size}:rate=30,"
                    f"geq="
                    f"r='128+100*sin(2*3.14*X/{random.randint(150,400)}+T*{random.uniform(0.5,2.0):.2f})':"
                    f"g='128+80*cos(2*3.14*Y/{random.randint(200,500)}+T*{random.uniform(0.3,1.5):.2f})':"
                    f"b='200+55*sin(2*3.14*(X+Y)/{random.randint(300,700)}+T*{random.uniform(0.8,2.5):.2f})'"
                ),
                "-t", str(duration),
                "-c:v", "libx264", "-crf", "28", "-preset", "ultrafast",
                "-an", out
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                if result.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1000:
                    clips.append(out)
                    logger.info(f"[FootageFetcher] ✅ Sentez klip: {out}")
            except Exception as e:
                logger.warning(f"[FootageFetcher] Sentez klip hatası: {e}")

        return clips

    # ── İndirme yardımcısı ───────────────────────────────────────────────────
    def _download(self, url: str, filename: str,
                  max_mb: int = 40) -> Optional[str]:
        """URL'den dosya indir — cache kontrolü, boyut limiti, 3 yeniden deneme."""
        if not url:
            return None

        # Dosya adını güvenli yap
        safe_name = "".join(
            c if c.isalnum() or c in "-_." else "_"
            for c in filename
        )[:80]
        if not safe_name.endswith(".mp4"):
            safe_name = hashlib.md5(url.encode()).hexdigest()[:12] + ".mp4"

        dest = os.path.join(FOOTAGE_DIR, safe_name)

        # Önbellekte var ve geçerli boyuttaysa doğrudan döndür
        if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
            if not self.registry.is_file_duplicate(dest):
                return dest
            # Tekrar — eski dosyayı sil, yeniden indir
            try:
                os.remove(dest)
            except Exception:
                pass

        max_bytes = max_mb * 1024 * 1024
        for attempt in range(3):
            try:
                r = self.session.get(url, stream=True, timeout=35)
                if r.status_code != 200:
                    return None
                content_len = int(r.headers.get("content-length", 0))
                if content_len and content_len > max_bytes:
                    return None
                downloaded = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            break
                        f.write(chunk)
                if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
                    return dest
            except Exception as e:
                if attempt == 2:
                    logger.debug(f"[Download] Başarısız ({filename}): {e}")
                time.sleep(1)

        # Başarısız indirme — yarım dosyayı temizle
        try:
            if os.path.exists(dest):
                os.remove(dest)
        except Exception:
            pass
        return None
