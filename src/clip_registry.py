"""
clip_registry.py — Evcarix
Run'lar arası klip tekrarını önlemek için URL ve dosya hash'i takip eder.
used_clips.json GitHub Actions cache'inde saklanır.
"""
import json
import os
import hashlib
import logging

logger = logging.getLogger("ClipRegistry")
REGISTRY_PATH = "used_clips.json"
HASH_READ_BYTES = 65536  # İlk 64KB hash için yeterli


class ClipRegistry:
    """Hangi kliplerin kullanıldığını takip eder — run'lar arası kalıcı."""

    def __init__(self):
        self.registry = self._load()

    # ── Yükleme / Kaydetme ────────────────────────────────────────────────────
    def _load(self) -> dict:
        try:
            if os.path.exists(REGISTRY_PATH):
                with open(REGISTRY_PATH, "r") as f:
                    data = json.load(f)
                    # Eski format uyumluluğu
                    if "used_urls" not in data:
                        data["used_urls"] = []
                    if "used_hashes" not in data:
                        data["used_hashes"] = []
                    return data
        except Exception as e:
            logger.warning(f"[ClipRegistry] Registry yüklenemedi: {e}")
        return {"used_urls": [], "used_hashes": []}

    def save(self):
        try:
            with open(REGISTRY_PATH, "w") as f:
                json.dump(self.registry, f, indent=2)
        except Exception as e:
            logger.error(f"[ClipRegistry] Kayıt hatası: {e}")

    # ── Sorgulama ─────────────────────────────────────────────────────────────
    def is_used(self, url: str) -> bool:
        return url in self.registry["used_urls"]

    def is_file_duplicate(self, local_path: str) -> bool:
        if not os.path.exists(local_path):
            return False
        h = self._file_hash(local_path)
        return h in self.registry["used_hashes"]

    # ── İşaretleme ────────────────────────────────────────────────────────────
    def mark_used(self, url: str, local_path: str = None):
        if url and url not in self.registry["used_urls"]:
            self.registry["used_urls"].append(url)

        if local_path and os.path.exists(local_path):
            h = self._file_hash(local_path)
            if h not in self.registry["used_hashes"]:
                self.registry["used_hashes"].append(h)

        self.save()

    # ── Otomatik temizlik ─────────────────────────────────────────────────────
    def reset_if_exhausted(self, threshold: int = 500):
        """Registry dolduğunda en eski %50'yi sil."""
        total = len(self.registry["used_urls"])
        if total > threshold:
            half = total // 2
            logger.info(f"[ClipRegistry] Registry dolu ({total}), en eski {half} girdi siliniyor.")
            self.registry["used_urls"] = self.registry["used_urls"][half:]
            # Hash'leri de orantılı temizle
            h_half = len(self.registry["used_hashes"]) // 2
            self.registry["used_hashes"] = self.registry["used_hashes"][h_half:]
            self.save()

    # ── Yardımcı ─────────────────────────────────────────────────────────────
    def _file_hash(self, path: str) -> str:
        h = hashlib.md5()
        try:
            with open(path, "rb") as f:
                h.update(f.read(HASH_READ_BYTES))
        except Exception:
            return ""
        return h.hexdigest()

    def stats(self) -> str:
        return (f"[ClipRegistry] {len(self.registry['used_urls'])} URL, "
                f"{len(self.registry['used_hashes'])} hash takip ediliyor.")
