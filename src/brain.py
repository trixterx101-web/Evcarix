import os
import json
import random
import datetime
import pandas as pd
from src.trend_engine import TrendEngine
from src.writer import CreativeWriter

try:
    from src.content_discovery import ContentDiscovery
    _discovery = ContentDiscovery()
except Exception as e:
    print(f"[Brain] ContentDiscovery yüklenemedi: {e}")
    _discovery = None

HISTORY_FILE = "used_topics.json"
HISTORY_LIMIT = 100

# Manuel konu modları → arama sorgusu eşleştirmesi
MANUAL_MODE_TOPICS = {
    "electric vehicles":      ["Future of electric vehicles", "EV adoption trends", "Electric car technology 2026", "Best electric vehicles 2026"],
    "artificial intelligence":["AI in electric vehicles", "Machine learning for EVs", "AI autonomous driving", "Neural networks in cars"],
    "robotics":               ["Robot electric vehicles", "Autonomous EV robots", "Future robotics transport", "Self-driving robot cars"],
    "new technologies":       ["New EV technology 2026", "Future car innovations", "Next gen electric vehicles", "EV tech breakthroughs"],
    "battery systems":        ["EV battery technology", "Solid state battery EVs", "Battery range improvement", "Lithium battery future"],
    "smart cities":           ["Smart city EV charging", "Urban electric transport", "City EV infrastructure", "Smart grid electric cars"],
    "devices of the future":  ["Future EV devices", "Next gen car technology", "Smart EV gadgets 2026", "Electric vehicle innovation"],
}


class EvcarixBrain:
    def __init__(self):
        self.trend_engine = TrendEngine()
        self.writer = CreativeWriter()

    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_history(self, topic):
        history = self._load_history()
        history.append(topic)
        if len(history) > HISTORY_LIMIT:
            history = history[-HISTORY_LIMIT:]
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def select_strategic_topic(self, video_type="short"):
        content_mode = os.getenv("CONTENT_MODE", "auto").strip().lower()
        print(f"[Brain] 📌 Content Mode: {content_mode}")

        # ── 1. Trend Modu ─────────────────────────────────────────
        if content_mode == "trend" and video_type == "short":
            try:
                trend_plan = self.trend_engine.trigger_from_youtube_trend(hours_back=48)
                if trend_plan:
                    print(f"[Brain] 🔥 Trend modu aktif: {trend_plan['title']}")
                    return trend_plan['full_topic'], trend_plan
                else:
                    print("[Brain] ⚠️ Trend bulunamadı, auto moda geçiliyor.")
            except Exception as e:
                print(f"[Brain] Trend hatası: {e}")

        # ── 2. ContentDiscovery Modları ───────────────────────────
        discovery_modes = ["educational", "scientific", "ev_news"]
        if content_mode in discovery_modes and _discovery:
            try:
                topics = _discovery.discover(strategy=content_mode, limit=10)
                if topics:
                    chosen = random.choice(topics)
                    topic_title = chosen.get("title", "Future of Electric Vehicles")
                    print(f"[Brain] 🔍 ContentDiscovery ({content_mode}): {topic_title[:60]}")
                    print(f"        Kaynak: {chosen.get('source', '?')}")
                    _discovery.mark_used(topic_title)
                    return topic_title, None
                else:
                    print(f"[Brain] ⚠️ ContentDiscovery ({content_mode}) boş döndü, auto moda geçiliyor.")
            except Exception as e:
                print(f"[Brain] ContentDiscovery hatası: {e}")

        # ── 3. Manuel Konu Modları ────────────────────────────────
        if content_mode in MANUAL_MODE_TOPICS:
            topic_list = MANUAL_MODE_TOPICS[content_mode]
            # Daha önce kullanılmamış birini seç
            history = self._load_history()
            unused = [t for t in topic_list if t not in history]
            topic = random.choice(unused if unused else topic_list)
            print(f"[Brain] 🎯 Manuel mod ({content_mode}): {topic}")
            return topic, None

        # ── 4. Sıralı Havuz (Auto/Default) ───────────────────────
        try:
            csv_path = os.path.join("data", "topics.csv")
            if not os.path.exists(csv_path):
                print(f"[Brain] ❌ {csv_path} bulunamadı!")
                return "Future of Electric Vehicles", None

            df = pd.read_csv(csv_path, on_bad_lines='skip')
            if df.empty:
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
                print(f"[Brain] 🔄 Liste sonu ({len(df)}), başa dönülüyor.")
                idx = 0

            selected = df.iloc[idx]
            topic    = selected['topic']
            category = selected.get('category_id', 'general')

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
        topic, trend_plan = self.select_strategic_topic(video_type)

        if trend_plan:
            self._save_history(topic)
            trend_plan['video_type'] = video_type
            return trend_plan

        if video_type == "long":
            print(f"[Brain] Haftalık Uzun Video üretiliyor: {topic}")
            content = self.writer.generate_long_content(topic)
        else:
            print(f"[Brain] Günlük Shorts üretiliyor: {topic}")
            content = self.writer.generate_short_content(topic)

        self._save_history(topic)

        tags = content.get('tags', [])
        if len(tags) > 30:
            tags = tags[:30]

        return {
            "topic":       topic,
            "full_topic":  topic,
            "script":      content['script'],
            "title":       content['title'],
            "description": content['description'],
            "tags":        tags,
            "voice":       content.get('voice', "female"),
            "category":    content.get('category', 'general'),
            "video_type":  video_type
        }
