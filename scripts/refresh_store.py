#!/usr/bin/env python3
"""Refresh a minimal public MW4 store snapshot from itemshop.gg's documented API.

API credentials are never stored in the public JSON or logged. This script does not
access any Activision account, retrieve personalized deals, or scrape web pages.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_URL = "https://itemshop.gg/api/v1/shop/call-of-duty"
PROVIDER_URL = "https://itemshop.gg/call-of-duty"
MAX_JSON_BYTES = 3_000_000
MAX_ITEMS = 30
MAX_CONTENTS = 20
ALLOWED_IMAGE_HOSTS = {"cdn.source.gs", "itemshop.gg", "mw4.source.gs"}
OFFICIAL_HOSTS = {"callofduty.com", "www.callofduty.com"}


def safe_text(value: object, limit: int = 140) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = re.sub(r"[\x00-\x1f\x7f<>]", " ", value)
    return re.sub(r"\s+", " ", cleaned).strip()[:limit]


def safe_url(value: object, hosts: set[str]) -> str | None:
    if not isinstance(value, str) or len(value) > 1500:
        return None
    try:
        p = urlsplit(value)
    except ValueError:
        return None
    if (p.scheme != "https" or p.hostname not in hosts or p.username
            or p.password or p.fragment or not p.path.startswith("/")):
        return None
    return value


def timestamp(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) > 36:
        raise ValueError(f"{label}: missing ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label}: invalid ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label}: timezone required")
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def optional_timestamp(value: object) -> str | None:
    if value is None:
        return None
    try:
        return timestamp(value, "availability")
    except ValueError:
        return None


def transform(payload: dict, *, checked_at: str) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("Shop response lacks data")
    data = payload["data"]
    if data.get("game") != "call-of-duty":
        raise ValueError("Wrong game: expecting call-of-duty")
    if not isinstance(data.get("sections"), list) or len(data["sections"]) > 100:
        raise ValueError("Invalid shop sections")
    if not isinstance(data.get("stale"), bool):
        raise ValueError("Missing source freshness status")
    updated_at = timestamp(data.get("updatedAt"), "updatedAt")
    shop_date = data.get("shopDate")
    if not isinstance(shop_date, str) or re.fullmatch(r"\d{4}-\d\d-\d\d", shop_date) is None:
        raise ValueError("Invalid store date")
    try:
        datetime.strptime(shop_date, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Impossible store date") from exc
    att = payload.get("meta", {}).get("attribution", {})
    att_url = safe_url(att.get("url") if isinstance(att, dict) else None, {"itemshop.gg"})
    if not att_url:
        raise ValueError("Provider attribution URL absent or unsafe")

    items = []
    seen = set()
    for section in data["sections"]:
        if not isinstance(section, dict):
            continue
        # This is intentionally strict: BO7/WZ-only listings must not leak into MW4.
        if safe_text(section.get("title"), 90).casefold() != "modern warfare 4":
            continue
        rows = section.get("items")
        if not isinstance(rows, list):
            raise ValueError("Invalid Modern Warfare 4 shop items")
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = safe_text(row.get("itemKey"), 110)
            name = safe_text(row.get("name"), 120)
            if not key or not name or key in seen:
                continue
            price = row.get("price") if isinstance(row.get("price"), dict) else {}
            amount = price.get("amount")
            if isinstance(amount, bool) or not (amount is None or isinstance(amount, (int, float)) and 0 <= amount <= 100_000):
                amount = None
            source = safe_url(row.get("sourceUrl"), OFFICIAL_HOSTS)
            card = row.get("images") if isinstance(row.get("images"), dict) else {}
            image = safe_url(card.get("card") or card.get("render"), ALLOWED_IMAGE_HOSTS)
            raw_contents = row.get("contents") if isinstance(row.get("contents"), list) else []
            contents = []
            for detail in raw_contents[:MAX_CONTENTS]:
                if not isinstance(detail, dict):
                    continue
                detail_name = safe_text(detail.get("name"), 90)
                if detail_name:
                    contents.append({"name": detail_name, "type": safe_text(detail.get("type"), 55)})
            availability = row.get("availability") if isinstance(row.get("availability"), dict) else {}
            badge = row.get("badge")
            if isinstance(badge, dict):
                badge = badge.get("label") or badge.get("text")
            seen.add(key)
            items.append({
                "id": key,
                "name": name,
                "type": safe_text(row.get("type"), 70),
                "image": image,
                "badge": safe_text(badge, 40) if badge else None,
                "price": {
                    "amount": amount,
                    "label": safe_text(price.get("label"), 60) or None,
                    "currency": safe_text(price.get("currency"), 45) or "COD Points",
                },
                "officialUrl": source,
                "upcoming": bool(section.get("upcoming")),
                "availability": {
                    "from": optional_timestamp(availability.get("from")),
                    "until": optional_timestamp(availability.get("until")),
                },
                "contents": contents,
            })
            if len(items) >= MAX_ITEMS:
                break
        if len(items) >= MAX_ITEMS:
            break
    # This is a small display projection, not an API key, full provider response,
    # archive of every COD item, or claim about personalized in-game inventory.
    return {
        "schema": 1,
        "provider": "itemshop.gg",
        "game": "call-of-duty",
        "status": "synced",
        "shopDate": shop_date,
        "updatedAt": updated_at,
        "checkedAt": timestamp(checked_at, "checkedAt"),
        "stale": data["stale"],
        "attribution": {"text": "Data from itemshop.gg", "url": att_url},
        "note": "Public MW4 web-store listings only. In-game offers, platform prices, and personalized bundles can differ.",
        "items": items,
    }


def fetch_live(api_key: str) -> dict:
    if not api_key or "\n" in api_key or "\r" in api_key:
        raise ValueError("ITEMSHOP_API_KEY is not set or invalid")
    req = Request(
        API_URL,
        headers={
            "Authorization": "Bearer " + api_key,
            "Accept": "application/json",
            "User-Agent": "MW4WarRoom/0.4 (personal public-store companion)",
        },
    )
    try:
        with urlopen(req, timeout=20) as response:
            if urlsplit(response.geturl()).hostname != "itemshop.gg":
                raise ValueError("Unexpected API redirect")
            if "json" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("Store response is not JSON")
            body = response.read(MAX_JSON_BYTES + 1)
    except HTTPError as exc:
        raise RuntimeError(f"Store API request failed: HTTP {exc.code} (no existing data was changed)") from None
    except URLError as exc:
        raise RuntimeError("Store API request failed; last good feed retained") from None
    if len(body) > MAX_JSON_BYTES:
        raise ValueError("Store response exceeds size limit")
    return json.loads(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path, help="Offline fixture for validation, not a live request")
    parser.add_argument("--checked-at", help="ISO UTC override only for deterministic tests")
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8")) if args.input else fetch_live(os.getenv("ITEMSHOP_API_KEY", ""))
    now = args.checked_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    projected = transform(source, checked_at=now)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Atomic file write means errors cannot corrupt or erase the last good feed.
    temp = args.output.with_name(args.output.name + ".next")
    temp.write_text(json.dumps(projected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(args.output)
    print(f"MW4 Store projection valid: {len(projected['items'])} MW4-only bundles; "
          f"source stale={projected['stale']}. No API credentials written.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print("Store refresh failed: " + str(exc), file=sys.stderr)
        sys.exit(1)
