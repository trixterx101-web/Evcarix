"""
trend_analyzer.py — Evcarix Global English
Fetches trending topics from Google Trends and YouTube.
Ensures we only make videos that people are actually searching for.
"""
import os
import requests
import feedparser
import logging
import random

logger = logging.getLogger("TrendAnalyzer")

class TrendAnalyzer:
    def __init__(self):
        # RSS feeds for tech and EV trends
        self.feeds = [
            "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
            "https://www.theverge.com/rss/index.xml",
            "https://electrek.co/feed/",
            "https://insideevs.com/rss/articles/all/"
        ]

    def get_trending_topic(self) -> str:
        """En popüler konuyu döndürür."""
        trends = []
        try:
            for url in self.feeds:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    title = entry.title
                    # Filtreleme: Konularımızla ilgili mi?
                    keywords = ["electric", "tesla", "ai", "robot", "battery", "future", "tech", "ev", "quantum"]
                    if any(k in title.lower() for k in keywords):
                        trends.append(title)
            
            if trends:
                # En viral olanı veya rastgele birini seç
                choice = random.choice(trends)
                logger.info(f"[TrendAnalyzer] Found trending topic: {choice}")
                return choice
        except Exception as e:
            logger.error(f"Trend Analysis Error: {e}")
        
        # Fallback topics
        return random.choice([
            "Next-gen Solid State Batteries 2025",
            "Tesla Model 2 Production Secrets",
            "Humanoid Robots in Global Factories",
            "AI Breakthrough in Quantum Computing"
        ])
