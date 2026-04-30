#!/usr/bin/env python3
"""
Evcarix YouTube Content Generator
Generates SEO title, description, tags (500 char), and Shorts script for each topic.
Usage:
  python generate_content.py                  # generate all pending topics
  python generate_content.py --id 5           # generate single topic by id
  python generate_content.py --priority high  # generate only high-priority topics
  python generate_content.py --category battery
  python generate_content.py --force          # regenerate even if output exists
"""

import os
import csv
import json
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime

try:
    from groq import Groq
except ImportError:
    print("ERROR: groq package not found. Run: pip install groq")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
MODEL         = "llama-3.3-70b-versatile"
MAX_TOKENS    = 2048
DELAY_SECONDS = 2          # pause between API calls to respect rate limits
DATA_DIR      = Path(__file__).parent.parent / "data"
OUTPUT_DIR    = Path(__file__).parent.parent / "output"
TOPICS_CSV    = DATA_DIR / "topics.csv"

SYSTEM_PROMPT = """You are an elite YouTube SEO specialist for "Evcarix" — a data-driven EV channel.
Channel motto: "No hype. Just numbers." — Real test data, shocking statistics, no marketing fluff.
Primary audience: American EV enthusiasts + international viewers.

Return ONLY a valid JSON object with these exact fields (no markdown, no code blocks, no extra text):
{
  "title": "YouTube title max 60 chars. Must open with a data hook or provocative question. High CTR style. Example: 'Fast Charging KILLS Battery? Real 500,000km Data'",

  "description": "Full YouTube description 400-500 words. Structure:\\n1) HOOK: First line with shocking stat or question (this is above the fold)\\n2) WHAT YOU LEARN: 3 bullet points starting with •\\n3) KEY FINDINGS: 2 paragraphs with real data context\\n4) WHY IT MATTERS: 1 short paragraph\\n5) CHANNEL LINE: One sentence about Evcarix — No hype. Just numbers.\\n6) HASHTAGS: 8 hashtags on last line\\nNaturally integrate EV keywords throughout. Do not use generic filler.",

  "tags": "Comma-separated YouTube tags. CRITICAL: total character count including commas must be UNDER 500 characters. Order by search volume descending. Mix: 3 very broad EV terms + 4 medium specificity + 4 long-tail exact match terms. No duplicates.",

  "shorts_script": "60-second vertical 9:16 Shorts script. Use this exact format for each section:\\n\\n[HOOK — 0 to 3s]\\nSpoken line: <the line>\\n(VISUAL: <what appears on screen>)\\n\\n[SHOCKING STAT — 3 to 8s]\\nSpoken line: <the line>\\n(VISUAL: <bold text overlay description>)\\n\\n[MYTH vs REALITY — 8 to 20s]\\nSpoken line: <the line>\\n(VISUAL: <split screen or animation note>)\\n\\n[DATA REVEAL — 20 to 45s]\\nSpoken line: <the line>\\n(VISUAL: <chart, graph, or data visualization note>)\\n\\n[KEY TAKEAWAY — 45 to 55s]\\nSpoken line: <the line>\\n(VISUAL: <text overlay with key number>)\\n\\n[CTA — 55 to 60s]\\nSpoken line: <subscribe hook tied to the topic>\\n(VISUAL: subscribe button animation)"
}"""


def load_topics(csv_path: Path) -> list[dict]:
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def output_path(topic_id: str, topic_text: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "- " else "_" for c in topic_text[:50]).strip()
    return OUTPUT_DIR / f"{int(topic_id):03d}_{safe}.json"


def already_generated(topic_id: str, topic_text: str) -> bool:
    return output_path(topic_id, topic_text).exists()


def generate_content(client: Groq, topic: dict) -> dict:
    user_msg = (
        f"Category: {topic['category_title']}\n"
        f"Topic: {topic['topic']}\n"
        f"Priority: {topic['priority']}\n\n"
        f"Generate complete YouTube SEO content for this Evcarix video."
    )

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
    )

    raw = response.choices[0].message.content
    # strip markdown fences if model added them
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```", 2)[-1]
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.rsplit("```", 1)[0].strip()

    parsed = json.loads(clean)

    # enforce 500-char tag limit
    if len(parsed.get("tags", "")) > 500:
        tags = parsed["tags"].split(",")
        trimmed, total = [], 0
        for t in tags:
            chunk = t.strip()
            if total + len(chunk) + 2 > 500:
                break
            trimmed.append(chunk)
            total += len(chunk) + 2
        parsed["tags"] = ", ".join(trimmed)

    return parsed


def save_result(topic: dict, content: dict) -> Path:
    out = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "topic_id": topic["id"],
        "category": topic["category_title"],
        "topic": topic["topic"],
        "priority": topic["priority"],
        "content": content,
        "stats": {
            "title_chars": len(content.get("title", "")),
            "description_words": len(content.get("description", "").split()),
            "tags_chars": len(content.get("tags", "")),
            "tags_count": len(content.get("tags", "").split(",")),
        },
    }
    path = output_path(topic["id"], topic["topic"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return path


def build_summary(topics: list[dict]) -> None:
    """Write output/SUMMARY.md with all generated content at a glance."""
    rows = []
    for t in topics:
        p = output_path(t["id"], t["topic"])
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        c = data["content"]
        rows.append(
            f"## {t['id']}. {c.get('title','—')}\n"
            f"**Category:** {t['category_title']}  \n"
            f"**Topic:** {t['topic']}  \n"
            f"**Tags ({data['stats']['tags_chars']} chars):** `{c.get('tags','')}`\n\n"
            f"<details><summary>Description</summary>\n\n{c.get('description','')}\n\n</details>\n\n"
            f"<details><summary>Shorts Script</summary>\n\n{c.get('shorts_script','')}\n\n</details>\n\n---\n"
        )
    summary = OUTPUT_DIR / "SUMMARY.md"
    with open(summary, "w", encoding="utf-8") as f:
        f.write(f"# Evcarix Content Summary\n\nGenerated: {datetime.utcnow().isoformat()}Z\n\n")
        f.write("\n".join(rows))
    print(f"  📄 Summary written → {summary}")


def main():
    parser = argparse.ArgumentParser(description="Evcarix content generator")
    parser.add_argument("--id",       type=int,   help="Generate single topic by id")
    parser.add_argument("--category", type=str,   help="Filter by category_id (e.g. battery)")
    parser.add_argument("--priority", type=str,   choices=["high","medium","new"], help="Filter by priority")
    parser.add_argument("--force",    action="store_true", help="Regenerate even if output exists")
    parser.add_argument("--dry-run",  action="store_true", help="Show what would be generated, no API calls")
    parser.add_argument("--summary",  action="store_true", help="Only rebuild SUMMARY.md from existing outputs")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key and not args.dry_run and not args.summary:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        sys.exit(1)

    topics = load_topics(TOPICS_CSV)

    if args.summary:
        build_summary(topics)
        return

    # Apply filters
    if args.id:
        topics = [t for t in topics if int(t["id"]) == args.id]
    if args.category:
        topics = [t for t in topics if t["category_id"] == args.category]
    if args.priority:
        topics = [t for t in topics if t["priority"] == args.priority]
    if not args.force:
        topics = [t for t in topics if not already_generated(t["id"], t["topic"])]

    if not topics:
        print("✅ Nothing to generate (all topics already have output). Use --force to regenerate.")
        return

    print(f"\n⚡ Evcarix Content Generator")
    print(f"   Model  : {MODEL}")
    print(f"   Topics : {len(topics)}")
    print(f"   Dry run: {args.dry_run}\n")

    if args.dry_run:
        for t in topics:
            print(f"  [{t['id']:>2}] {t['category_title']} → {t['topic']}")
        return

    client = Groq(api_key=api_key)

    ok, fail = 0, 0
    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] Generating: {topic['topic'][:60]}")
        try:
            content = generate_content(client, topic)
            path = save_result(topic, content)
            print(f"  ✓ Saved → {path.name}")
            print(f"    Title ({len(content.get('title',''))} chars): {content.get('title','')}")
            print(f"    Tags  ({len(content.get('tags',''))} chars)")
            ok += 1
        except Exception as e:
            print(f"  ✗ FAILED: {e}")
            fail += 1

        if i < len(topics):
            time.sleep(DELAY_SECONDS)

    print(f"\n{'='*50}")
    print(f"Done. ✓ {ok} generated  ✗ {fail} failed")

    build_summary(topics)


if __name__ == "__main__":
    main()
