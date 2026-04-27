import feedparser
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

class TrendEngine:
    def __init__(self):
        self.feeds = [
            "https://electrek.co/feed/",
            "https://insideevs.com/rss/articles/all/",
            "https://www.teslarati.com/feed/",
            "https://ev-database.org/rss.xml"
        ]

    def get_latest_news(self):
        """Haber kaynaklarından en son haberleri çeker."""
        news_items = []
        for url in self.feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]: # Her kaynaktan son 5 haber
                    news_items.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.summary if 'summary' in entry else "",
                        "published": entry.published if 'published' in entry else datetime.now().isoformat(),
                        "source": url.split("//")[1].split("/")[0]
                    })
            except Exception as e:
                print(f"Hata ({url}): {e}")
        
        return pd.DataFrame(news_items)

    def select_trending_topic(self, news_df):
        """Haberler arasından en dikkat çekici olanı seçer (Basit mantık: Başlık uzunluğu veya anahtar kelime)."""
        # Burada Gemini API da kullanılabilir haberleri özetleyip trendi seçmek için
        if news_df.empty:
            return "General EV Trends and Innovation"
        
        # En yeni haberi seçelim şimdilik
        return news_df.iloc[0]['title']

if __name__ == "__main__":
    engine = TrendEngine()
    news = engine.get_latest_news()
    print("Son Haberler:")
    print(news[['title', 'source']].head())
    trend = engine.select_trending_topic(news)
    print(f"\nSeçilen Trend: {trend}")
