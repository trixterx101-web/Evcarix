import feedparser
import requests
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger("TrendScraper")

class TrendScraper:
    def get_google_trends(self):
        try:
            feed = feedparser.parse("https://trends.google.com/trends/trendingsearches/daily/rss?geo=TR")
            return [item.title for item in feed.entries]
        except: return []

    def get_reddit_facts(self, subreddit="todayilearned"):
        # Reddit RSS is a quick way to get trends without an API key for small tasks
        url = f"https://www.reddit.com/r/{subreddit}/hot.rss"
        try:
            feed = feedparser.parse(url)
            return [item.title for item in feed.entries if len(item.title) > 20]
        except: return []

    def get_wikipedia_dyk(self):
        url = "https://en.wikipedia.org/wiki/Main_Page"
        try:
            r = requests.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            dyk_div = soup.find(id="mp-dyk")
            facts = [li.text for li in dyk_div.find_all("li")]
            return facts
        except: return []

    def get_all_trends(self):
        trends = {
            "google": self.get_google_trends()[:5],
            "reddit": self.get_reddit_facts()[:5],
            "wikipedia": self.get_wikipedia_dyk()[:3]
        }
        return trends
