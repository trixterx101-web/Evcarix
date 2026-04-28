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
            "Monday":    {"type": "short", "topic": "EV News Summary",       "duration": 60},
            "Tuesday":   {"type": "short", "topic": "Charging Tips",          "duration": 45},
            "Wednesday": {"type": "short", "topic": "Tesla/BMW/Rivian",       "duration": 50},
            "Thursday":  {"type": "short", "topic": "Market Comparison",      "duration": 55},
            "Friday":    {"type": "short", "topic": "World EV Trend",         "duration": 45},
            "Saturday":  {"type": "short", "topic": "Weekend EV Tips",        "duration": 60},
            "Sunday":    {"type": "long",  "topic": "Deep EV Review",         "duration": 480},
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

        # Açıklama üret
        description = self.writer.generate_description(specific_topic, best_title)

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
            "tags": ["ev", "electriccar", "electricvehicle", "battery",
                     "tesla", "evrange", "Evcarix", "shorts"]
        }

        with open("daily_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)

        print("Plan oluşturuldu: daily_plan.json")
        return plan


if __name__ == "__main__":
    brain = EvcarixBrain()
    brain.create_daily_plan()
