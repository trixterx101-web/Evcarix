"""
content_discovery.py — v1.0
Tamamen ücretsiz içerik keşif modülü. Hiçbir ücretli API kullanmaz.
Kaynaklar: Google Trends RSS, Reddit RSS, Wikipedia API, Arxiv RSS, EV Haber RSS
"""
import os, re, json, random, logging, requests, feedparser
from datetime import datetime

logger = logging.getLogger("ContentDiscovery")

REDDIT_SUBREDDITS = [
    "todayilearned", "interestingasfuck", "Futurology",
    "ElectricVehicles", "technology", "science", "artificial"
]
ARXIV_FEEDS = [
    "https://rss.arxiv.org/rss/cs.AI",
    "https://rss.arxiv.org/rss/cs.RO",
    "https://rss.arxiv.org/rss/eess.SY",
]
EV_NEWS_FEEDS = [
    ("https://electrek.co/feed/", "Electrek"),
    ("https://insideevs.com/rss/articles/all/", "InsideEVs"),
    ("https://cleantechnica.com/feed/", "CleanTechnica"),
    ("https://www.greencarreports.com/rss/news", "GreenCarReports"),
]
BLOCKED = ["kardashian","celebrity","gossip","sport","nfl","nba","cooking",
           "recipe","fashion","makeup","nsfw","gambling"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EvcarixBot/1.0)"}


class ContentDiscovery:
    def __init__(self):
        self.history_file = "content_history.json"
        self._history = self._load_history()

    def _load_history(self) -> set:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return set(json.load(f).get("used_titles", []))
            except Exception:
                return set()
        return set()

    def _save_history(self, title: str):
        data = {"used_titles": list(self._history)[-200:] + [title]}
        self._history.add(title)
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"History save failed: {e}")

    def _is_used(self, title: str) -> bool:
        tl = title.lower()
        return any(tl[:40] in h.lower() or h.lower()[:40] in tl for h in self._history)

    def _is_blocked(self, text: str) -> bool:
        tl = text.lower()
        return any(b in tl for b in BLOCKED)

    def get_google_trends(self, region: str = "US", limit: int = 8) -> list:
        url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={region}"
        results = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if not title or self._is_used(title) or self._is_blocked(title):
                    continue
                results.append({
                    "title": title, "source": f"google_trends_{region}",
                    "hook_angle": f"This is trending RIGHT NOW: {title}"
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.error(f"Google Trends error ({region}): {e}")
        logger.info(f"[ContentDiscovery] Google Trends {region}: {len(results)}")
        return results

    def get_reddit_topics(self, subreddit: str = "todayilearned", limit: int = 6) -> list:
        url = f"https://www.reddit.com/r/{subreddit}/hot/.rss?limit={limit*3}"
        results = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = re.sub(r'^TIL[: ]+', '', entry.get("title",""), flags=re.IGNORECASE).strip()
                if not title or self._is_used(title) or self._is_blocked(title):
                    continue
                results.append({
                    "title": title[:150], "source": f"reddit_{subreddit}",
                    "url": entry.get("link", ""),
                    "hook_angle": f"Did you know? {title[:100]}"
                })
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.error(f"Reddit RSS error (r/{subreddit}): {e}")
        return results

    def get_all_reddit_topics(self, limit_per_sub: int = 4) -> list:
        all_topics = []
        for sub in REDDIT_SUBREDDITS:
            all_topics.extend(self.get_reddit_topics(sub, limit=limit_per_sub))
        return all_topics

    def get_wikipedia_facts(self, limit: int = 5) -> list:
        results = []
        try:
            url = "https://en.wikipedia.org/api/rest_v1/feed/featured/{}".format(
                datetime.now().strftime("%Y/%m/%d"))
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                for item in r.json().get("onthisday", [])[:limit*2]:
                    text = re.sub(r'<[^>]+>', '', item.get("text","")).strip()
                    if len(text) < 20 or self._is_blocked(text):
                        continue
                    results.append({
                        "title": text[:120], "source": "wikipedia",
                        "hook_angle": f"On this day in history: {text[:80]}"
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.error(f"Wikipedia error: {e}")
        # Fallback: random article
        if len(results) < 2:
            try:
                for _ in range(4):
                    r = requests.get(
                        "https://en.wikipedia.org/api/rest_v1/page/random/summary",
                        headers=HEADERS, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        extract = data.get("extract","").split(".")[0]
                        title = data.get("title","")
                        if extract and not self._is_blocked(extract):
                            results.append({
                                "title": title, "summary": extract[:200],
                                "source": "wikipedia_random",
                                "hook_angle": f"Fun fact: {extract[:100]}"
                            })
                            if len(results) >= limit:
                                break
            except Exception as e:
                logger.error(f"Wikipedia random error: {e}")
        logger.info(f"[ContentDiscovery] Wikipedia: {len(results)}")
        return results

    def get_arxiv_papers(self, limit: int = 5) -> list:
        results = []
        for feed_url in ARXIV_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:8]:
                    title = entry.get("title","").strip()
                    summary = entry.get("summary","").strip()[:250]
                    if not title or self._is_used(title):
                        continue
                    results.append({
                        "title": title, "summary": summary,
                        "source": "arxiv", "url": entry.get("link",""),
                        "hook_angle": f"Scientists just discovered: {title}"
                    })
                    if len(results) >= limit:
                        return results
            except Exception as e:
                logger.error(f"Arxiv error: {e}")
        logger.info(f"[ContentDiscovery] Arxiv: {len(results)}")
        return results

    def get_ev_news(self, limit: int = 8) -> list:
        results = []
        for url, source_name in EV_NEWS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    title = entry.get("title","").strip()
                    if not title or self._is_used(title):
                        continue
                    results.append({
                        "title": title, "source": source_name,
                        "url": entry.get("link",""),
                        "hook_angle": f"Breaking: {title}"
                    })
                    if len(results) >= limit:
                        return results
            except Exception as e:
                logger.error(f"EV RSS error ({source_name}): {e}")
        logger.info(f"[ContentDiscovery] EV News: {len(results)}")
        return results

    def discover(self, strategy: str = "auto", limit: int = 20) -> list:
        """
        Tüm kaynaklardan konu toplar. strategy: auto|trending|educational|scientific|ev_news
        """
        all_topics = []
        if strategy in ("auto", "trending"):
            all_topics.extend(self.get_google_trends("US", 5))
            all_topics.extend(self.get_google_trends("TR", 3))
            all_topics.extend(self.get_all_reddit_topics(limit_per_sub=3))
        if strategy in ("auto", "educational"):
            all_topics.extend(self.get_wikipedia_facts(5))
            all_topics.extend(self.get_arxiv_papers(5))
        if strategy in ("auto", "ev_news"):
            all_topics.extend(self.get_ev_news(8))
        if strategy == "scientific":
            all_topics.extend(self.get_arxiv_papers(10))
            all_topics.extend(self.get_wikipedia_facts(5))

        seen, filtered = set(), []
        for t in all_topics:
            key = t["title"][:50].lower()
            if key not in seen and not self._is_used(t["title"]):
                seen.add(key)
                filtered.append(t)

        random.shuffle(filtered)
        logger.info(f"[ContentDiscovery] Toplam benzersiz: {len(filtered)}")
        return filtered[:limit]

    def mark_used(self, title: str):
        self._save_history(title)
