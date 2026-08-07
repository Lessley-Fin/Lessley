#!/usr/bin/env python3
"""Rebuild `clubs.json` from the seed club definitions plus their member stores.

The club *definitions* (id, name, source_id, description) come from
`lessley-deals/data/seed/clubs.json`, which is the source of truth for which
clubs exist — it grows whenever a scraper is added.  The `stores` list is
derived here, because the seed file deliberately ships them empty.

Membership is derived from **`source_id`, not `club_id`**: every deal currently
carries `club_id = None`, because deals produced in JSON mode before
`data/clubs.json` existed got an empty source→club map (see the warning in
`persistence/seeding.py`).  Each club declares its `source_id`, so joining on
that recovers the membership the `club_id` field was supposed to hold.

The result is the union of what the file already listed and what the deals
imply, so a store is never dropped from a club it was previously in; only
store_ids absent from the canonical `stores` collection are removed, to keep
the list free of dangling references.  Output is sorted, making the script
idempotent — re-running produces a byte-identical file.

Usage:
    python build_clubs.py [--check] [--deals-db lessley]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

RESOURCES_DIR = Path(__file__).resolve().parent
REPO_ROOT = RESOURCES_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "lessley-deals" / "src"))

SEED_CLUBS = REPO_ROOT / "lessley-deals" / "data" / "seed" / "clubs.json"
CLUBS_FILE = RESOURCES_DIR / "clubs.json"

CLUB_KEYS = ("id", "name", "source_id", "description", "metadata", "stores")


def build(check: bool = False) -> int:
    from lessley_deals.persistence.mongo_client import get_database

    db = get_database()
    known_stores = set(db["stores"].distinct("_id"))

    definitions: list[dict[str, Any]] = json.loads(SEED_CLUBS.read_text(encoding="utf-8"))
    existing = {c["id"]: c for c in json.loads(CLUBS_FILE.read_text(encoding="utf-8"))}

    original = CLUBS_FILE.read_text(encoding="utf-8")
    clubs: list[dict[str, Any]] = []

    print(f"{'club':34}{'kept':>7}{'added':>7}{'dangling':>10}{'total':>8}")
    for definition in definitions:
        club_id = definition["id"]
        was = {s for s in existing.get(club_id, {}).get("stores", [])}
        derived = {s for s in db["deals"].distinct("store_id", {"source_id": definition["source_id"]}) if s}

        merged = was | derived
        dangling = merged - known_stores
        stores = sorted(merged & known_stores)

        print(
            f"  {club_id:32}{len(was & known_stores):>7}{len(derived - was):>7}"
            f"{len(dangling):>10}{len(stores):>8}"
        )

        clubs.append(
            {
                "id": club_id,
                "name": definition["name"],
                "source_id": definition["source_id"],
                "description": definition["description"],
                "metadata": definition.get("metadata") or {},
                "stores": stores,
            }
        )

    for club in clubs:
        assert tuple(club) == CLUB_KEYS, f"key order drift on {club['id']}"

    orphaned = set(existing) - {c["id"] for c in clubs}
    if orphaned:
        print(f"\nWARNING: in clubs.json but not in the seed definitions: {sorted(orphaned)}")

    output = json.dumps(clubs, ensure_ascii=False, indent=2) + "\n"
    changed = output != original
    print(f"\nclubs: {len(clubs)}  changed: {changed}")

    if changed and not check:
        CLUBS_FILE.write_text(output, encoding="utf-8")
        print(f"wrote {CLUBS_FILE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="Report changes without writing")
    args = parser.parse_args()
    return build(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
