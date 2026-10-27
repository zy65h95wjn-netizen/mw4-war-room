#!/usr/bin/env python3
"""Review-only, non-scraping schedule monitor for War Room's curated data.

This does not contact Activision, CODMunity, WZStats or any external provider,
does not imply a new patch was published, and never edits data/intel.json.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from validate_intel import DEFAULT_PATH, SECTION_KEYS, valid_day, validate

REVIEW_SOURCES = {
    "meta": ("cod", "wz"),
    "builds": ("builds", "esports", "vGC"),
    "patches": ("officialIndex", "officialPatch"),
    "events": ("officialMaps", "boot", "roadmap"),
    "battlePass": ("officialBP", "roadmap"),
}
SECTION_NAMES = {"meta": "Multiplayer meta rankings", "builds": "Published loadouts", "patches": "Official patch summaries", "events": "Events and timed modes", "battlePass": "Battle Pass and BlackCell"}


def due_items(data: dict, today: date) -> list[dict]:
    pending = []
    for section in SECTION_KEYS:
        reviewed = valid_day(data["reviewedSections"][section], section)
        due = reviewed + timedelta(days=data["reviewLimitsDays"][section])
        if today > due:
            pending.append({"kind": "stale", "section": section, "date": due.isoformat(), "label": f"{SECTION_NAMES[section]}: review overdue since {due.isoformat()}"})

    reviewed_events = valid_day(data["reviewedSections"]["events"], "reviewedSections.events")
    for event in data["events"]:
        start = valid_day(event["starts"], "event starts")
        if reviewed_events < start <= today + timedelta(days=1):
            pending.append({"kind": "event-start", "section": "events", "date": start.isoformat(), "label": f"Verify event start: {event['title']} ({event['starts']})"})
        if event.get("ends"):
            end = valid_day(event["ends"], "event ends")
            if reviewed_events < end <= today + timedelta(days=2):
                pending.append({"kind": "event-end", "section": "events", "date": end.isoformat(), "label": f"Verify event end: {event['title']} ({event['ends']})"})

    reviewed_pass = valid_day(data["reviewedSections"]["battlePass"], "reviewedSections.battlePass")
    start = valid_day(data["battlePass"]["start"], "battlePass.start")
    if reviewed_pass < start <= today + timedelta(days=2):
        pending.append({"kind": "battle-pass", "section": "battlePass", "date": start.isoformat(), "label": f"Verify {data['battlePass']['label']} launch and rewards ({start.isoformat()})"})
    return pending


def markdown(data: dict, pending: list[dict]) -> str:
    lines = [
        "# War Room intelligence review",
        "",
        "This report checks **review ages and scheduled dates only**. It does not poll, scrape, or verify any publisher's current website. An overdue item is not evidence that its source changed.",
        "",
        f"Current curated snapshot: **{data['reviewed']}** — release **{data['release']}**.",
        "",
    ]
    if pending:
        lines += ["## Review needed", ""]
        for item in pending:
            lines.append(f"- [ ] {item['label']}")
    else:
        lines += ["## No overdue reviews or date triggers", "", "The automated check passed. No external change detection was performed."]
    source_map = {src["id"]: src for src in data["sources"]}
    lines += ["", "## Direct source links for editorial review", "", "These links are presented for a human reviewer; the watchdog does not fetch them.", ""]
    for section, source_ids in REVIEW_SOURCES.items():
        lines.append(f"### {SECTION_NAMES[section]}")
        for src_id in source_ids:
            if src_id in source_map:
                source = source_map[src_id]
                lines.append(f"- [{source['name']}]({source['url']}) ({source['class'].lower()})")
        lines.append("")
    lines += [
        "", "## Safe publication process", "",
        "1. Read the linked **official** notes for patches and season dates; read publisher sites **manually** for the meta and builds.",
        "2. Verify Multiplayer mode, exact facts, source URLs and any dates; do not infer a buff or nerf from tier-list movement.",
        "3. Edit only the supported editorial snapshot data. Update the appropriate `reviewedSections` dates **only after a real review**; update `reviewed` to the date of this publication.",
        "4. Run `python3 scripts/validate_intel.py` and `python3 -m unittest discover -s tests -v`. Publish only if both pass.",
        "5. The site reads the updated JSON on its next online load. No credentials or player data are involved.",
        "", "See the repository README for the source-policy limitations and archive/rollback instructions.", "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_PATH)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--markdown-file", type=Path)
    parser.add_argument("--output-file", type=Path, help="GitHub Actions output file (needs_review)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    validate(data, today=args.today)
    pending = due_items(data, args.today)
    report = markdown(data, pending)
    if args.markdown_file:
        args.markdown_file.write_text(report, encoding="utf-8")
    if args.output_file:
        with args.output_file.open("a", encoding="utf-8") as handle:
            handle.write(f"needs_review={'true' if pending else 'false'}\n")
    if args.json:
        print(json.dumps({"today": args.today.isoformat(), "needsReview": bool(pending), "items": pending}, indent=2))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())