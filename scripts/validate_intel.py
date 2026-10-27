#!/usr/bin/env python3
"""War Room curated briefing validation. No network access or third-party dependencies."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / "data" / "intel.json"
CATEGORIES = {"AR", "SMG", "Shotgun", "LMG", "Marksman", "Sniper", "Pistol", "Launcher", "Melee"}
SECTION_KEYS = ("meta", "builds", "patches", "events", "battlePass")
LIMITS = {"meta": 3, "builds": 10, "patches": 3, "events": 2, "battlePass": 4}
OFFICIAL_DOMAINS = {"www.callofduty.com", "callofduty.com", "support.activision.com"}


class IntelInvalid(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IntelInvalid(message)


def valid_day(value: object, location: str) -> date:
    require(isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)), f"{location}: requires YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise IntelInvalid(f"{location}: impossible date {value}") from exc


def text(value: object, name: str) -> None:
    require(isinstance(value, str) and bool(value.strip()), f"{name}: nonempty text required")


def nonempty_list(value: object, name: str) -> None:
    require(isinstance(value, list) and bool(value), f"{name}: nonempty list required")


def validate(data: object, today: date | None = None) -> None:
    """Fail closed on malformed editorial data, without treating aged snapshots as false."""
    now = today or date.today()
    require(isinstance(data, dict), "briefing: object required")
    require(data.get("schema") == 2, "schema: expected 2")
    text(data.get("release"), "release")
    require(re.fullmatch(r"\d+\.\d+\.\d+", data["release"]) is not None, "release: expected semver")
    text(data.get("coverage"), "coverage")
    require(data["coverage"] == "Modern Warfare 4 multiplayer only", "coverage: must be Multiplayer only")
    text(data.get("sourcePolicy"), "sourcePolicy")
    valid_day(data.get("reviewed"), "reviewed")
    require(valid_day(data["reviewed"], "reviewed") <= now + timedelta(days=1), "reviewed: future dated")

    stamps = data.get("reviewedSections")
    limits = data.get("reviewLimitsDays")
    require(isinstance(stamps, dict) and set(stamps) == set(SECTION_KEYS), "reviewedSections: exact section keys required")
    require(isinstance(limits, dict) and set(limits) == set(SECTION_KEYS), "reviewLimitsDays: exact section keys required")
    for key in SECTION_KEYS:
        day = valid_day(stamps[key], f"reviewedSections.{key}")
        require(day <= now + timedelta(days=1), f"reviewedSections.{key}: future review date")
        require(isinstance(limits[key], int) and not isinstance(limits[key], bool) and limits[key] == LIMITS[key], f"reviewLimitsDays.{key}: expected {LIMITS[key]}")
        require(day <= valid_day(data["reviewed"], "reviewed"), f"reviewedSections.{key}: after snapshot date")

    sources = data.get("sources")
    nonempty_list(sources, "sources")
    ids: set[str] = set()
    for index, src in enumerate(sources):
        loc = f"sources[{index}]"
        require(isinstance(src, dict), f"{loc}: object required")
        for field in ("id", "name", "url"):
            text(src.get(field), f"{loc}.{field}")
        require(src["id"] not in ids, f"{loc}: duplicate source id {src['id']}")
        ids.add(src["id"])
        require(src.get("class") in {"Official", "Community"}, f"{loc}: unknown source class")
        url = urlparse(src["url"])
        require(url.scheme == "https" and url.hostname is not None and url.username is None and url.password is None and not url.fragment, f"{loc}: safe HTTPS URL required")
        if src["class"] == "Official":
            require(url.hostname in OFFICIAL_DOMAINS, f"{loc}: official source must use Activision-controlled domain")
    require({"officialPatch", "officialMaps", "officialBP", "cod", "wz"}.issubset(ids), "sources: mandatory sources missing")

    def ref(source_id: object, where: str) -> None:
        require(isinstance(source_id, str) and source_id in ids, f"{where}: unknown source id {source_id!r}")

    meta = data.get("meta")
    nonempty_list(meta, "meta")
    seen_meta: set[str] = set()
    for idx, m in enumerate(meta):
        loc = f"meta[{idx}]"
        require(isinstance(m, dict), f"{loc}: object required")
        for key in ("id", "name", "rankingType", "note"):
            text(m.get(key), f"{loc}.{key}")
        require(m["id"] not in seen_meta, f"{loc}: repeated ranking id")
        seen_meta.add(m["id"])
        ref(m.get("source"), f"{loc}.source")
        valid_day(m.get("updated"), f"{loc}.updated")
        nonempty_list(m.get("entries"), f"{loc}.entries")
        ranks = set()
        weapons = set()
        for k, w in enumerate(m["entries"]):
            p = f"{loc}.entries[{k}]"
            require(isinstance(w, dict), f"{p}: object required")
            text(w.get("weapon"), f"{p}.weapon")
            text(w.get("tier"), f"{p}.tier")
            require(w.get("category") in CATEGORIES, f"{p}: invalid category")
            require(type(w.get("rank")) is int and w["rank"] > 0, f"{p}: invalid rank")
            duplicate_key = w["rank"] if m["id"] == "cod" else (w["category"], w["rank"])
            require(duplicate_key not in ranks, f"{p}: repeated rank in same ranking scope")
            require(w["weapon"] not in weapons, f"{p}: repeated weapon")
            ranks.add(duplicate_key)
            weapons.add(w["weapon"])
    require({"cod", "wz"}.issubset(seen_meta), "meta: missing publisher split")

    builds = data.get("builds")
    nonempty_list(builds, "builds")
    build_ids = set()
    for idx, b in enumerate(builds):
        loc = f"builds[{idx}]"
        require(isinstance(b, dict), f"{loc}: object required")
        for key in ("id", "weapon", "style", "description"):
            text(b.get(key), f"{loc}.{key}")
        require(b["id"] not in build_ids, f"{loc}: duplicate build id")
        build_ids.add(b["id"])
        require(b.get("category") in CATEGORIES, f"{loc}: invalid category")
        require(type(b.get("optic")) is bool, f"{loc}: optic must be boolean")
        valid_day(b.get("updated"), f"{loc}.updated")
        ref(b.get("source"), f"{loc}.source")
        nonempty_list(b.get("parts"), f"{loc}.parts")
        require(1 <= len(b["parts"]) <= 5, f"{loc}: illegal standard attachment count")
        part_slots = set()
        for i, pair in enumerate(b["parts"]):
            require(isinstance(pair, list) and len(pair) == 2, f"{loc}.parts[{i}]: expected [slot,name]")
            text(pair[0], f"{loc}.parts[{i}].slot")
            text(pair[1], f"{loc}.parts[{i}].name")
            slot = pair[0].casefold()
            require(slot not in part_slots, f"{loc}: duplicate slot {slot}")
            part_slots.add(slot)
        require(("optic" in part_slots) == b["optic"], f"{loc}: optic flag contradicts attachment slots")
    require("han-iron" in build_ids, "builds: home spotlight missing han-iron")

    patches = data.get("patches")
    nonempty_list(patches, "patches")
    patch_dates: list[date] = []
    for idx, p in enumerate(patches):
        loc = f"patches[{idx}]"
        require(isinstance(p, dict), f"{loc}: object required")
        patch_dates.append(valid_day(p.get("date"), f"{loc}.date"))
        for key in ("title", "scope"):
            text(p.get(key), f"{loc}.{key}")
        ref(p.get("source"), f"{loc}.source")
        nonempty_list(p.get("bullet"), f"{loc}.bullet")
        for i, bullet in enumerate(p["bullet"]):
            text(bullet, f"{loc}.bullet[{i}]")
        require(p["scope"].startswith("Multiplayer"), f"{loc}: multiplayer-scoped content required")
    require(patch_dates == sorted(patch_dates, reverse=True), "patches: newest must come first")

    events = data.get("events")
    nonempty_list(events, "events")
    event_ids = set()
    for idx, ev in enumerate(events):
        loc = f"events[{idx}]"
        require(isinstance(ev, dict), f"{loc}: object required")
        for key in ("id", "title", "tag", "summary"):
            text(ev.get(key), f"{loc}.{key}")
        require(ev["id"] not in event_ids, f"{loc}: duplicate event id")
        event_ids.add(ev["id"])
        start = valid_day(ev.get("starts"), f"{loc}.starts")
        if ev.get("ends") is not None:
            require(valid_day(ev["ends"], f"{loc}.ends") >= start, f"{loc}: end precedes start")
        ref(ev.get("source"), f"{loc}.source")
        require(isinstance(ev.get("rewards"), list), f"{loc}: rewards list required")
        for i, reward in enumerate(ev["rewards"]):
            text(reward, f"{loc}.rewards[{i}]")

    bp = data.get("battlePass")
    require(isinstance(bp, dict), "battlePass: object required")
    for key in ("label", "status", "officialSummary", "startConfidence"):
        text(bp.get(key), f"battlePass.{key}")
    valid_day(bp.get("start"), "battlePass.start")
    for key in ("roadmapSource", "verifiedSource"):
        ref(bp.get(key), f"battlePass.{key}")
    require(isinstance(bp.get("tiersKnown"), bool), "battlePass.tiersKnown: boolean required")
    nonempty_list(bp.get("rewardCategories"), "battlePass.rewardCategories")
    bc = bp.get("blackcell")
    require(isinstance(bc, dict), "battlePass.blackcell: object required")
    require(type(bc.get("codPoints")) is int and bc["codPoints"] >= 0, "battlePass.blackcell.codPoints: nonnegative integer required")
    require(type(bc.get("tierSkips")) is int and bc["tierSkips"] >= 0, "battlePass.blackcell.tierSkips: nonnegative integer required")
    for k in ("totalRewards", "exclusive"):
        text(bc.get(k), f"battlePass.blackcell.{k}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
        validate(data)
        print(f"PASS: briefing schema, source references, weapon builds, ranks, dates, and multiplayer scope ({data['release']})")
        return 0
    except (IntelInvalid, json.JSONDecodeError, OSError) as exc:
        print(f"FAIL: invalid War Room briefing: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())