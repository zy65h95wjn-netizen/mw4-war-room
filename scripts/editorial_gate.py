#!/usr/bin/env python3
"""Enforce an evidence receipt when editorial data or freshness dates change.

Checks provenance metadata, not whether an external claim is true.
Does not connect to publishers, modify source data, or publish a site.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

SECTIONS = ("meta", "builds", "patches", "events", "battlePass")
REVIEW_TYPES = {"official-confirmed", "community-reported"}
OFFICIAL_HOSTS = {"www.callofduty.com", "callofduty.com", "support.activision.com"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{3,79}$")


class ReviewGateError(ValueError):
    """Proposed editorial change lacks valid source-review metadata."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ReviewGateError(reason)


def iso_day(value: object, field: str) -> date:
    require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None,
            f"{field}: expected YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ReviewGateError(f"{field}: impossible date") from exc


def validate_ledger(ledger: dict, intel: dict, today: date) -> None:
    require(isinstance(ledger, dict) and ledger.get("schema") == 1, "ledger schema must be 1")
    reviews = ledger.get("reviews")
    require(isinstance(reviews, list), "ledger reviews must be a list")
    sources = {x.get("id"): x for x in intel.get("sources", []) if isinstance(x, dict)}
    seen = set()
    for i, item in enumerate(reviews):
        where = f"reviews[{i}]"
        require(isinstance(item, dict), f"{where}: object required")
        ident = item.get("id")
        require(isinstance(ident, str) and ID_RE.fullmatch(ident) is not None and ident not in seen,
                f"{where}: unique lowercase hyphenated id required")
        seen.add(ident)
        section = item.get("section")
        require(section in (*SECTIONS, "sources"), f"{where}: invalid section")
        checked = iso_day(item.get("checkedAt"), f"{where}.checkedAt")
        require(checked <= today + timedelta(days=1), f"{where}: future-dated")
        kind = item.get("reviewType")
        require(kind in REVIEW_TYPES, f"{where}: invalid reviewType")
        require(item.get("method") == "human-source-review", f"{where}: a human-source-review is required")
        refs = item.get("sourceIds")
        require(isinstance(refs, list) and bool(refs) and len(refs) <= 8
                and all(isinstance(s, str) for s in refs) and len(set(refs)) == len(refs),
                f"{where}: distinct sourceIds required")
        require(all(s in sources for s in refs), f"{where}: unrecognized source")
        note = item.get("evidenceNote")
        require(isinstance(note, str) and 30 <= len(note.strip()) <= 1200,
                f"{where}: evidenceNote must be 30–1200 characters")
        if kind == "official-confirmed":
            require(any(sources[s].get("class") == "Official"
                        and urlsplit(sources[s].get("url", "")).hostname in OFFICIAL_HOSTS for s in refs),
                    f"{where}: official Activision source required")
        if section == "patches":
            require(kind == "official-confirmed", f"{where}: patch claims require official sources")
        if section in ("meta", "builds"):
            require(kind == "community-reported", f"{where}: publisher rankings/builds require attribution")


def changed_sections(before: dict, after: dict) -> set[str]:
    changed = {key for key in SECTIONS if before.get(key) != after.get(key)
               or before.get("reviewedSections", {}).get(key) != after.get("reviewedSections", {}).get(key)}
    if before.get("sources") != after.get("sources"):
        changed.add("sources")
    return changed


def check_change(before: dict, after: dict, old_ledger: dict, new_ledger: dict,
                 today: date | None = None) -> list[str]:
    today = today or date.today()
    validate_ledger(new_ledger, after, today)
    require(old_ledger.get("schema") == 1 and isinstance(old_ledger.get("reviews"), list),
            "old ledger malformed")
    old_reviews = old_ledger["reviews"]
    new_reviews = new_ledger["reviews"]
    require(new_reviews[:len(old_reviews)] == old_reviews,
            "historical source-review receipts must remain immutable and ordered")
    appended = new_reviews[len(old_reviews):]
    changed = changed_sections(before, after)
    require(before.get("coverage") == after.get("coverage"),
            "multiplayer-only coverage must remain unchanged")
    require(before.get("schema") == after.get("schema"),
            "schema upgrades require separate migration")
    require(not appended or changed, "cannot add review receipts without editorial changes")
    if not changed:
        return []
    for section in sorted(changed):
        matches = [x for x in appended if x.get("section") == section]
        require(len(matches) == 1,
                f"{section}: exactly one appended human-reviewed receipt required")
        reviewed = iso_day(matches[0]["checkedAt"], f"{section}.checkedAt")
        if section != "sources":
            stamp = iso_day(after.get("reviewedSections", {}).get(section), f"{section}.newStamp")
            old_stamp = iso_day(before.get("reviewedSections", {}).get(section), f"{section}.oldStamp")
            require(stamp == reviewed, f"{section}: freshness stamp must match reviewed source date")
            require(stamp >= old_stamp, f"{section}: review date must not go backwards")
    require(len(appended) == len(changed), "only changes to matching sections may add receipts")
    last = iso_day(after.get("reviewed"), "after.reviewed")
    require(last >= iso_day(before.get("reviewed"), "before.reviewed"), "snapshot date went backwards")
    require(last >= max(iso_day(x["checkedAt"], "receipt.checkedAt") for x in appended),
            "snapshot reviewed date must cover all new receipts")
    return sorted(changed)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--old-ledger", type=Path, required=True)
    parser.add_argument("--new-ledger", type=Path, required=True)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    try:
        touched = check_change(
            json.loads(args.before.read_text(encoding="utf-8")),
            json.loads(args.after.read_text(encoding="utf-8")),
            json.loads(args.old_ledger.read_text(encoding="utf-8")),
            json.loads(args.new_ledger.read_text(encoding="utf-8")), args.today)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"EDITORIAL GATE FAILED: {exc}", file=sys.stderr)
        return 1
    print("Editorial gate passed for: " + (", ".join(touched) or "no editorial change"))
    print("Receipt metadata cannot substitute for independently reviewing the original source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
