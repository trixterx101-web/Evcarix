import subprocess
import os
import logging

logger = logging.getLogger("AudioMixer")

def mix_audio(tts_path: str, music_path: str, output_path: str, music_volume: float = 0.12) -> str:
    """
    Mix TTS voice with background music robustly using FFmpeg.
    Returns output_path if success, tts_path if fails (voice only fallback).
    """
    if not tts_path or not os.path.exists(tts_path):
        logger.error(f"[AudioMixer] TTS file not found: {tts_path}")
        return None
    
    # If no music, just return TTS
    if not music_path or not os.path.exists(music_path):
        logger.info("[AudioMixer] No music file, using TTS only")
        return tts_path
    
    try:
        # filter_complex explains:
        # [1:a] loop the music infinitely, then apply volume
        # amix: mix both, duration=first (ends when TTS ends)
        cmd = [
            "ffmpeg", "-y",
            "-i", tts_path,
            "-i", music_path,
            "-filter_complex",
            f"[1:a]volume={music_volume},aloop=loop=-1:size=2e+09[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.warning(f"[AudioMixer] ⚠️ Mix failed: {result.stderr[-200:]}")
            logger.info("[AudioMixer] Fallback: using TTS only")
            return tts_path
        
        logger.info(f"[AudioMixer] ✅ Mixed audio successfully: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"[AudioMixer] Mix fatal error: {e}")
        return tts_path
