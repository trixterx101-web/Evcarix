import os
import re
import subprocess
import logging

logger = logging.getLogger("Editor")

class AutoEditor:
    """
    Assembles multiple clips with word-level subtitle burn-in.
    Short (9:16): clips stacked, subtitles at bottom.
    Long (16:9): clips stacked full-width, subtitles at bottom, NO side panel.
    """

    def assemble(self, clips_paths, audio_path, output_path,
                 is_short=True, title=None, topic=None, words_with_times=None):
        try:
            logger.info(f"[Editor] Assembling {len(clips_paths)} clips, short={is_short}")

            duration = self._get_audio_duration(audio_path)
            logger.info(f"[Editor] Audio duration: {duration:.1f}s")

            # Make sure we have enough clips — loop if needed
            clip_dur  = 6  # seconds per clip
            needed    = max(1, int(duration / clip_dur) + 1)
            if len(clips_paths) < needed:
                clips_paths = (clips_paths * (needed // len(clips_paths) + 1))[:needed]

            W, H = (1080, 1920) if is_short else (1920, 1080)

            # ── Build subtitle filters (word-level) ──────────────
            script_text = title or ""
            subtitle_filters = self._build_subtitles(script_text, duration, W, H, is_short)

            # ── Build filter_complex ──────────────────────────────
            inputs = []
            scale_parts = []
            for i, clip in enumerate(clips_paths):
                inputs += ["-i", os.path.abspath(clip)]
                scale_parts.append(
                    f"[{i}:v]trim=duration={clip_dur},setpts=PTS-STARTPTS,"
                    f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                    f"crop={W}:{H},setsar=1,fps=24[v{i}]"
                )

            concat_inputs = "".join(f"[v{i}]" for i in range(len(clips_paths)))
            subtitle_chain = ",".join(subtitle_filters) if subtitle_filters else ""

            if subtitle_chain:
                fg = (
                    ";".join(scale_parts) + ";" +
                    concat_inputs + f"concat=n={len(clips_paths)}:v=1:a=0[concat];" +
                    f"[concat]{subtitle_chain}[vout]"
                )
            else:
                fg = (
                    ";".join(scale_parts) + ";" +
                    concat_inputs + f"concat=n={len(clips_paths)}:v=1:a=0[vout]"
                )

            temp_video = f"/tmp/temp_merged_{os.getpid()}.mp4"

            # Pass 1: video assembly with subtitles
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
                return False

            # Pass 2: mux with audio, trim to exact duration
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

            logger.info(f"[Editor] ✅ Done: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[Editor] Error: {e}")
            return False

    def _build_subtitles(self, text: str, duration: float, W: int, H: int, is_short: bool) -> list:
        """Word-level subtitle burn-in — strict non-overlapping time slices."""
        clean = re.sub(r"[^A-Z0-9 .,!?%\-']", "", text.upper()).strip()
        words = clean.split()
        if not words:
            return []

        font_size = 68 if is_short else 52
        y_pos     = H - 180 if is_short else H - 120

        # Equal slice per word, no +0.3 tail that caused stacking
        word_dur = duration / len(words)

        filters = []
        for i, w in enumerate(words):
            t0 = round(i * word_dur, 3)
            t1 = round((i + 1) * word_dur - 0.04, 3)  # 40ms gap = no overlap
            safe_w = w.replace("'", "\\'")
            filters.append(
                f"drawtext=text='{safe_w}'"
                f":fontsize={font_size}:fontcolor=white"
                f":x=(w-tw)/2:y={y_pos}"
                f":shadowcolor=black@0.9:shadowx=3:shadowy=3"
                f":enable='between(t\\,{t0}\\,{t1})'"
            )
        return filters

    def _get_audio_duration(self, path: str) -> float:
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", path]
            r = subprocess.run(cmd, capture_output=True, text=True)
            return float(r.stdout.strip())
        except:
            return 45.0
