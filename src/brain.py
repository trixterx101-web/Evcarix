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
