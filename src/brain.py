import os
import json
<<<<<<< HEAD
import datetime
from src.trend_engine import TrendEngine
from src.writer import CreativeWriter

class EvcarixBrain:
    def __init__(self):
        self.trend_engine = TrendEngine()
        self.writer = CreativeWriter()

    def get_daily_config(self):
        weekday = datetime.datetime.now().strftime("%A")
        schedule = {
            "Monday": {"type": "short", "topic": "EV Haber Özeti", "duration": 60},
            "Tuesday": {"type": "short", "topic": "Şarj İpuçları", "duration": 45},
            "Wednesday": {"type": "short", "topic": "Tesla/BMW/Rivian", "duration": 50},
            "Thursday": {"type": "short", "topic": "Piyasa Karşılaştırma", "duration": 55},
            "Friday": {"type": "short", "topic": "Dünya Trendi", "duration": 45},
            "Saturday": {"type": "short", "topic": "Hafta Sonu Tüyo", "duration": 60},
            "Sunday": {"type": "long", "topic": "Derin EV İnceleme", "duration": 480},
        }
        return schedule.get(weekday, schedule["Monday"])

    def create_daily_plan(self):
        print("Evcarix Brain: Plan oluşturuluyor...")
        config = self.get_daily_config()
        
        news_df = self.trend_engine.get_latest_news()
        specific_topic = self.trend_engine.select_trending_topic(news_df)
        full_topic = f"{config['topic']}: {specific_topic}"
        
        print(f"Konu seçildi: {full_topic}")
        writer_output = self.writer.generate_script(full_topic, format_type=config['type'])
        
        plan = {
            "timestamp": datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
            "config": config,
            "topic": specific_topic,
            "full_topic": full_topic,
            "script": writer_output['script'],
            "voice": writer_output['voice']
        }
        
        with open("daily_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)
        
        print("Plan başarıyla oluşturuldu: daily_plan.json")
        return plan

if __name__ == "__main__":
    brain = EvcarixBrain()
    brain.create_daily_plan()
=======
from src.trend_engine import TrendEngine
from src.writer import CreativeWriter


class Brain:
    def __init__(self):
        self.trend_engine = TrendEngine()
        self.writer = CreativeWriter()
        self.plan_file = "daily_plan.json"

    def create_daily_plan(self, num_videos=1):
        """Create a daily content plan with topics, titles, and scripts."""
        print("[Brain] Fetching latest news...")
        news_df = self.trend_engine.get_latest_news()

        plans = []
        used_topics = set()

        for i in range(num_videos):
            print(f"\n[Brain] Planning video {i + 1}/{num_videos}...")

            # Select topic
            topic = self.trend_engine.select_trending_topic(news_df)

            # Avoid duplicates
            attempts = 0
            while topic in used_topics and attempts < 5:
                if not news_df.empty and len(news_df) > attempts + 1:
                    topic = news_df.iloc[attempts + 1]['title']
                attempts += 1
            used_topics.add(topic)

            print(f"[Brain] Topic: {topic}")

            # Generate titles
            titles = self.writer.generate_title(topic)
            best_title = titles[0] if titles else topic
            print(f"[Brain] Title: {best_title}")

            # Generate script
            script = self.writer.generate_script(topic)
            print(f"[Brain] Script length: {len(script.split())} words")

            # Generate description
            description = self.writer.generate_description(topic, best_title)

            plans.append({
                "video_index": i + 1,
                "topic": topic,
                "title": best_title,
                "all_titles": titles,
                "script": script,
                "description": description,
                "tags": ["ev", "electriccar", "electricvehicle", "battery",
                         "tesla", "evrange", "Evcarix", "shorts"]
            })

        # Save plan
        with open(self.plan_file, "w", encoding="utf-8") as f:
            json.dump(plans, f, indent=2, ensure_ascii=False)

        print(f"\n[Brain] Daily plan saved to {self.plan_file}")
        return plans
>>>>>>> d0b04483447cc004bbce9fb8f096e62cafafcaca
