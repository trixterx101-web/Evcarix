import os
import re
import json
import subprocess
import logging

logger = logging.getLogger("Editor")


def _get_word_timings_whisper(audio_path: str) -> list:
    """
    Whisper ile ses dosyasını analiz et, her kelimenin
    başlangıç ve bitiş zamanını döndür.
    Returns: [{"word": "HELLO", "start": 0.0, "end": 0.5}, ...]
    """
    try:
        import whisper
        model = whisper.load_model("tiny")  # En hızlı model
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            language="en"
        )

        timings = []
        for segment in result.get("segments", []):
            for word_data in segment.get("words", []):
                word  = word_data.get("word", "").strip().upper()
                start = float(word_data.get("start", 0))
                end   = float(word_data.get("end", 0))
                if word:
                    timings.append({
                        "word":  word,
                        "start": round(start, 3),
                        "end":   round(end, 3)
                    })

        logger.info(f"[Editor] Whisper: {len(timings)} kelime zamanlandı")
        return timings

    except ImportError:
        logger.warning("[Editor] Whisper kurulu değil, pip install openai-whisper")
        return []
    except Exception as e:
        logger.warning(f"[Editor] Whisper hatası: {e}")
        return []


def _fallback_timings(text: str, duration: float) -> list:
    """
    Whisper yoksa eşit zaman dilimiyle fallback timing üret.
    """
    clean = re.sub(r"[^A-Z0-9 .,!?%\-']", "", text.upper()).strip()
    words = clean.split()
    if not words:
        return []

    word_dur = duration / len(words)
    timings  = []
    for i, w in enumerate(words):
        timings.append({
            "word":  w,
            "start": round(i * word_dur, 3),
            "end":   round((i + 1) * word_dur - 0.04, 3)
        })
    return timings


class AutoEditor:
    """
    Assembles multiple clips with word-level subtitle burn-in.
    Short (9:16): clips stacked, subtitles at bottom.
    Long (16:9): clips stacked full-width, subtitles at bottom.
    Whisper kullanarak ses ile tam senkron altyazı üretir.
    """

    def assemble(self, clips_paths, audio_path, output_path,
                 is_short=True, title=None, topic=None, words_with_times=None):
        try:
            logger.info(f"[Editor] {len(clips_paths)} klip birleştiriliyor, short={is_short}")

            duration = self._get_audio_duration(audio_path)
            logger.info(f"[Editor] Ses süresi: {duration:.1f}s")

            # Yeterli klip yoksa döngüye al
            clip_dur = 6
            needed   = max(1, int(duration / clip_dur) + 1)
            if len(clips_paths) < needed:
                clips_paths = (clips_paths * (needed // len(clips_paths) + 1))[:needed]

            W, H = (1080, 1920) if is_short else (1920, 1080)

            # ── Whisper ile kelime zamanlaması ────────────────────
            if words_with_times:
                # Dışarıdan geçirilmişse kullan
                timings = words_with_times
                logger.info(f"[Editor] Dışarıdan timing alındı: {len(timings)} kelime")
            else:
                logger.info("[Editor] Whisper ile timing analiz ediliyor...")
                timings = _get_word_timings_whisper(audio_path)
                if not timings:
                    logger.info("[Editor] Whisper yok, fallback timing kullanılıyor")
                    timings = _fallback_timings(title or "", duration)

            # ── Altyazı filtreleri ────────────────────────────────
            subtitle_filters = self._build_subtitles_from_timings(
                timings, W, H, is_short
            )

            # ── Filter complex ────────────────────────────────────
            inputs      = []
            scale_parts = []
            for i, clip in enumerate(clips_paths):
                inputs += ["-i", os.path.abspath(clip)]
                scale_parts.append(
                    f"[{i}:v]trim=duration={clip_dur},setpts=PTS-STARTPTS,"
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H},setsar=1,fps=24[v{i}]"
                )

            concat_inputs  = "".join(f"[v{i}]" for i in range(len(clips_paths)))

            # Altyazıları gruplara böl — FFmpeg komutunu kısa tut
            subtitle_chain = self._build_subtitle_chain(subtitle_filters)

            if subtitle_chain:
                fg = (
                    ";".join(scale_parts) + ";" +
                    concat_inputs +
                    f"concat=n={len(clips_paths)}:v=1:a=0[concat];" +
                    f"[concat]{subtitle_chain}[vout]"
                )
            else:
                fg = (
                    ";".join(scale_parts) + ";" +
                    concat_inputs +
                    f"concat=n={len(clips_paths)}:v=1:a=0[vout]"
                )

            temp_video = f"/tmp/temp_merged_{os.getpid()}.mp4"

            # Pass 1: Video + altyazı
            cmd_v = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", fg,
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-threads", "2", "-an",
                temp_video
            ]
            r = subprocess.run(cmd_v, capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                logger.error(f"[Editor] Pass 1 failed: {r.stderr[-400:]}")
                # Fallback: altyazısız dene
                return self._assemble_without_subtitles(
                    clips_paths, audio_path, output_path,
                    duration, clip_dur, W, H
                )

            # Pass 2: Ses ekle
            cmd_a = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-i", os.path.abspath(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(round(duration, 3)),
                "-shortest", output_path
            ]
            r2 = subprocess.run(cmd_a, capture_output=True, text=True, timeout=120)
            if r2.returncode != 0:
                logger.error(f"[Editor] Pass 2 failed: {r2.stderr[-400:]}")
                return False

            if os.path.exists(temp_video):
                os.remove(temp_video)

            logger.info(f"[Editor] ✅ Tamamlandı: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Hata: {e}")
            return False

    def _build_subtitles_from_timings(
        self, timings: list, W: int, H: int, is_short: bool
    ) -> list:
        """
        Whisper timing'e göre kelime kelime altyazı filtresi üret.
        Her kelime tam konuşulduğu anda ekrana gelir.
        """
        if not timings:
            return []

        font_size  = 72 if is_short else 56
        y_pos      = H - 200 if is_short else H - 130
        box_h      = font_size + 20
        box_y      = y_pos - 10

        filters = []
        for item in timings:
            word  = item.get("word", "").strip()
            t0    = item.get("start", 0)
            t1    = item.get("end", 0)

            if not word or t1 <= t0:
                continue

            # Güvenli metin
            safe = re.sub(r"[^A-Z0-9 .,!?%\-]", "", word.upper())
            safe = safe[:20].strip()
            safe = safe.replace("'", "").replace(":", "").replace("\\", "")

            if not safe:
                continue

            # Arka plan kutusu (okunabilirlik için)
            filters.append(
                f"drawbox="
                f"x=(w-tw)/2-10:y={box_y}:w=tw+20:h={box_h}:"
                f"color=black@0.6:t=fill:"
                f"enable='between(t\\,{t0}\\,{t1})'"
                f",drawtext=text='{safe}'"
                f":fontsize={font_size}"
                f":fontcolor=white"
                f":x=(w-tw)/2:y={y_pos}"
                f":shadowcolor=black@0.9:shadowx=3:shadowy=3"
                f":enable='between(t\\,{t0}\\,{t1})'"
            )

        return filters

    def _build_subtitle_chain(self, filters: list) -> str:
        """
        Çok fazla drawtext tek komutta patlıyor.
        Max 30 kelimelik gruplar halinde böl,
        her grup ayrı bir overlay katmanı olarak uygula.
        Toplam max 60 kelime göster (uzun video için yeterli).
        """
        if not filters:
            return ""

        # Max 60 filtre al (daha fazlası FFmpeg'i patlatır)
        filters = filters[:60]
        return ",".join(filters)

    def _assemble_without_subtitles(
        self, clips_paths, audio_path, output_path,
        duration, clip_dur, W, H
    ) -> str | bool:
        """Altyazısız fallback assembly."""
        logger.info("[Editor] Fallback: altyazısız montaj yapılıyor")
        try:
            inputs      = []
            scale_parts = []
            for i, clip in enumerate(clips_paths):
                inputs += ["-i", os.path.abspath(clip)]
                scale_parts.append(
                    f"[{i}:v]trim=duration={clip_dur},setpts=PTS-STARTPTS,"
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H},setsar=1,fps=24[v{i}]"
                )

            concat_inputs = "".join(f"[v{i}]" for i in range(len(clips_paths)))
            fg = (
                ";".join(scale_parts) + ";" +
                concat_inputs +
                f"concat=n={len(clips_paths)}:v=1:a=0[vout]"
            )

            temp = f"/tmp/temp_nosub_{os.getpid()}.mp4"
            cmd  = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", fg,
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-an", temp
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                return False

            cmd2 = [
                "ffmpeg", "-y",
                "-i", temp,
                "-i", os.path.abspath(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-t", str(round(duration, 3)), "-shortest",
                output_path
            ]
            r2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=120)
            if os.path.exists(temp):
                os.remove(temp)

            if r2.returncode == 0:
                logger.info(f"[Editor] ✅ Fallback tamamlandı: {output_path}")
                return output_path
            return False

        except Exception as e:
            logger.error(f"[Editor] Fallback hatası: {e}")
            return False

    def _get_audio_duration(self, path: str) -> float:
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            return float(r.stdout.strip())
        except:
            return 45.0
