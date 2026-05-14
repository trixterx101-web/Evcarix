"""
Evcarix Query Builder
Maps video topic/category to specific, relevant stock video search queries.
Used by MediaEngine for both Pexels and Pixabay searches.
"""

import re

# ── Topic keyword → ranked search queries ─────────────────────────────────────
TOPIC_QUERY_MAP = [
    # Battery & charging science
    (["lfp", "lithium", "battery", "pil", "degradasyon", "degradation",
      "bms", "solid state", "cycle", "döngü", "kalibrasyon"],
     ["electric car battery pack closeup",
      "lithium battery cells technology",
      "battery charging indicator display",
      "electric vehicle battery module"]),

    # Range & efficiency
    (["menzil", "range", "verimlilik", "efficiency", "tüketim",
      "consumption", "kwh", "wltp", "epa"],
     ["electric car highway driving",
      "car dashboard digital display range",
      "electric vehicle speedometer screen",
      "modern car driving road"]),

    # Winter & temperature
    (["kış", "winter", "soğuk", "cold", "sıcaklık", "temperature",
      "ısı pompası", "heat pump", "ptc"],
     ["car driving snow winter road",
      "electric vehicle cold weather charging",
      "snowy road automobile driving",
      "car heater dashboard winter"]),

    # Charging speed & infrastructure
    (["şarj", "charging", "800v", "400v", "ccs", "dc fast",
      "hızlı şarj", "fast charge", "v2g", "v2h", "şarj ağı"],
     ["electric car charging station",
      "EV charger plug connector",
      "fast charging electric vehicle",
      "charging point parking lot"]),

    # Cost & ownership
    (["maliyet", "cost", "fiyat", "price", "sigorta", "insurance",
      "bakım", "maintenance", "değer", "depreciation", "garanti"],
     ["car cost comparison chart",
      "money savings piggy bank finance",
      "automobile service maintenance",
      "financial graph economy"]),

    # Market & sales data
    (["pazar", "market", "satış", "sales", "adaptasyon", "adoption",
      "çin", "china", "byd", "pazar payı", "share"],
     ["electric vehicle sales growth chart",
      "automotive market data screen",
      "car showroom modern electric",
      "global map data visualization"]),

    # Comparison & ranking
    (["karşılaştırma", "comparison", "vs", "ranking", "sıralama",
      "segment", "suv", "sedan", "aile", "family"],
     ["electric cars lineup parking",
      "car comparison side by side",
      "automobile test track driving",
      "multiple electric vehicles display"]),

    # Infrastructure & grid
    (["altyapı", "infrastructure", "şebeke", "grid", "apartman",
      "apartment", "akıllı şarj", "smart charging", "solar"],
     ["solar panel energy electric",
      "power grid electricity infrastructure",
      "charging station parking lot",
      "renewable energy technology"]),

    # Education & technical
    (["açıklama", "explained", "nasıl", "how", "teknik", "technical",
      "inverter", "motor", "aerodinamik", "drag", "soh"],
     ["electric motor technology engineering",
      "car engine cutaway diagram display",
      "technology data screen dashboard",
      "engineering laboratory equipment"]),

    # Tools & data
    (["hesaplayıcı", "calculator", "tool", "araç", "grafik", "chart",
      "veri", "data", "analiz", "analysis"],
     ["data analytics screen technology",
      "digital dashboard information display",
      "chart graph business screen",
      "technology interface visualization"]),

    # Electric Vehicles & Future Tech (New)
    (["ev_tech", "motor type", "platform", "ota", "aerodynamics", "wireless", "900v"],
     ["electric car motor engineering",
      "modern vehicle platform chassis",
      "car software update screen",
      "wind tunnel car testing",
      "wireless EV charging pad"]),

    # Artificial Intelligence (New)
    (["ai", "artificial intelligence", "self-driving", "autonomous", "neural", "predictive"],
     ["self driving car interior POV",
      "artificial intelligence brain digital",
      "autonomous vehicle sensor radar",
      "robot car driving automation",
      "AI technology visualization"]),

    # Robotics (New)
    (["robotics", "robot", "humanoid", "factory", "automation", "robotic arm"],
     ["car factory robot arm production",
      "humanoid robot walking technology",
      "robotic assembly line automobile",
      "high tech industrial automation",
      "Tesla Optimus robot style"]),

    # New Technologies (New)
    (["new_tech", "sodium-ion", "silicon anode", "v2g", "perovskite", "breakthrough"],
     ["laboratory science battery research",
      "futuristic technology energy grid",
      "clean energy innovation lab",
      "new tech breakthrough visualization"]),

    # Smart Cities & Infrastructure (New)
    (["smart_city", "smart city", "grid", "infrastructure", "connected car"],
     ["smart city traffic management",
      "modern city sunset high tech",
      "electric grid power lines digital",
      "connected vehicles smart city"]),

    # Future Devices & Gadgets (New)
    (["future_devices", "ar hud", "wearable", "smart tire", "gadget", "ar"],
     ["augmented reality car windshield",
      "futuristic tech gadget device",
      "smart wearable technology",
      "digital HUD display automotive"]),
]

# Generic EV fallback queries — used when no keyword matches
FALLBACK_QUERIES = [
    "electric car driving road",
    "EV charging station modern",
    "electric vehicle technology",
    "clean energy automobile",
    "modern electric car exterior",
]


def get_queries(topic: str, category_id: str = "") -> list[str]:
    """
    Return ranked list of search queries for the given topic string.
    First match wins. Always appends 1 fallback query at the end.
    """
    combined = (topic + " " + category_id).lower()

    for keywords, queries in TOPIC_QUERY_MAP:
        if any(kw in combined for kw in keywords):
            # Return matched queries + 1 fallback for safety
            return queries + [FALLBACK_QUERIES[0]]

    # No match — return all fallbacks
    return FALLBACK_QUERIES


def get_queries_for_script(script: str, topic: str,
                            category_id: str = "") -> list[str]:
    """
    Extract queries from the narration script text for richer matching.
    Combines topic match + script keyword scan.
    """
    base = get_queries(topic, category_id)

    # Scan script for additional keywords
    script_lower = script.lower()
    extras = []
    if any(w in script_lower for w in ["winter", "cold", "snow", "kış"]):
        extras.append("car driving snow winter")
    if any(w in script_lower for w in ["highway", "otoyol", "motorway"]):
        extras.append("highway driving car aerial")
    if any(w in script_lower for w in ["charge", "şarj", "plug"]):
        extras.append("electric car charging closeup")
    if any(w in script_lower for w in ["battery", "pil", "kwh"]):
        extras.append("battery technology electric")

    # Deduplicate while preserving order
    seen = set()
    result = []
    for q in base + extras:
        if q not in seen:
            seen.add(q)
            result.append(q)
    return result
