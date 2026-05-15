import subprocess
import os
import json
import logging

logger = logging.getLogger("AudioMixer")


def _get_audio_codec(output_path: str) -> str:
    """Dosya uzantısına göre doğru ses kodekini seçer."""
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".mp3":
        return "libmp3lame"
    return "aac"  # .aac, .m4a, .mp4 vb. için

def _get_duration(path: str, default: float = 60.0) -> float:
    """ffprobe ile dosya süresini float olarak döndürür."""
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", path],
            capture_output=True, text=True, timeout=15
        )
        info = json.loads(probe.stdout)
        for stream in info.get("streams", []):
            dur = stream.get("duration")
            if dur:
                return float(dur)
    except Exception as e:
        logger.warning(f"[AudioMixer] ffprobe süre alınamadı ({path}): {e}")
    return default


def _reencode_tts(tts_path: str, output_path: str) -> str:
    """TTS'yi temiz ses olarak yeniden encode eder — her zaman geçerli bir dosya döndürür."""
    codec = _get_audio_codec(output_path)
    cmd = [
        "ffmpeg", "-y", "-i", tts_path,
        "-c:a", codec, "-b:a", "192k", "-ar", "44100",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path
    logger.warning("[AudioMixer] Re-encode başarısız, orijinal TTS kullanılıyor.")
    return tts_path


def mix_audio(tts_path: str, music_path: str, output_path: str,
              music_volume: float = 0.12) -> str:
    """
    TTS sesi ile arka plan müziğini karıştırır.
    Her koşulda geçerli bir ses dosyası yolu döndürür (hiçbir zaman None).
    """
    # ── Giriş doğrulama ──────────────────────────────────────────────────────
    if not tts_path or not os.path.exists(tts_path):
        logger.error(f"[AudioMixer] TTS dosyası bulunamadı: {tts_path}")
        raise FileNotFoundError(f"[AudioMixer] TTS not found: {tts_path}")

    # TTS süresini ffprobe ile ölç
    duration = _get_duration(tts_path, default=60.0)
    logger.info(f"[AudioMixer] TTS süresi: {duration:.2f}s")

    # ── Müzik yoksa sadece TTS'yi re-encode et ───────────────────────────────
    if not music_path or not os.path.exists(music_path):
        logger.info("[AudioMixer] Müzik dosyası yok — TTS yeniden encode ediliyor.")
        return _reencode_tts(tts_path, output_path)

    # ── Karıştırma: atrim + amix (stream_loop ile güvenli) ───────────────────
    # Mix with music — uzantıya göre doğru codec
    codec = _get_audio_codec(output_path)
    filter_complex = (
        f"[1:a]atrim=0:{duration},asetpts=PTS-STARTPTS,volume={music_volume}[music];"
        f"[0:a]volume=1.0[voice];"
        f"[voice][music]amix=inputs=2:duration=first:dropout_transition=2[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", tts_path,
        "-stream_loop", "-1", "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", codec, "-b:a", "192k", "-ar", "44100",
        "-t", str(duration),
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if (result.returncode == 0
                and os.path.exists(output_path)
                and os.path.getsize(output_path) > 1000):
            logger.info(f"[AudioMixer] ✅ Karıştırma başarılı: {output_path}")
            return output_path

        # Mix başarısız → stderr'in son 400 karakterini logla
        logger.warning(f"[AudioMixer] ⚠️ Mix başarısız: {result.stderr[-400:]}")

    except Exception as e:
        logger.error(f"[AudioMixer] Mix exception: {e}")

    # ── Fallback: sadece TTS'yi temiz encode et ──────────────────────────────
    logger.info("[AudioMixer] Fallback: TTS yeniden encode ediliyor (müziksiz).")
    return _reencode_tts(tts_path, output_path)
