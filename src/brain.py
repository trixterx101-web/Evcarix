import os
import json
import random
import datetime
from src.trend_engine import TrendEngine
from src.writer import CreativeWriter

CONTENT_HISTORY_FILE = "content_history.json"
HISTORY_LIMIT = 60  # Son 60 konu/başlık tekrar edilmez


class EvcarixBrain:
    def __init__(self):
        self.trend_engine = TrendEngine()
        self.writer = CreativeWriter()

    # ───────────────────────────────────────────────────────────────
    # İÇERİK GEÇMİŞİ — Başlık & Konu tekrarını önlemek için
    # ───────────────────────────────────────────────────────────────
    def _load_history(self):
        if os.path.exists(CONTENT_HISTORY_FILE):
            try:
                with open(CONTENT_HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_history(self, plan):
        history = self._load_history()
        entry = {
            "timestamp": plan["timestamp"],
            "slot": plan["slot"],
            "topic": plan["topic"],
            "title": plan["title"],
            "script_preview": plan["script"][:200] if plan.get("script") else ""
        }
        history.append(entry)
        history = history[-HISTORY_LIMIT:]
        with open(CONTENT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def _get_used_titles(self):
        return [h["title"] for h in self._load_history()]

    def _get_used_topics(self):
        return [h["topic"] for h in self._load_history()]

    # ───────────────────────────────────────────────────────────────
    # KONU HAVUZU — 67 veri-odaklı EV konusu, 9 kategorilere ayrılmış
    # ───────────────────────────────────────────────────────────────
    _TOPIC_POOL = {
        # ── 1. Pil Bilimi & Teknoloji (8 konu) ──────────────────────────
        "battery_science": [
            "LFP vs NMC vs NCA real-world degradation after 100000 miles data",
            "Solid-state battery realistic timeline and energy density roadmap",
            "How battery degradation science actually works SOC cycles",
            "BMS battery management system deep dive explained",
            "Battery heating systems comparison active vs passive thermal",
            "What is a charge cycle really counting partial charges",
            "Hot weather battery lifespan impact data Celsius analysis",
            "LFP battery after 100000 miles real data analysis",
        ],
        # ── 2. Menzil & Verimlilik Testleri (8 konu) ─────────────────────
        "range_tests": [
            "Tesla Model Y vs Hyundai IONIQ 5 winter range loss data Norway",
            "BMW iX vs Mercedes EQS highway efficiency test 70mph",
            "BYD Seal vs Tesla Model 3 real world range comparison China",
            "Lucid Air vs Tesla Model S Plaid efficiency kWh per 100km",
            "Rivian R1T vs Ford F-150 Lightning towing range impact data",
            "Winter range loss complete data set Norway vs Canada vs US",
            "Summer vs winter range comparison same car same route test",
            "Highway vs city range difference 70mph vs 25mph real data",
            "Speed and range relationship curve analysis 30 to 80mph",
            "EV consumption breakdown kWh per 100km real driving data",
        ],
        # ── 3. Şarj Teknolojisi (8 konu) ────────────────────────────────
        "charging": [
            "800V vs 400V real charging speed difference minutes saved data",
            "Does fast charging actually kill your battery 5 year study",
            "CCS vs CHAdeMO vs Tesla connector situation 2026 market share",
            "Charging power loss cable length effect volts drop data",
            "Bi-directional charging V2G V2H realistic grid backup analysis",
            "Home charging vs DC fast charging cost per mile comparison",
            "Charging network reliability test Europe Electrify America data",
            "Solar energy plus EV combination payback period calculation",
        ],
        # ── 4. Sahiplik Maliyeti (8 konu) ───────────────────────────────
        "cost_ownership": [
            "5 year total cost EV vs diesel compact sedan real numbers USA",
            "Used EV depreciation value loss data by brand and model",
            "Insurance cost comparison EV vs gas car is it really higher",
            "EV maintenance cost brakes tires service real 100000 mile data",
            "Battery replacement cost 2026 actual price out of warranty",
            "Home solar plus EV charging payback period calculation USA Europe",
            "Public charging subscription plans worth it or cost per kWh analysis",
            "EV tax incentives 2026 USA Europe China comparison amounts",
        ],
        # ── 5. Araç Karşılaştırmaları (7 konu) ──────────────────────────
        "comparisons": [
            "Tesla Model 3 Highland vs Xiaomi SU7 specs and tech data",
            "Porsche Taycan vs Audi e-tron GT platform sharing analysis",
            "Volkswagen ID.4 vs Kia EV6 family SUV comparison data",
            "NIO ET7 vs BMW i7 luxury electric sedan tech comparison",
            "Volvo EX30 vs Smart #1 platform and efficiency comparison",
            "Same segment EV comparison data only specs vs real world",
            "Platform architecture differences what actually changes EV",
        ],
        # ── 6. Pazar & Sektör Verileri (7 konu) ─────────────────────────
        "market_data": [
            "BYD vs Tesla global sales data 2026 Q1 market share analysis",
            "European EV market trends VW Group vs Stellantis market share",
            "Chinese EV brand expansion in Europe NIO Xpeng MG data",
            "US EV adoption rates by state California vs Texas numbers",
            "Global battery production capacity CATL vs BYD vs LG Energy",
            "Global EV market trends year over year percentage growth",
            "Top 10 selling electric vehicles global sales data set",
        ],
        # ── 7. Marka İncelemeleri & Teknoloji (8 konu) ──────────────────
        "trend": [
            "Tesla Cybertruck production ramp up and delivery data",
            "Xiaomi SU7 ultra performance specs and battery tech",
            "Rivian R2 platform cost reduction strategy analysis",
            "Toyota Solid State battery breakthrough 2027 roadmap",
            "BMW Neue Klasse platform architecture and efficiency",
            "BYD Blade Battery safety vs NMC technology deep dive",
            "Mercedes EQG electric G-Wagon quad motor tech data",
            "Porsche Macan Electric vs Tesla Model Y Performance specs",
        ],
        # ── 8. Altyapı & Şebeke (7 konu) ────────────────────────────────
        "infrastructure": [
            "Charging station reliability test results uptime data",
            "Europe charging infrastructure map gaps and coverage data",
            "Apartment building EV charging solutions and cost analysis",
            "EV charging time calculator real vs advertised minutes",
            "Does EV charging crash the grid real math demand data",
            "Renewable energy plus EV combination analysis carbon data",
            "Smart charging V1G V2G does it really matter cost data",
        ],
        # ── 9. Eğitim & Teknik Açıklamalar (7 konu) ────────────────────────
        "education": [
            "Heat pump how does it work visual explanation efficiency data",
            "PTC heater vs heat pump full comparison range impact data",
            "One-pedal driving how does it work efficiency gain data",
            "EV thermal management system explained coolant loop data",
            "Aerodynamic drag and range relationship Cd A coefficient data",
            "Why does charging curve drop battery chemistry explained",
            "SOH State of Health what is it how measured accuracy data",
        ],
        # ── 10. İnteraktif Araçlar & Hesaplayıcılar (7 konu) ────────────────
        "interactive_tools": [
            "Range calculator by temperature interactive data visualization",
            "EV vs diesel cost comparator total 5 year calculation tool",
            "EV charging cost calculator home vs public vs solar data",
            "Battery degradation predictor based on usage pattern data",
            "Charging speed comparison graph 10 to 80 percent data",
            "Range loss animated explanation temperature speed data",
            "Market share interactive visualization global regions data",
        ],
    }

    def _pick_topic(self, slot="evening"):
        """Havuzdan rastgele, tekrar etmeyen, çeşitli kategoriden konu seçer.
        Returns: (topic, category) tuple."""
        used_topics = self._get_used_topics()
        used_lower = [t.lower() for t in used_topics]

        # Her kategoriden birer aday seç, tekrar olmayanları filtrele
        candidates = []
        for cat, topics in self._TOPIC_POOL.items():
            fresh = [t for t in topics if t.lower() not in used_lower]
            if fresh:
                candidates.append((random.choice(fresh), cat))

        if candidates:
            return random.choice(candidates)

        # Hepsi kullanılmışsa — en eski konulardan başlayarak tekrar izin ver
        all_pairs = [(t, c) for c, topics in self._TOPIC_POOL.items() for t in topics]
        random.shuffle(all_pairs)
        return all_pairs[0]

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
                "myth-busting",  # Common misconception
                "comparison",    # Side by side
            ]),
            "emoji_set": random.choice([
                ["⚡", "🔋", "📊"],
                ["🚗", "⚡", "🔌"],
                ["📈", "🔋", "🏎️"],
                ["❄️", "🔥", "📉"],
            ])
        }

    def _clean_topic(self, text):
        """Hashtag, URL ve gereksiz karakterleri temizler."""
        import re
        text = re.sub(r'#\w+', '', text)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip(' :;|')
        return text

    def create_daily_plan(self, slot="evening", video_type="short"):
        mode = os.environ.get("CONTENT_MODE", "auto").lower()
        print(f"Evcarix Brain: Plan oluşturuluyor ({video_type}, mode={mode})...")

        # ── YouTube Trend Tetikleyici (Sadece trend modunda aktif) ──────────
        if mode == "trend":
            try:
                triggered_plan = self.trend_engine.trigger_from_youtube_trend(hours_back=48)
                if triggered_plan:
                    print(f"\n🚀 TREND MOD AKTİF!")
                    triggered_plan["config"]["type"] = video_type
                    
                    # EĞER UZUN VİDEO İSE: Trend konusunu alıp CreativeWriter ile UZUN script üret
                    if video_type == "long":
                        print(f"[Brain] Trend konusu için UZUN script üretiliyor: {triggered_plan['topic']}")
                        long_script_data = self.writer.generate_script(
                            triggered_plan['topic'], format_type="long", category=triggered_plan.get("category", "trend")
                        )
                        triggered_plan["script"] = long_script_data["script"]
                        triggered_plan["voice"]  = long_script_data["voice"]
                        # SEO meta verilerini de uzun formata göre güncelle
                        triggered_plan["description"] = self.writer.generate_description(
                            topic=triggered_plan['topic'],
                            title=triggered_plan['title'],
                            tags_list=triggered_plan['tags'],
                            format_type="long"
                        )

                    self._save_history(triggered_plan)

                # SEO metadata ekle
                import datetime as _dt
                best_hours = [6, 7, 8, 14, 15, 16, 19, 20]
                now_h = _dt.datetime.utcnow().hour
                next_best = min(best_hours, key=lambda h: (h - now_h) % 24)
                triggered_plan["seo_metadata"] = {
                    "suggested_upload_time_utc": f"{next_best:02d}:00",
                    "first_24h_actions": [
                        "Pin a question comment immediately after upload",
                        "Reply to ALL comments within first 2 hours",
                        "Share to r/electricvehicles and r/teslamotors",
                        "Post on Twitter/X with top 3 hashtags",
                        "Add to EV Data playlist within 10 min of upload",
                    ],
                    "a_b_test_titles": triggered_plan.get("all_titles", []),
                    "target_ctr": "12-18%",
                    "target_retention": "70%+",
                    "shorts_optimization": {
                        "hook_in_first_3s": True,
                        "loop_friendly_ending": True,
                        "vertical_9_16": True,
                        "recommended_length_sec": 38,
                    }
                }
                print(f"[Brain] 📊 Upload önerisi: {next_best:02d}:00 UTC | Hedef CTR: %12-18")
                return triggered_plan
            except Exception as e:
                print(f"[Brain] Trend tetikleyici hatası (normal moda geçiliyor): {e}")
        # ── Trend bulunamazsa normal pipeline devam eder ─────────────

        duration = 210 if video_type == "long" else 37  # long: 3-4 min (180-240s), short: 25-50s
        config = {"type": video_type, "duration": duration}

        # Trend haberleri çek (LLM için context)
        news_df = self.trend_engine.get_latest_news()
        trending_topic = self.trend_engine.select_trending_topic(news_df)
        if trending_topic:
            trending_topic = self._clean_topic(trending_topic)

        # Ana konu seçimi — Havuz (67 konu) veya Trend haber karışımı
        pool_topic, pool_category = self._pick_topic(slot)
        
        # 'auto' modunda sadece havuzdan seçer. 'trend' modunda haberlere de bakar.
        if mode == "trend" and trending_topic and random.random() < 0.4:
            specific_topic = trending_topic
            topic_category = "trend"
        else:
            specific_topic = pool_topic
            topic_category = pool_category
        
        full_topic = specific_topic

        used_titles = self._get_used_titles()
        print(f"Konu seçildi: {full_topic.encode('ascii', 'ignore').decode('ascii')}")
        print(f"Geçmiş başlık sayısı: {len(used_titles)}")

        # Başlık üret — geçmiş başlıkları vererek tekrarı önle
        titles = self.writer.generate_title(specific_topic, history_titles=used_titles, category=topic_category, format_type=video_type)
        best_title = titles[0] if titles else specific_topic
        print(f"Başlık: {best_title.encode('ascii', 'ignore').decode('ascii')}")

        # Senaryo üret — kategoriye göre özel prompt
        writer_output = self.writer.generate_script(
            full_topic, format_type=video_type, category=topic_category
        )

        # Etiket üret — kategoriye göre SEO etiketleri
        tags_list = self.writer.generate_tags(specific_topic, best_title, category=topic_category, format_type=video_type)
        print(f"Etiketler: {len(tags_list)} adet")

        # Açıklama üret — kategoriye göre SEO açıklaması
        variation = self._get_metadata_variation()
        description = self.writer.generate_description(
            topic=specific_topic,
            title=best_title,
            tags_list=tags_list,
            cta_override=variation["cta_style"],
            category=topic_category,
            format_type=video_type
        )
        
        # Add editorial disclaimer to description
        disclaimer = (
            "\n\nStock footage courtesy of Pexels, Pixabay (CC0). "
            "Manufacturer press imagery used for editorial/informational purposes only. "
            "No affiliation with any manufacturer shown."
        )
        description += disclaimer

        plan = {
            "timestamp":  datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
            "slot":       slot,
            "config":     config,
            "topic":      specific_topic,
            "full_topic": full_topic,
            "category":   topic_category,
            "title":      best_title,
            "all_titles": titles,
            "script":     writer_output['script'],
            "voice":      writer_output['voice'],
            "description": description,
            "tags":       tags_list,
            "variation":  variation,
        }

        # ── SEO Metadata (normal mod) ─────────────────────────────────
        import datetime as _dt
        best_hours = [6, 7, 8, 14, 15, 16, 19, 20]
        now_h = _dt.datetime.utcnow().hour
        next_best = min(best_hours, key=lambda h: (h - now_h) % 24)
        plan["seo_metadata"] = {
            "suggested_upload_time_utc": f"{next_best:02d}:00",
            "first_24h_actions": [
                "Pin a question comment immediately after upload",
                "Reply to ALL comments within first 2 hours",
                "Share to r/electricvehicles and r/teslamotors",
                "Post on Twitter/X with top 3 hashtags",
                "Add to EV Data playlist within 10 min of upload",
            ],
            "a_b_test_titles": titles,
            "target_ctr": "12-18%",
            "target_retention": "70%+",
        }
        print(f"[Brain] 📊 Upload önerisi: {next_best:02d}:00 UTC | Hedef CTR: %12-18")

        # Geçmişe kaydet
        self._save_history(plan)

        with open("daily_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=4)

        print("Plan hazır: daily_plan.json")
        return plan


if __name__ == "__main__":
    brain = EvcarixBrain()
    brain.create_daily_plan(slot="evening")
