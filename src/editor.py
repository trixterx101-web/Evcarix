import os
import re
import subprocess
import logging

logger = logging.getLogger("Editor")


def _get_word_timings_whisper(audio_path: str) -> list:
    """Whisper ile kelime zamanlaması al."""
    try:
        import whisper
        model  = whisper.load_model("tiny")
        result = model.transcribe(audio_path, word_timestamps=True, language="en")
        timings = []
        for segment in result.get("segments", []):
            for wd in segment.get("words", []):
                word = wd.get("word", "").strip().upper()
                if word:
                    timings.append({
                        "word":  word,
                        "start": round(float(wd.get("start", 0)), 3),
                        "end":   round(float(wd.get("end", 0)), 3),
                    })
        logger.info(f"[Editor] Whisper: {len(timings)} kelime")
        return timings
    except ImportError:
        logger.warning("[Editor] openai-whisper kurulu degil")
        return []
    except Exception as e:
        logger.warning(f"[Editor] Whisper hatasi: {e}")
        return []


def _fallback_timings(text: str, duration: float) -> list:
    """Esit zaman dilimiyle fallback timing."""
    clean = re.sub(r"[^A-Z0-9 .,!?%\-']", "", text.upper()).strip()
    words = clean.split()
    if not words:
        return []
    wd = duration / len(words)
    return [
        {"word": w, "start": round(i * wd, 3), "end": round((i + 1) * wd - 0.04, 3)}
        for i, w in enumerate(words)
    ]


def _write_srt(timings: list, srt_path: str):
    """
    Kelime zamanlamalarini SRT dosyasina yaz.
    Her satirda max 4 kelime.
    """
    groups = []
    chunk  = []
    for item in timings:
        chunk.append(item)
        if len(chunk) == 4:
            groups.append(chunk)
            chunk = []
    if chunk:
        groups.append(chunk)

    def fmt_time(s: float) -> str:
        h  = int(s // 3600)
        m  = int((s % 3600) // 60)
        sc = s % 60
        return f"{h:02d}:{m:02d}:{sc:06.3f}".replace(".", ",")

    lines = []
    for i, group in enumerate(groups):
        t0   = group[0]["start"]
        t1   = group[-1]["end"]
        text = " ".join(item["word"] for item in group)
        text = re.sub(r"[^A-Z0-9 .,!?%\-]", "", text)[:80]
        lines.append(f"{i+1}")
        lines.append(f"{fmt_time(t0)} --> {fmt_time(t1)}")
        lines.append(text)
        lines.append("")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


class AutoEditor:
    """
    Klipleri birlestir + Whisper ile senkron altyazi ekle.
    Altyazilar SRT dosyasiyla FFmpeg subtitles filtresine gecilir.
    Bu yontem FFmpeg komutunu asla patlatmaz.
    """

    def assemble(self, clips_paths, audio_path, output_path,
                 is_short=True, title=None, topic=None, words_with_times=None):
        try:
            logger.info(f"[Editor] {len(clips_paths)} klip, short={is_short}")

            duration = self._get_audio_duration(audio_path)
            logger.info(f"[Editor] Ses: {duration:.1f}s")

            clip_dur = 6
            needed   = max(1, int(duration / clip_dur) + 1)
            if len(clips_paths) < needed:
                clips_paths = (clips_paths * (needed // len(clips_paths) + 1))[:needed]

            W, H = (1080, 1920) if is_short else (1920, 1080)

            # Whisper timing
            if words_with_times:
                timings = words_with_times
            else:
                timings = _get_word_timings_whisper(audio_path)
                if not timings:
                    timings = _fallback_timings(title or "", duration)

            # SRT dosyasi yaz
            srt_path = f"/tmp/subs_{os.getpid()}.srt"
            _write_srt(timings, srt_path)

            # Filter complex
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

            temp_video = f"/tmp/temp_merged_{os.getpid()}.mp4"

            # Pass 1: Klipleri birlestir
            cmd_v = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", fg,
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-threads", "2", "-an",
                temp_video
            ]
            r = subprocess.run(cmd_v, capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                logger.error(f"[Editor] Pass 1 failed: {r.stderr[-300:]}")
                return False

            # Pass 2: Altyazi ekle (SRT ile)
            font_size   = 22 if is_short else 18
            sub_filter  = (
                f"subtitles={srt_path}:"
                f"force_style='FontName=Arial,"
                f"FontSize={font_size},"
                f"PrimaryColour=&HFFFFFF,"
                f"OutlineColour=&H000000,"
                f"Outline=2,Shadow=1,"
                f"Alignment=2,MarginV=40'"
            )

            temp_subbed = f"/tmp/temp_subbed_{os.getpid()}.mp4"
            cmd_sub = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-vf", sub_filter,
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
                "-pix_fmt", "yuv420p", "-an",
                temp_subbed
            ]
            r_sub = subprocess.run(cmd_sub, capture_output=True, text=True, timeout=300)

            if r_sub.returncode != 0:
                logger.warning(f"[Editor] Altyazi eklenemedi: {r_sub.stderr[-200:]}")
                temp_subbed = temp_video  # altyazisiz devam

            # Pass 3: Ses ekle
            cmd_a = [
                "ffmpeg", "-y",
                "-i", temp_subbed,
                "-i", os.path.abspath(audio_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(round(duration, 3)),
                "-shortest", output_path
            ]
            r2 = subprocess.run(cmd_a, capture_output=True, text=True, timeout=120)

            # Temizlik
            for f in [temp_video, temp_subbed, srt_path]:
                try:
                    if os.path.exists(f):
                        os.remove(f)
                except:
                    pass

            if r2.returncode == 0 and os.path.exists(output_path):
                logger.info(f"[Editor] done: {output_path}")
                return output_path

            logger.error(f"[Editor] Pass 3 failed: {r2.stderr[-300:]}")
            return False

        except Exception as e:
            logger.error(f"[Editor] Hata: {e}")
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
