import os
import json
import random
import feedparser
import requests
import pandas as pd
from datetime import datetime

try:
    from google import genai
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

TOPIC_HISTORY_FILE = "used_topics.json"
TOPIC_HISTORY_LIMIT = 14  # Son 14 konu tekrar edilmez


class TrendEngine:
    def __init__(self):
        self.feeds = [
            "https://electrek.co/feed/",
            "https://insideevs.com/rss/articles/all/",
            "https://www.teslarati.com/feed/",
            "https://ev-database.org/rss.xml",
            "https://www.greencarreports.com/rss/news",
            "https://cleantechnica.com/feed/",
        ]
        # EV konularında YouTube arama terimleri — her çalışmada farklısı seçilir
        self.ev_search_queries = [
            "electric car range test",
            "EV battery technology 2024",
            "Tesla vs competition real world",
            "electric vehicle charging speed comparison",
            "EV battery degradation data",
            "best electric cars 2024 real test",
            "solid state battery breakthrough",
            "electric car ownership cost analysis",
            "BYD electric car range test",
            "EV winter range cold weather",
            "800V charging electric car comparison",
            "electric car efficiency wh per mile",
            "EV vs hybrid total cost",
            "electric vehicle battery life test",
            "fast charging impact battery health",
        ]
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") if GEMINI_AVAILABLE else None
        self.gemini_client = None
        if GEMINI_AVAILABLE and self.gemini_api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
            except Exception as e:
                print(f"[TrendEngine] Gemini init hatası: {e}")
                self.gemini_client = None

    # ─── Konu Geçmişi ─────────────────────────────────────────────────────────
    def _load_topic_history(self):
        """Daha önce kullanılan konuları yükler."""
        if os.path.exists(TOPIC_HISTORY_FILE):
            try:
                with open(TOPIC_HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_topic_history(self, topic):
        """Kullanılan konuyu geçmişe ekler, limitin üstündekini siler."""
        history = self._load_topic_history()
        if topic in history:
            history.remove(topic)
        history.append(topic)
        history = history[-TOPIC_HISTORY_LIMIT:]
        with open(TOPIC_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _is_used_recently(self, topic):
        """Bu konu son TOPIC_HISTORY_LIMIT içinde kullanıldı mı?"""
        history = self._load_topic_history()
        topic_lower = topic.lower()
        for h in history:
            if h.lower() in topic_lower or topic_lower in h.lower():
                return True
        return False

    # ─── RSS Haberleri ─────────────────────────────────────────────────────────
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

    # ─── YouTube Trending (Autos Kategorisi) ───────────────────────────────────
    def get_youtube_trending(self, region_code="US", max_results=20):
        """YouTube Data API'den en popüler Autos & Vehicles videolarını çeker."""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            print("[TrendEngine] YOUTUBE_API_KEY bulunamadı, trending atlanıyor.")
            return []
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': region_code,
            'videoCategoryId': '2',  # Autos & Vehicles
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

    # ─── YouTube EV Keyword Araması ────────────────────────────────────────────
    def get_youtube_ev_search(self, max_results=20):
        """EV anahtar kelimeleriyle en çok izlenen YouTube videolarını arar."""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            return []
        # Her seferinde farklı bir arama terimi seç
        query = random.choice(self.ev_search_queries)
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'order': 'viewCount',
            'relevanceLanguage': 'en',
            'maxResults': max_results,
            'key': api_key
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            results = []
            for it in r.json().get('items', []):
                snip = it.get('snippet', {})
                results.append({
                    'title': snip.get('title', ''),
                    'channelTitle': snip.get('channelTitle', ''),
                    'videoId': it.get('id', {}).get('videoId', ''),
                    'query_used': query
                })
            print(f"[TrendEngine] YouTube EV araması '{query}': {len(results)} sonuç")
            return results
        except Exception as e:
            print(f"[TrendEngine] YouTube EV arama hatası: {e}")
            return []

    # ─── Ana Konu Seçici ───────────────────────────────────────────────────────
    def select_trending_topic(self, news_df):
        """Her seferinde farklı, geçmişte kullanılmamış EV konusu seçer.
        Öncelik: YouTube EV Arama > YouTube Trending > Gemini RSS > Core Fallback
        """
        ev_keywords = [
            'ev', 'electric', 'battery', 'tesla', 'range', 'charging',
            'volt', 'watt', 'efficiency', 'byd', 'ioniq', 'rivian', 'lucid',
            'solid state', 'lithium', 'kwh', 'kilowatt', 'hybrid', 'motor'
        ]

        def is_ev_related(title):
            t = title.lower()
            return any(word in t for word in ev_keywords)

        # 1) YouTube EV Keyword Araması — En Yüksek Öncelik
        yt_ev = self.get_youtube_ev_search(max_results=20)
        random.shuffle(yt_ev)  # Her seferinde farklı sıra
        for item in yt_ev:
            title = item['title']
            if is_ev_related(title) and not self._is_used_recently(title):
                clean = title.encode('ascii', 'ignore').decode('ascii')
                print(f"[TrendEngine] YouTube EV search selected: {clean}")
                self._save_topic_history(title)
                return title

        # 2) YouTube Trending (Autos Kategorisi)
        yt = self.get_youtube_trending(region_code=os.getenv('YOUTUBE_REGION', 'US'))
        candidates = [i for i in yt if is_ev_related(i['title'])]
        random.shuffle(candidates)
        for item in candidates:
            title = item['title']
            if not self._is_used_recently(title):
                clean = title.encode('ascii', 'ignore').decode('ascii')
                print(f"[TrendEngine] YouTube trending selected: {clean}")
                self._save_topic_history(title)
                return title

        # 3) Gemini — RSS Haberlerinden Seçim
        if GEMINI_AVAILABLE and self.gemini_client and news_df is not None and not news_df.empty:
            try:
                titles = news_df['title'].tolist()
                random.shuffle(titles)
                unused = [t for t in titles if not self._is_used_recently(t)]
                pool = (unused if unused else titles)[:20]
                prompt = (
                    "You are a technical EV analyst for the 'Evcarix' channel. "
                    "Pick the ONE most data-driven, technical, or performance-related headline. "
                    "Focus on batteries, range, charging, efficiency, or real-world tests. "
                    "Return ONLY the headline text.\n\n"
                    + "\n".join(f"- {t}" for t in pool)
                )
                response = self.gemini_client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=prompt
                )
                selected = response.text.strip()
                if any(t.lower() in selected.lower() or selected.lower() in t.lower() for t in pool):
                    print(f"[TrendEngine] Gemini RSS selection: {selected}")
                    self._save_topic_history(selected)
                    return selected
            except Exception as e:
                print(f"[TrendEngine] Gemini error: {e}")

        # 4) Geniş Core Topics Fallback — Geçmişte kullanılmayanı seç
        core_topics = [
            "Real-world EV range test vs manufacturer claims",
            "Battery degradation: LFP vs NMC after 100k miles",
            "Winter range loss in modern electric cars: real data",
            "EV charging speed: 400V vs 800V architecture comparison",
            "True cost of EV ownership over 100k miles",
            "Heat pump efficiency in extreme cold weather",
            "Solid-state battery progress: real timeline and data",
            "EV efficiency: Wh/km breakdown by model",
            "Tesla Model 3 vs BYD Seal: head-to-head efficiency test",
            "Hyundai IONIQ 6 real-world range: the real numbers",
            "EV battery warranty: what manufacturers don't tell you",
            "DC fast charging impact on battery health: long-term data",
            "Rivian R1T range in cold weather: real test results",
            "EV vs hybrid: total cost comparison over 5 years",
            "Home charging vs public charging costs: full breakdown",
            "LFP battery advantages: why BYD keeps winning on cost",
            "800V ultra-fast charging: which EVs actually support it",
            "EV depreciation rates: which models hold value best",
            "Regenerative braking efficiency: how much range does it add",
            "Used EV battery health: how to check before buying",
        ]
        unused_core = [t for t in core_topics if not self._is_used_recently(t)]
        pool = unused_core if unused_core else core_topics
        selected_core = random.choice(pool)
        print(f"[TrendEngine] Core concept fallback: {selected_core}")
        self._save_topic_history(selected_core)
        return selected_core


if __name__ == "__main__":
    engine = TrendEngine()
    news = engine.get_latest_news()
    print(news[['title', 'source']].head())
    print(engine.select_trending_topic(news))
