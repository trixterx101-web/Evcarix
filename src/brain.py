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
        """v9.1: Robust Hybrid Topic Selector (Sequential for Auto/Long, Trends for Trend Mode)"""
        content_mode = os.getenv("CONTENT_MODE", "auto").lower()
        
        # 1. Trend Modu (Sabah slotu veya manuel trend seçimi)
        if content_mode == "trend" and video_type == "short":
            try:
                trend_plan = self.trend_engine.trigger_from_youtube_trend(hours_back=48)
                if trend_plan:
                    print(f"[Brain] 🔥 Trend modu aktif: {trend_plan['title']}")
                    return trend_plan['full_topic'], trend_plan
                else:
                    print("[Brain] ⚠️ Trend bulunamadı, auto/sıralı moda geçiliyor.")
            except Exception as e:
                print(f"[Brain] Trend hatası: {e}")

        # 2. Sıralı Havuz Kontrolü (Sequential Selection)
        try:
            csv_path = os.path.join("data", "topics.csv")
            if not os.path.exists(csv_path):
                print(f"[Brain] ❌ Hata: {csv_path} bulunamadı!")
                return "Future of Electric Vehicles", None

            df = pd.read_csv(csv_path, on_bad_lines='skip')
            if df.empty:
                print("[Brain] ❌ Hata: topics.csv boş veya tüm satırlar hatalı!")
                return "Future of Electric Vehicles", None

            state_file = "sequential_state.json"
            state = {"next_index": 0}
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r") as f:
                        state = json.load(f)
                except Exception as e:
                    print(f"[Brain] State okuma hatası: {e}")
            
            idx = state.get("next_index", 0)
            if idx >= len(df):
                print(f"[Brain] 🔄 Liste sonuna gelindi ({len(df)}), başa dönülüyor.")
                idx = 0
            
            selected = df.iloc[idx]
            topic = selected['topic']
            category = selected.get('category_id', 'general')
            
            # Update state for next run
            state["next_index"] = idx + 1
            with open(state_file, "w") as f:
                json.dump(state, f)
            
            print(f"[Brain] 🔄 Sıralı seçim: [{idx+1}/{len(df)}] ({category}) -> {topic}")
            return topic, None

        except Exception as e:
            import traceback
            print(f"[Brain] ❌ Sıralı seçim hatası: {e}")
            traceback.print_exc()
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
