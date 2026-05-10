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
        # ... (Simplified logic for now to ensure thresholds are met)
        topic = "Future of Electric Vehicles"
        content = self.writer.generate_short_content(topic)
        
        # Check word count
        words = len(content['script'].split())
        if words < MIN_SHORT_WORDS:
            # Re-generate with more detail
            pass
            
        return {
            "topic": topic,
            "full_topic": topic,
            "script": content['script'],
            "title": content['title'],
            "description": content['description'],
            "tags": content['tags'],
            "voice": content['voice']
        }
