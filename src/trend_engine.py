import os
import feedparser
import requests
import pandas as pd
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


class TrendEngine:
    def __init__(self):
        self.feeds = [
            "https://electrek.co/feed/",
            "https://insideevs.com/rss/articles/all/",
            "https://www.teslarati.com/feed/",
            "https://ev-database.org/rss.xml"
        ]
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") if GEMINI_AVAILABLE else None
        if GEMINI_AVAILABLE and self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')

    def get_latest_news(self):
        """Haber kaynaklarından en son haberleri çeker."""
        news_items = []
        for url in self.feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    news_items.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.summary if 'summary' in entry else "",
                        "published": entry.published if 'published' in entry else datetime.now().isoformat(),
                        "source": url.split("//")[1].split("/")[0]
                    })
            except Exception as e:
                print(f"Feed hatası ({url}): {e}")
        return pd.DataFrame(news_items)

    def get_youtube_trending(self, region_code="US", max_results=10):
        """YouTube Data API'den en popüler videoları çeker."""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            print("[TrendEngine] YOUTUBE_API_KEY bulunamadı, trending atlanıyor.")
            return []
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': region_code,
            'videoCategoryId': '2', # Autos & Vehicles
            'maxResults': max_results,
            'key': api_key
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            trending = []
            for it in r.json().get('items', []):
                snip = it.get('snippet', {})
                stats = it.get('statistics', {})
                trending.append({
                    'title': snip.get('title', ''),
                    'channelTitle': snip.get('channelTitle', ''),
                    'videoId': it.get('id'),
                    'viewCount': int(stats.get('viewCount', 0)) if stats.get('viewCount') else 0
                })
            return sorted(trending, key=lambda x: x['viewCount'], reverse=True)
        except Exception as e:
            print(f"[TrendEngine] YouTube trending hatası: {e}")
            return []

    def select_trending_topic(self, news_df):
        """Selects a topic that aligns with Evcarix: No hype, just numbers.
        Hierarchy: YouTube Trending > Gemini (from RSS) > Core Topics Fallback
        """
        
        # 1) YouTube Trending (Autos Category) - Highest Priority
        yt = self.get_youtube_trending(region_code=os.getenv('YOUTUBE_REGION', 'US'))
        if yt:
            for item in yt:
                title = item['title']
                # Filter to ensure it's EV or car related
                if any(word in title.lower() for word in ['ev', 'electric', 'battery', 'tesla', 'range', 'car', 'volt', 'watt', 'efficiency']):
                    print(f"[TrendEngine] YouTube technical trend selected: {title}")
                    return title

        # 2) Gemini Selection from RSS News - Secondary Priority
        if GEMINI_AVAILABLE and self.gemini_api_key and news_df is not None and not news_df.empty:
            try:
                titles = news_df.head(15)['title'].tolist()
                prompt = (
                    "You are a technical EV analyst for the 'Evcarix' channel. "
                    "Pick the ONE most data-driven, technical, or performance-related headline from this list. "
                    "Avoid generic hype or political news. Focus on batteries, range, charging, or efficiency. "
                    "Return ONLY the headline text.\n\n"
                    + "\n".join(f"- {t}" for t in titles)
                )
                response = self.gemini_model.generate_content(prompt)
                selected = response.text.strip()
                # Validate selection matches one of the titles (loosely)
                if any(t.lower() in selected.lower() or selected.lower() in t.lower() for t in titles):
                    print(f"[TrendEngine] Technical news selected via Gemini: {selected}")
                    return selected
            except Exception as e:
                print(f"[TrendEngine] Gemini error: {e}")

        # 3) Diverse Fallback from Core Topics
        core_topics = [
            "Real-world EV range test results",
            "Battery degradation analysis: LFP vs NMC",
            "Winter range loss in modern electric cars",
            "EV charging speed comparison: 400V vs 800V",
            "The true cost of EV ownership over 100k miles",
            "Heat pump efficiency in extreme cold",
            "Solid-state battery progress and data",
            "EV efficiency: Wh/km breakdown by model"
        ]
        import random
        selected_core = random.choice(core_topics)
        print(f"[TrendEngine] Using core concept fallback: {selected_core}")
        return selected_core


if __name__ == "__main__":
    engine = TrendEngine()
    news = engine.get_latest_news()
    print(news[['title', 'source']].head())
    print(engine.select_trending_topic(news))
