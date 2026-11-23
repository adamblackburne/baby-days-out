#!/usr/bin/env python3
"""Check events.json before it goes live.

Usage: python3 scripts/validate.py [path/to/events.json]
Exits 0 if the file is valid, 1 (with a list of problems) if not.
"""
import json
import re
import sys
from datetime import date

TOP_KEYS = {"updated", "new_since", "week_start", "week_end", "notes", "events"}
REQUIRED = ["id", "title", "organiser", "date", "start", "end", "venue", "address",
            "area", "category", "age", "cost", "free", "booking", "url", "highlight", "added"]
OPTIONAL = {"urls", "highlight_reason"}
BANNED = {"status", "status_note", "age_note"}
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def is_date(s):
    try:
        date.fromisoformat(s)
        return len(s) == 10
    except (TypeError, ValueError):
        return False


def find_banned(obj, path="$"):
    """Yield paths of any banned keys, at any depth."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in BANNED:
                yield f"{path}.{k}"
            yield from find_banned(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from find_banned(v, f"{path}[{i}]")


def validate(data):
    errs = []
    if not isinstance(data, dict):
        return ["top level must be an object"]

    keys = set(data)
    if keys != TOP_KEYS:
        if TOP_KEYS - keys:
            errs.append(f"missing top-level keys: {sorted(TOP_KEYS - keys)}")
        if keys - TOP_KEYS:
            errs.append(f"unexpected top-level keys: {sorted(keys - TOP_KEYS)}")
    for k in ("updated", "new_since", "week_start", "week_end"):
        if k in data and not is_date(data[k]):
            errs.append(f"{k} is not a valid YYYY-MM-DD date: {data[k]!r}")
    if "notes" in data and not isinstance(data["notes"], str):
        errs.append("notes must be a string")
    errs += [f"banned key {p}" for p in find_banned(data)]

    events = data.get("events")
    if not isinstance(events, list):
        return errs + ["events must be a list"]

    seen_id, seen_url_date, seen_slot = {}, {}, {}
    for i, e in enumerate(events):
        where = f"event {i} ({e.get('id', '?') if isinstance(e, dict) else '?'})"
        if not isinstance(e, dict):
            errs.append(f"{where}: must be an object")
            continue
        missing = [f for f in REQUIRED if f not in e]
        if missing:
            errs.append(f"{where}: missing fields {missing}")
        extra = set(e) - set(REQUIRED) - OPTIONAL - BANNED
        if extra:
            errs.append(f"{where}: unexpected fields {sorted(extra)}")

        for f in REQUIRED:
            if f in ("free", "highlight"):
                if f in e and not isinstance(e[f], bool):
                    errs.append(f"{where}: {f} must be true or false")
            elif f in e and not isinstance(e[f], str):
                errs.append(f"{where}: {f} must be a string")

        for f in ("id", "title", "url"):
            if isinstance(e.get(f), str) and not e[f].strip():
                errs.append(f"{where}: {f} is empty")
        if isinstance(e.get("url"), str) and e["url"] and not e["url"].startswith("https://"):
            errs.append(f"{where}: url should start with https://")
        if e.get("area") not in ("local", "central"):
            errs.append(f"{where}: area must be 'local' or 'central', got {e.get('area')!r}")
        d = e.get("date")
        if d != "" and not is_date(d):
            errs.append(f"{where}: date is not YYYY-MM-DD or empty: {d!r}")
        if not is_date(e.get("added")):
            errs.append(f"{where}: added is not a valid date: {e.get('added')!r}")
        for f in ("start", "end"):
            v = e.get(f)
            if v != "" and not (isinstance(v, str) and TIME.match(v)):
                errs.append(f"{where}: {f} is not HH:MM or empty: {v!r}")
        if e.get("highlight") is True and not str(e.get("highlight_reason", "")).strip():
            errs.append(f"{where}: highlight is true but highlight_reason is missing")
        if "urls" in e:
            u = e["urls"]
            if not isinstance(u, list) or not all(
                    isinstance(x, dict) and set(x) == {"label", "url"} for x in u):
                errs.append(f"{where}: urls must be a list of {{label, url}}")

        # De-duplication rules
        def dup(table, key, label):
            if key in table:
                errs.append(f"{where}: duplicate {label} with event {table[key]}")
            else:
                table[key] = i

        dup(seen_id, e.get("id"), "id")
        if d:
            dup(seen_url_date, (e.get("url"), d), "url + date")
            if e.get("start"):
                dup(seen_slot, (e.get("venue"), d, e.get("start")), "venue + date + start")
    return errs


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "events.json"
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read {path}: {exc}")
        return 1
    errs = validate(data)
    if errs:
        print(f"FAIL: {len(errs)} problem(s) in {path}")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"OK: {path} is valid ({len(data['events'])} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
