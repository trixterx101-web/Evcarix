"""
audio_mixer.py — Evcarix
TTS sesi ile arka plan müziğini karıştırır.
Çıktı her zaman .m4a (AAC) formatındadır — .mp3 konteyner hatası yok.
"""
import subprocess
import os
import json
import logging

logger = logging.getLogger("AudioMixer")


def _probe_duration(path: str, default: float = 60.0) -> float:
    """ffprobe ile dosyanın süresini float olarak döndürür."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", path],
            capture_output=True, text=True, timeout=15
        )
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            dur = stream.get("duration")
            if dur:
                return float(dur)
    except Exception as e:
        logger.warning(f"[AudioMixer] ffprobe hatası ({os.path.basename(path)}): {e}")
    return default


def _to_aac_path(path: str) -> str:
    """
    Herhangi bir uzantıyı .m4a'ya çevirir.
    .mp3 konteynerine AAC yazmak geçersiz — her zaman .m4a kullan.
    """
    base = os.path.splitext(path)[0]
    return base + ".m4a"


def _reencode_as_aac(src: str, dst: str) -> str:
    """TTS'yi temiz AAC olarak yeniden encode eder. Başarısız olursa src döner."""
    cmd = [
        "ffmpeg", "-y", "-i", src,
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        dst
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 1000:
            logger.info(f"[AudioMixer] TTS re-encode başarılı: {os.path.basename(dst)}")
            return dst
    except Exception as e:
        logger.error(f"[AudioMixer] Re-encode exception: {e}")
    logger.warning("[AudioMixer] Re-encode başarısız, orijinal TTS kullanılıyor.")
    return src


def mix_audio(tts_path: str, music_path: str, output_path: str,
              music_volume: float = 0.12) -> str:
    """
    TTS sesi ile arka plan müziğini karıştırır.
    - Çıktı DAIMA .m4a (AAC) formatındadır.
    - Hiçbir zaman None döndürmez.
    - Her adımda fallback mevcuttur.

    Args:
        tts_path:     Giriş TTS ses dosyası
        music_path:   Arka plan müziği (opsiyonel)
        output_path:  İstenen çıktı yolu (.mp3 verilse bile .m4a'ya dönüştürülür)
        music_volume: Müzik ses seviyesi (0.0–1.0)

    Returns:
        Geçerli ses dosyasının yolu
    """
    # ── Giriş doğrulama ──────────────────────────────────────────────────────
    if not tts_path or not os.path.exists(tts_path):
        raise FileNotFoundError(f"[AudioMixer] TTS dosyası bulunamadı: {tts_path}")

    # Çıktı yolunu .m4a'ya zorla (.mp3 konteyner hatasını önle)
    aac_out = _to_aac_path(output_path)

    # TTS süresini ölç
    duration = _probe_duration(tts_path, default=60.0)
    logger.info(f"[AudioMixer] TTS süresi: {duration:.2f}s | Çıktı: {os.path.basename(aac_out)}")

    # ── Müzik yoksa sadece re-encode ─────────────────────────────────────────
    if not music_path or not os.path.exists(music_path):
        logger.info("[AudioMixer] Müzik yok — TTS re-encode ediliyor.")
        return _reencode_as_aac(tts_path, aac_out)

    # ── Karıştırma (atrim + amix) ────────────────────────────────────────────
    # atrim: müziği TTS süresiyle sınırlar (aloop boş stream sorununu önler)
    # stream_loop: müzik TTS'den kısaysa döngüye al
    filter_complex = (
        f"[1:a]atrim=0:{duration + 2},asetpts=PTS-STARTPTS,"
        f"volume={music_volume}[music];"
        f"[0:a]volume=1.0[voice];"
        f"[voice][music]amix=inputs=2:duration=first:dropout_transition=3[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", tts_path,
        "-stream_loop", "-1", "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "aac",       # Her zaman AAC — .m4a konteyner ile uyumlu
        "-b:a", "192k",
        "-ar", "44100",
        "-t", str(duration),
        aac_out
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if (result.returncode == 0
                and os.path.exists(aac_out)
                and os.path.getsize(aac_out) > 1000):
            logger.info(f"[AudioMixer] ✅ Karıştırma başarılı: {os.path.basename(aac_out)}")
            return aac_out

        logger.warning(f"[AudioMixer] Mix başarısız: {result.stderr[-300:]}")

    except Exception as e:
        logger.error(f"[AudioMixer] Mix exception: {e}")

    # ── Fallback: sadece TTS re-encode ───────────────────────────────────────
    logger.info("[AudioMixer] Fallback: müziksiz TTS re-encode.")
    return _reencode_as_aac(tts_path, aac_out)
