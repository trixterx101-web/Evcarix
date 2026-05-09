"""
Evcarix YouTube Shorts Automation Pipeline Configuration
API keys and settings loaded from environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── API Keys ───────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
KLING_ACCESS_KEY = os.getenv("KLING_ACCESS_KEY")
KLING_SECRET_KEY = os.getenv("KLING_SECRET_KEY")
GEMINIGEN_API_KEY = os.getenv("GEMINIGEN_API_KEY")

# ── YouTube Configuration ──────────────────────────────────────────────────────
YOUTUBE_CLIENT_SECRET_PATH = os.getenv("YOUTUBE_CLIENT_SECRET_PATH", "client_secret.json")
YOUTUBE_TOKEN_PATH = os.getenv("YOUTUBE_TOKEN_PATH", "token.json")
CHANNEL_ID = os.getenv("CHANNEL_ID", "UC_YOUR_CHANNEL_ID")

# ── Video Settings ───────────────────────────────────────────────────────────────
# Short video (YouTube Shorts, TikTok, Reels)
SHORT_VIDEO_DURATION_MIN = 25  # seconds
SHORT_VIDEO_DURATION_MAX = 50  # seconds

# Long video (YouTube normal)
LONG_VIDEO_DURATION_MIN = 180  # seconds (3 minutes)
LONG_VIDEO_DURATION_MAX = 240  # seconds (4 minutes)

# Legacy settings (for backward compatibility)
VIDEO_DURATION_MIN = 25  # seconds
VIDEO_DURATION_MAX = 50  # seconds

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # 9:16 vertical format
VIDEO_FPS = 30

# ── Thumbnail Settings ───────────────────────────────────────────────────────────
THUMBNAIL_WIDTH = 1080
THUMBNAIL_HEIGHT = 1920  # 9:16 vertical format
THUMBNAIL_QUALITY = "4K"  # SDXL/Flux quality

# ── Language Settings ───────────────────────────────────────────────────────────
DEFAULT_LANGUAGE = "en"  # English ONLY
SUPPORTED_LANGUAGES = ["en"]

# ── Content Settings ─────────────────────────────────────────────────────────────
ENABLE_TURKISH_TITLES = False  # English ONLY
ENABLE_GLOBAL_CONTENT = True  # Use USA, Europe, China examples only (no Turkey)
ENABLE_AI_VIDEO_FALLBACK = False  # Kling AI/Runway (requires API key)
ENABLE_STABILITY_AI = False  # Stability AI for thumbnails (requires API key)

# ── Output Settings ─────────────────────────────────────────────────────────────
OUTPUT_DIR = "output"
TEMP_DIR = "assets/temp"
THUMBNAIL_DIR = "output/thumbnails"

# ── Validation ───────────────────────────────────────────────────────────────────
def validate_config():
    """Validate required API keys are present."""
    required_keys = {
        "GROQ_API_KEY": GROQ_API_KEY,
        "PEXELS_API_KEY": PEXELS_API_KEY,
        "PIXABAY_API_KEY": PIXABAY_API_KEY,
    }

    missing_keys = [k for k, v in required_keys.items() if not v]
    if missing_keys:
        print(f"⚠️  Missing required API keys: {', '.join(missing_keys)}")
        print("Please add them to your .env file")
        return False

    # Optional keys warnings
    optional_keys = {
        "STABILITY_API_KEY": STABILITY_API_KEY,
        "REPLICATE_API_KEY": REPLICATE_API_KEY,
        "KLING_ACCESS_KEY": KLING_ACCESS_KEY,
        "KLING_SECRET_KEY": KLING_SECRET_KEY,
        "GEMINIGEN_API_KEY": GEMINIGEN_API_KEY,
    }

    missing_optional = [k for k, v in optional_keys.items() if not v]
    if missing_optional:
        print(f"ℹ️  Optional API keys not set: {', '.join(missing_optional)}")
        print("Some features may be limited")

    return True

if __name__ == "__main__":
    validate_config()
