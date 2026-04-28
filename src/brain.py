import os
import json
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
