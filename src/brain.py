import os
import json
import random
import datetime
from src.trend_engine import TrendEngine
from src.writer import CreativeWriter


class EvcarixBrain:
    def __init__(self):
        self.trend_engine = TrendEngine()
        self.writer = CreativeWriter()

    def get_daily_config(self, slot="evening"):
        """
        Her gün 2 farklı video için farklı konular seçer.
        slot: 'evening' (18:00 TR) | 'night' (21:00 TR)
        """
        weekday = datetime.datetime.now().strftime("%A")

        # Her gün için 2 konu: [sabah/akşam, gece]
        schedule = {
            "Monday": [
                {"type": "short", "topic": "Solid-State Battery: Real Data vs Promises",        "duration": 55},
                {"type": "short", "topic": "Next-Gen EV Range: 600+ Mile Cars Are Coming",       "duration": 50},
            ],
            "Tuesday": [
                {"type": "short", "topic": "BYD vs Tesla: Real-World Range Comparison",          "duration": 55},
                {"type": "short", "topic": "Hyundai IONIQ 6 vs Tesla Model 3: True Efficiency",  "duration": 50},
            ],
            "Wednesday": [
                {"type": "short", "topic": "LFP vs NMC Battery: Which Lasts Longer?",           "duration": 55},
                {"type": "short", "topic": "EV Battery Degradation: 200,000 Mile Real Data",    "duration": 50},
            ],
            "Thursday": [
                {"type": "short", "topic": "Winter EV Range: 0°C Real-World Test Results",      "duration": 55},
                {"type": "short", "topic": "Heat Pump vs Resistance Heater: EV Range Impact",   "duration": 50},
            ],
            "Friday": [
                {"type": "short", "topic": "True Cost of EV Ownership: 100k Mile Analysis",     "duration": 55},
                {"type": "short", "topic": "EV Charging Cost vs Gasoline: Real Numbers 2024",   "duration": 50},
            ],
            "Saturday": [
                {"type": "short", "topic": "Fastest Charging EVs: 10-80% Speed Comparison",    "duration": 55},
                {"type": "short", "topic": "800V vs 400V Charging: Does It Matter?",            "duration": 50},
            ],
            "Sunday": [
                {"type": "short", "topic": "Best Range EVs Under $40k: Real-World Test",        "duration": 55},
                {"type": "short", "topic": "Global EV Battery Supply Chain: What's Changing",   "duration": 50},
            ],
        }

        day_slots = schedule.get(weekday, schedule["Monday"])
        # slot'a göre doğru konu
        if slot == "night":
            return day_slots[1] if len(day_slots) > 1 else day_slots[0]
        return day_slots[0]

    def _get_metadata_variation(self):
        """Her çalışmada biraz farklı metadata yapısı üretmek için varyasyon seçer."""
        return {
            "cta_style": random.choice([
                "Subscribe to Evcarix for real EV data every day.",
                "Follow Evcarix — no hype, just numbers. ⚡",
                "Join Evcarix for honest electric vehicle data.",
                "Like & subscribe for daily real-world EV tests.",
            ]),
            "hook_style": random.choice([
                "data-driven",   # Numbers first
                "question",      # Curiosity gap
                "shocking",      # Surprising fact
            ]),
            "emoji_set": random.choice([
                ["⚡", "🔋", "📊"],
                ["🚗", "⚡", "🔌"],
                ["📈", "🔋", "🏎️"],
            ])
        }

    def create_daily_plan(self, slot="evening"):
        print("Evcarix Brain: Plan oluşturuluyor...")
        config = self.get_daily_config(slot=slot)
        variation = self._get_metadata_variation()

        # Trend seç
        news_df = self.trend_engine.get_latest_news()
        specific_topic = self.trend_engine.select_trending_topic(news_df)
        full_topic = f"{config['topic']}: {specific_topic}"
        print(f"Konu seçildi: {full_topic.encode('ascii', 'ignore').decode('ascii')}")

        # Başlık üret
        titles = self.writer.generate_title(specific_topic)
        best_title = titles[0] if titles else specific_topic
        print(f"Başlık: {best_title.encode('ascii', 'ignore').decode('ascii')}")

        # Senaryo üret
        writer_output = self.writer.generate_script(full_topic, format_type=config['type'])

        # Etiket üret
        tags_list = self.writer.generate_tags(specific_topic, best_title)
        print(f"Etiketler: {len(tags_list)} adet")

        # Açıklama üret — CTA varyasyonunu geç
        description = self.writer.generate_description(
            topic=specific_topic,
            title=best_title,
            tags_list=tags_list,
            cta_override=variation["cta_style"]
        )

        plan = {
            "timestamp":  datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
            "slot":       slot,
            "config":     config,
            "topic":      specific_topic,
            "full_topic": full_topic,
            "title":      best_title,
            "all_titles": titles,
            "script":     writer_output['script'],
            "voice":      writer_output['voice'],
            "description": description,
            "tags":       tags_list,
            "variation":  variation,
        }

        with open("daily_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)

        print("Plan hazır: daily_plan.json")
        return plan


if __name__ == "__main__":
    brain = EvcarixBrain()
    brain.create_daily_plan(slot="evening")
