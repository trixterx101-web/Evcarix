import feedparser
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

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
                for entry in feed.entries[:5]:
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
        """Haberler arasından Gemini ile en trendy olanı seçer."""
        if news_df.empty:
            return "General EV Trends and Innovation"
        
        try:
            # En son 10 haberi al
            top_news = news_df.head(10)['title'].tolist()
            
            # Gemini API'yi configure et
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                print("GEMINI_API_KEY bulunamadı, ilk haber seçiliyor...")
                return news_df.iloc[0]['title']
            
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Prompt oluştur
            prompt = f"""Aşa��ıdaki elektrikli araç haberleri arasından BUGÜN YouTube'da en çok trend olacak olanı seç ve bunu video konusu olarak öner:

{chr(10).join(f'{i+1}. {title}' for i, title in enumerate(top_news))}

Sadece seçtiğin başlığı döndür, başka hiçbir şey ekleme. Cevap tek bir satırda olmalıdır."""
            
            # Gemini'den cevap al
            response = model.generate_content(prompt)
            selected = response.text.strip()
            
            print(f"[Gemini Trend Seçimi] {selected}")
            
            # Seçilen haberi bul
            for title in top_news:
                if title.lower() in selected.lower() or selected.lower() in title.lower():
                    return title
            
            # Eğer eşleşme bulunamazsa seçilen metni döndür
            return selected if selected else news_df.iloc[0]['title']
            
        except Exception as e:
            print(f"Gemini hatası: {e}, ilk haber seçiliyor...")
            return news_df.iloc[0]['title']

if __name__ == "__main__":
    engine = TrendEngine()
    news = engine.get_latest_news()
    print("Son Haberler:")
    print(news[['title', 'source']].head())
    trend = engine.select_trending_topic(news)
    print(f"\nSeçilen Trend: {trend}")