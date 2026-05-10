import os
import json
import random
import datetime
import pandas as pd
from src.trend_engine import TrendEngine
from src.writer import CreativeWriter

HISTORY_FILE = "used_topics.json"
HISTORY_LIMIT = 100

class EvcarixBrain:
    def __init__(self):
        self.trend_engine = TrendEngine()
        self.writer = CreativeWriter()

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return []
        return []

    def _save_history(self, topic):
        history = self._load_history()
        history.append(topic)
        if len(history) > HISTORY_LIMIT:
            history = history[-HISTORY_LIMIT:]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def select_strategic_topic(self, video_type="short"):
        """v8.5: Strategic Topic Selector (Trends + 67 Topics)"""
        # 1. Trend Kontrolü (Son 12 saatteki en sıcak konular)
        try:
            # Shorts için YouTube trendlerinden ilham al
            if video_type == "short":
                trend_plan = self.trend_engine.trigger_from_youtube_trend(hours_back=12)
                if trend_plan:
                    print(f"[Brain] 🔥 Trend konu seçildi: {trend_plan['title']}")
                    return trend_plan['full_topic'], trend_plan
        except Exception as e:
            print(f"[Brain] Trend kontrol hatası: {e}")

        # 2. Havuz Kontrolü (data/topics.csv içindeki 67 stratejik konu)
        try:
            df = pd.read_csv("data/topics.csv")
            history = self._load_history()
            
            # Daha önce kullanılmamış olanları filtrele
            unused = df[~df['topic'].isin(history)]
            if unused.empty:
                print("[Brain] ⚠️ Tüm konular bitti, havuz sıfırlanıyor.")
                unused = df
                history = []
            
            # Önceliğe (priority) göre ağırlıklı seçim yap
            high_p = unused[unused['priority'] == 'high']
            if not high_p.empty and random.random() < 0.7:
                selected = high_p.sample(n=1).iloc[0]
            else:
                selected = unused.sample(n=1).iloc[0]
            
            topic = selected['topic']
            category = selected.get('category_id', 'general')
            print(f"[Brain] 🎯 Havuzdan konu seçildi ({category}): {topic}")
            return topic, None
        except Exception as e:
            print(f"[Brain] Havuz seçim hatası: {e}")
            return "Future of Electric Vehicles", None

    def create_daily_plan(self, slot="evening", video_type="short"):
        """v8.5 Enhanced Plan Creation with SEO & Trend Awareness"""
        topic, trend_plan = self.select_strategic_topic(video_type)
        
        # Eğer TrendEngine zaten bir plan (script dahil) ürettiyse onu kullan
        if trend_plan:
            self._save_history(topic)
            trend_plan['video_type'] = video_type
            return trend_plan

        # Yoksa CreativeWriter ile derinlemesine içerik üret
        if video_type == "long":
            print(f"[Brain] Haftalık Uzun Video üretiliyor: {topic}")
            content = self.writer.generate_long_content(topic)
        else:
            print(f"[Brain] Günlük Shorts üretiliyor: {topic}")
            content = self.writer.generate_short_content(topic)
        
        self._save_history(topic)
        
        # SEO & Tag Kontrolü (500 karakter sınırı uploader'da ama burada da ön-temizlik yapalım)
        tags = content.get('tags', [])
        if len(tags) > 30: tags = tags[:30] # Limit tags count

        return {
            "topic": topic,
            "full_topic": topic,
            "script": content['script'],
            "title": content['title'],
            "description": content['description'],
            "tags": tags,
            "voice": content.get('voice', "female"),
            "category": content.get('category', 'general'),
            "video_type": video_type
        }
