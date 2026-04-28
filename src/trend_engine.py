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
                print(f"Feed error ({url}): {e}")
        return pd.DataFrame(news_items)

    def get_youtube_trending(self, region_code="US", max_results=10):
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            print("[TrendEngine] YOUTUBE_API_KEY not set, skipping trending.")
            return []
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': region_code,
            'maxResults': max_results,
            'key': api_key
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            trending = []
            for it in data.get('items', []):
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
            print(f"[TrendEngine] YouTube trending error: {e}")
            return []

    def select_trending_topic(self, news_df):
        if news_df is None or news_df.empty:
            return "General EV Trends and Innovation"

        # 1) YouTube Trending
        yt = self.get_youtube_trending(region_code=os.getenv('YOUTUBE_REGION', 'US'))
        if yt:
            top = yt[0]
            print(f"[TrendEngine] YouTube trending selected: {top['title']}")
            return top['title']

        # 2) Gemini fallback
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                titles = news_df.head(10)['title'].tolist()
                prompt = (
                    "From the following EV news headlines, pick the ONE most likely to trend on YouTube today. "
                    "Return ONLY the headline text, nothing else.\n\n"
                    + "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
                )
                response = self.gemini_model.generate_content(prompt)
                selected = response.text.strip()
                for t in titles:
                    if t.lower() in selected.lower() or selected.lower() in t.lower():
                        print(f"[TrendEngine] Gemini selected: {t}")
                        return t
            except Exception as e:
                print(f"[TrendEngine] Gemini error: {e}")

        # 3) RSS fallback
        return news_df.iloc[0]['title']
