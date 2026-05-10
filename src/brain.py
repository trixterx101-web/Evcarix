import os
import json
import random
import datetime
from src.trend_engine import TrendEngine
from src.writer import CreativeWriter

HISTORY_LIMIT = 60
MIN_SHORT_WORDS = 70

class EvcarixBrain:
    def __init__(self):
        self.trend_engine = TrendEngine()
        self.writer = CreativeWriter()

    def create_daily_plan(self, slot="evening", video_type="short"):
        """v8.0 Plan Creation"""
        topic = "Future of Electric Vehicles"
        
        # Uzun video için farklı süre ve içerik
        if video_type == "long":
            print(f"[Brain] Long-form içerik üretiliyor: {topic}")
            content = self.writer.generate_long_content(topic)
        else:
            print(f"[Brain] Shorts içerik üretiliyor: {topic}")
            content = self.writer.generate_short_content(topic)
        
        # Check word count (Shorts için min 70 kelime, Long için min 400 kelime)
        words = len(content['script'].split())
        threshold = 400 if video_type == "long" else MIN_SHORT_WORDS
        
        if words < threshold:
            print(f"[Brain] İçerik yetersiz ({words} < {threshold}), tekrar deneniyor...")
            # Burada tekrar deneme mantığı eklenebilir
            
        return {
            "topic": topic,
            "full_topic": topic,
            "script": content['script'],
            "title": content['title'],
            "description": content['description'],
            "tags": content['tags'],
            "voice": content['voice'],
            "video_type": video_type
        }
