#!/usr/bin/env python3
"""
Evcarix YouTube Shorts Content Generator
- Konu dışı görsel YASAK: sadece kategoriye özel whitelist görseller
- Format: 9:16 dikey Shorts (60 saniye)
- Çıktı: title · description · tags (<=500 chr) · shorts_script

Kullanım:
  python generate_content.py                   # bekleyen tüm konular
  python generate_content.py --id 5            # tek konu
  python generate_content.py --category battery
  python generate_content.py --priority high
  python generate_content.py --force
  python generate_content.py --dry-run
  python generate_content.py --summary
"""

import os, csv, json, time, argparse, sys, re
from pathlib import Path
from datetime import datetime

try:
    from groq import Groq
except ImportError:
    print("ERROR: pip install groq")
    sys.exit(1)

# ── Sabitler ───────────────────────────────────────────────────────────────────
MODEL      = "llama-3.3-70b-versatile"
MAX_TOKENS = 2048
DELAY_SEC  = 3
BASE       = Path(__file__).parent.parent
OUTPUT_DIR = BASE / "output"
TOPICS_CSV = BASE / "data" / "topics.csv"

# ── Kategori bazlı onaylı görsel listesi ──────────────────────────────────────
VISUAL_WHITELIST = {
    "battery": [
        "LFP battery cell cross-section diagram",
        "NMC NCA battery cell comparison chart",
        "battery pack 3D visualization",
        "degradation curve graph capacity percent charge cycle",
        "BMS circuit block diagram",
        "battery thermal heat map",
        "SOH bar graph percentage indicator",
        "solid-state vs liquid electrolyte comparison diagram",
        "1 million km line graph km capacity percent",
        "charge cycle voltage current animation frame",
    ],
    "range": [
        "range bar graph km per vehicle comparison",
        "temperature range curve degree km axis",
        "kWh 100km consumption bar chart",
        "summer winter range comparison side by side bar",
        "speed range curve animation frame",
        "highway vs city range split screen graph",
        "AC consumption pie chart energy distribution",
        "regenerative braking energy flow diagram",
        "vehicle weight range scatter plot graph",
    ],
    "charging": [
        "800V 400V charging speed comparison bar graph",
        "charging curve kW SoC percent line graph",
        "CCS CHAdeMO connector technical diagram",
        "DC fast charging AC home charging flow diagram",
        "V2G V2H energy flow diagram",
        "charging network map Europe America point density",
        "solar energy EV charging flow diagram",
        "night day charging cost bar graph",
        "cable length power loss line graph",
    ],
    "ownership": [
        "5 year total cost stacked bar graph EV diesel",
        "value loss curve year vehicle value axis graph",
        "insurance cost comparison bar graph",
        "maintenance cost breakdown pie chart brake tire service",
        "battery replacement cost timeline infographic",
        "100k km user data distribution dot graph",
        "warranty coverage layered infographic diagram",
    ],
    "comparison": [
        "vehicle comparison radar graph range charging cost",
        "segment price range scatter plot graph",
        "70 vehicle range ranking horizontal bar graph",
        "single axle dual axle efficiency comparison curve",
        "budget EV comparison table infographic",
        "SUV range test result bar graph",
        "America market price comparison bar graph",
    ],
    "market": [
        "country based EV sales percent world map choropleth",
        "brand market share pie chart 2024 2025 comparison",
        "China EV brands Europe market share growth line graph",
        "EV sales trend monthly line graph",
        "subsidy before after sales comparison bar graph",
        "EV price deflation trend line graph",
        "second hand market size annual bar graph",
    ],
    "infrastructure": [
        "charging station reliability percent bar graph",
        "America charging point density map state based",
        "apartment charging installation cost breakdown infographic",
        "charging time calculation table kW battery capacity",
        "grid load simulation hourly consumption graph",
        "smart vs standard charging comparison diagram",
        "renewable energy EV integration flow diagram",
    ],
    "education": [
        "heat pump working principle step flow diagram",
        "PTC heat pump efficiency comparison bar graph",
        "one-pedal regeneration power flow animation frame",
        "thermal management system schematic block diagram",
        "aerodynamic drag Cd value visualization",
        "charging curve drop point explained graph arrow",
        "SOH measurement method step by step block diagram",
        "inverter circuit block diagram DC AC conversion",
        "WLTP EPA real range comparison bar graph",
    ],
    "tools": [
        "range calculator interface screen diagram",
        "EV diesel cost calculator output bar graph",
        "charging cost calculation table diagram",
        "battery degradation prediction curve graph",
        "charging speed comparison real time bar graph",
        "range loss information graph infographic",
        "market share interactive pie chart diagram",
    ],
}

FORBIDDEN = (
    "NEVER use:\n"
    "- Real human face or recognizable person\n"
    "- Vehicle brand logo (Tesla, BMW, etc.) — only anonymous vehicle silhouette\n"
    "- Stock photo (smiling driver, charging hand, etc.)\n"
    "- Irrelevant nature/landscape/city visual\n"
    "- Real banknote or money visual\n"
    "- Social media interface (Twitter, Instagram, etc.)\n"
    "- Animated character or cartoon element\n"
    "- Clipart or generic stock graphic\n"
    "- Any visual NOT in the approved list above\n"
)


def build_system(category_id: str) -> str:
    allowed = VISUAL_WHITELIST.get(category_id, [])
    allowed_block = "\n".join(f"  {i+1}. {v}" for i, v in enumerate(allowed))

    return f"""You are an expert YouTube Shorts content producer for "Evcarix" channel.
Channel motto: "No hype. Just numbers." — Real test data, shocking statistics, no marketing fluff.
Primary audience: American EV enthusiasts + international viewers.

══════════════════════════════════════════
VISUAL RESTRICTION — STRICT RULE
══════════════════════════════════════════
Every (VISUAL: ...) note in Shorts script MUST be selected ONLY from this list:

{allowed_block}

{FORBIDDEN}

══════════════════════════════════════════
SHORTS FORMAT: 9:16 VERTICAL · 60 SECONDS
══════════════════════════════════════════
Size: 1080x1920 pixels. Full screen data chart + text overlay.

Return ONLY JSON (no markdown, no explanation, no other text):
{{
  "title": "Max 60 chars. Start with shocking data point or question. High CTR.",
  "description": "400-500 word YouTube description.\\n1) HOOK: Shocking stat above fold\\n2) WHAT YOU LEARN: 3 bullet points\\n3) KEY FINDINGS: 2 paragraphs\\n4) WHY IT MATTERS: 1 paragraph\\n5) CHANNEL: Evcarix - No hype. Just numbers.\\n6) 8 hashtags on last line",
  "tags": "Comma-separated tags. Total UNDER 500 characters. Order by search volume descending. 3 broad + 4 medium + 4 long-tail.",
  "shorts_script": "[HOOK 0-3s]\\nSpoken: <text>\\n(VISUAL: <only from list>)\\n\\n[SHOCKING STAT 3-8s]\\nSpoken: <text>\\n(VISUAL: <only from list - big number overlay>)\\n\\n[MYTH vs REALITY 8-20s]\\nSpoken: <text>\\n(VISUAL: <only from list>)\\n\\n[DATA REVEAL 20-45s]\\nSpoken: <text>\\n(VISUAL: <only from list - chart or diagram>)\\n\\n[KEY TAKEAWAY 45-55s]\\nSpoken: <text>\\n(VISUAL: <only from list - key number overlay>)\\n\\n[CTA 55-60s]\\nSpoken: <subscribe hook tied to topic>\\n(VISUAL: subscribe animation + Evcarix logo)"
}}"""


# ── Yardımcılar ────────────────────────────────────────────────────────────────
def load_topics() -> list[dict]:
    with open(TOPICS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def out_path(tid: str, topic: str) -> Path:
    safe = re.sub(r"[^\w\- ]", "_", topic[:50]).strip()
    return OUTPUT_DIR / f"{int(tid):03d}_{safe}.json"


def is_done(tid: str, topic: str) -> bool:
    return out_path(tid, topic).exists()


def trim_tags(tags: str) -> str:
    if len(tags) <= 500:
        return tags
    parts, total, out = tags.split(","), 0, []
    for p in parts:
        chunk = p.strip()
        needed = len(chunk) + (2 if out else 0)
        if total + needed > 500:
            break
        out.append(chunk)
        total += needed
    return ", ".join(out)


def check_visuals(script: str, category_id: str) -> list[str]:
    """Return (VISUAL: ...) notes not in approved list."""
    allowed = VISUAL_WHITELIST.get(category_id, [])
    found   = re.findall(r"\(VISUAL:\s*(.+?)\)", script, re.IGNORECASE)
    bad     = []
    for visual in found:
        v = visual.strip().lower()
        if not any(
            any(kw in v for kw in ref.lower().split())
            for ref in allowed
        ):
            bad.append(visual)
    return bad


# ── Üretim ────────────────────────────────────────────────────────────────────
def generate(client: Groq, topic: dict, max_retries: int = 2) -> dict:
    cat_id = topic["category_id"]

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": build_system(cat_id)},
                    {"role": "user", "content": (
                        f"Category: {topic['category_title']}\n"
                        f"Topic: {topic['topic']}\n"
                        f"Priority: {topic['priority']}\n\n"
                        "Generate complete YouTube Shorts content for this Evcarix video."
                    )}
                ],
                temperature=0.7,
            )

            raw = response.choices[0].message.content
            if not raw:
                raise ValueError("Empty response from API")

            # markdown fence temizle
            if raw.startswith("```"):
                raw = raw.split("```", 2)[-1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.rsplit("```", 1)[0].strip()

            if not raw:
                raise ValueError("Empty response after cleaning")

            parsed = json.loads(raw)
            parsed["tags"] = trim_tags(parsed.get("tags", ""))

            bad_visuals = check_visuals(parsed.get("shorts_script", ""), cat_id)
            if bad_visuals:
                parsed["_visual_warnings"] = bad_visuals

            return parsed

        except json.JSONDecodeError as e:
            print(f"  JSON parse error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                raise
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str.lower() or "429" in error_str:
                print(f"  Rate limit hit (attempt {attempt + 1}/{max_retries}): Waiting...")
                if attempt < max_retries - 1:
                    wait_time = 30 * (attempt + 1)
                    print(f"  Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Rate limit exceeded after {max_retries} attempts")
            else:
                print(f"  Error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))
                else:
                    raise


def save_result(topic: dict, content: dict) -> Path:
    record = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "topic_id":     topic["id"],
        "category":     topic["category_title"],
        "topic":        topic["topic"],
        "priority":     topic["priority"],
        "content":      content,
        "stats": {
            "title_chars":       len(content.get("title", "")),
            "description_words": len(content.get("description", "").split()),
            "tags_chars":        len(content.get("tags", "")),
            "tags_count":        len([t for t in content.get("tags", "").split(",") if t.strip()]),
            "visual_clean":      "_visual_warnings" not in content,
        },
    }
    path = out_path(topic["id"], topic["topic"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return path


def build_summary(topics: list[dict]) -> None:
    rows = []
    for t in topics:
        p = out_path(t["id"], t["topic"])
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        c    = d["content"]
        flag = "✅" if d["stats"].get("visual_clean") else "⚠️ Visual warning"
        rows.append(
            f"## {t['id']}. {c.get('title','—')} {flag}\n"
            f"**Category:** {t['category_title']}  \n"
            f"**Topic:** {t['topic']}  \n"
            f"**Tags ({d['stats']['tags_chars']} chars):** `{c.get('tags','')}`\n\n"
            f"<details><summary>Description</summary>\n\n{c.get('description','')}\n\n</details>\n\n"
            f"<details><summary>Shorts Script 9:16</summary>\n\n{c.get('shorts_script','')}\n\n</details>\n\n---\n"
        )
    summary = OUTPUT_DIR / "SUMMARY.md"
    with open(summary, "w", encoding="utf-8") as f:
        f.write(f"# Evcarix Content Summary\n\nGenerated: {datetime.utcnow().isoformat()}Z\n\n")
        f.write("\n".join(rows))
    print(f"  📄 SUMMARY.md → {summary}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Evcarix Shorts content generator")
    ap.add_argument("--id",       type=int, help="Topic ID (1-67)")
    ap.add_argument("--category", type=str, help="Category filter")
    ap.add_argument("--priority", type=str, choices=["high", "medium", "new"])
    ap.add_argument("--force",    action="store_true")
    ap.add_argument("--dry-run",  action="store_true")
    ap.add_argument("--summary",  action="store_true")
    args = ap.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key and not args.dry_run and not args.summary:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        sys.exit(1)

    topics = load_topics()

    if args.summary:
        build_summary(topics)
        return

    if args.id:        topics = [t for t in topics if int(t["id"]) == args.id]
    if args.category:  topics = [t for t in topics if t["category_id"] == args.category]
    if args.priority:  topics = [t for t in topics if t["priority"] == args.priority]
    if not args.force: topics = [t for t in topics if not is_done(t["id"], t["topic"])]

    if not topics:
        print("No topics to generate. Use --force to regenerate.")
        return

    print(f"\n⚡ Evcarix Shorts Content Generator")
    print(f"   Model  : {MODEL}")
    print(f"   Format : 9:16 vertical Shorts - 60 seconds")
    print(f"   Topics : {len(topics)}")
    print(f"   Dry-run: {args.dry_run}\n")

    if args.dry_run:
        for t in topics:
            wl = len(VISUAL_WHITELIST.get(t["category_id"], []))
            print(f"  [{t['id']:>2}] {t['category_title']} ({wl} approved visuals) -> {t['topic']}")
        return

    client = Groq(api_key=api_key)
    ok = fail = warn = 0

    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] {topic['topic'][:65]}")
        try:
            content = generate(client, topic)
            path    = save_result(topic, content)
            w       = content.get("_visual_warnings", [])
            if w:
                warn += 1
                print(f"  VISUAL WARNING: {w}")
            print(f"  Saved -> {path.name}")
            print(f"  Title ({len(content.get('title',''))} chars): {content.get('title','')}")
            print(f"  Tags ({len(content.get('tags',''))} chars)")
            ok += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            fail += 1

        if i < len(topics):
            time.sleep(DELAY_SEC)

    print(f"\n{'='*55}")
    print(f"Done. {ok} generated  {fail} errors  {warn} visual warnings")
    build_summary(topics)


if __name__ == "__main__":
    main()
