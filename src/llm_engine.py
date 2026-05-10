"""
src/llm_engine.py — Legacy Proxy
=================================
This file now proxies calls to the new v8.0 writer.py and disables old features.
"""

from src.writer import generate_title, generate_script, generate_tags

def search_youtube_cc(*args, **kwargs):
    """DISABLED in v8.0"""
    return []

def collect_media(*args, **kwargs):
    """DEPRECATED: Use MediaEngine directly."""
    return []
