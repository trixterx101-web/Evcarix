import os
import json
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
            "Monday":    {"type": "short", "topic": "Next-Gen Battery Tech (Solid State, Sodium-ion)", "duration": 60},
            "Tuesday":   {"type": "short", "topic": "Global EV Comparison: BYD vs Tesla vs Hyundai", "duration": 45},
            "Wednesday": {"type": "short", "topic": "LFP vs NMC: Which battery wins for longevity?",   "duration": 50},
            "Thursday":  {"type": "short", "topic": "Winter Range King: Global 0°C Efficiency Test",  "duration": 55},
            "Friday":    {"type": "short", "topic": "Battery Degradation Data: 200,000 Mile Analysis", "duration": 45},
            "Saturday":  {"type": "short", "topic": "Fastest Charging EVs in 2024 (10-80% Comparison)", "duration": 60},
            "Sunday":    {"type": "long",  "topic": "The Future of Global Battery Supply Chains",      "duration": 480},
        }
        return schedule.get(weekday, schedule["Monday"])

    def create_daily_plan(self):
        print("Evcarix Brain: Plan oluşturuluyor...")
        config = self.get_daily_config()

        news_df = self.trend_engine.get_latest_news()
        specific_topic = self.trend_engine.select_trending_topic(news_df)
        full_topic = f"{config['topic']}: {specific_topic}"
        print(f"Konu seçildi: {full_topic}")

        # Başlık üret
        titles = self.writer.generate_title(specific_topic)
        best_title = titles[0] if titles else specific_topic
        print(f"Başlık: {best_title}")

        # Script üret
        writer_output = self.writer.generate_script(full_topic, format_type=config['type'])

        # Tags üret
        tags_list = self.writer.generate_tags(specific_topic, best_title)
        print(f"Etiketler üretildi: {len(tags_list)} adet.")

        # Açıklama üret
        description = self.writer.generate_description(specific_topic, best_title, tags_list)

        plan = {
            "timestamp": datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
            "config": config,
            "topic": specific_topic,
            "full_topic": full_topic,
            "title": best_title,
            "all_titles": titles,
            "script": writer_output['script'],
            "voice": writer_output['voice'],
            "description": description,
            "tags": tags_list
        }

        with open("daily_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)

        print("Plan oluşturuldu: daily_plan.json")
        return plan


if __name__ == "__main__":
    brain = EvcarixBrain()
    brain.create_daily_plan()
