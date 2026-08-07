#!/usr/bin/env python3
"""Rewrite stores.json into the canonical Mongo-export shape.

Every record ends up as exactly:

    {
        "_id": {"$oid": "..."},
        "id": "...",
        "name": "...",
        "name_forms": {"normalized": "...", "compact": "...", "tokens": [...]},
        "created_at": "...",
        "updated_at": "...",
        "metadata": {"image_urls": [...], "mcc_codes": [...], "store_url": "..."}
    }

Keys are emitted in that order, `metadata` holds those three keys and nothing
else (enrichment bookkeeping like `official_name` / `mcc_confidence` is
dropped), and `mcc_codes` is validated against the canonical 46-category
vocabulary in `lessley_deals.enrichment.mcc_catalog`, with legacy 4-digit codes
resolved through the saved mapping in `mccs.json`.

Usage:
    python normalize_stores.py [--check] [--file stores.json]

`--check` reports what would change without writing.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RESOURCES_DIR = Path(__file__).resolve().parent
REPO_ROOT = RESOURCES_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "lessley-deals" / "src"))

from lessley_deals.enrichment.mcc_catalog import (  # noqa: E402
    FALLBACK_CATEGORY,
    normalize_mcc_codes,
    unresolvable_codes,
)

TOP_LEVEL_KEYS = ("_id", "id", "name", "name_forms", "created_at", "updated_at", "metadata")
NAME_FORM_KEYS = ("normalized", "compact", "tokens")
METADATA_KEYS = ("image_urls", "mcc_codes", "store_url")


def normalize_name_forms(value: Any) -> dict[str, Any]:
    forms = value if isinstance(value, dict) else {}
    tokens = forms.get("tokens") or []
    return {
        "normalized": forms.get("normalized") or "",
        "compact": forms.get("compact") or "",
        "tokens": list(tokens),
    }


def normalize_metadata(value: Any, stats: Counter[str]) -> dict[str, Any]:
    metadata = value if isinstance(value, dict) else {}

    for dropped in set(metadata) - set(METADATA_KEYS):
        stats[f"dropped:{dropped}"] += 1

    image_urls = metadata.get("image_urls")
    if not isinstance(image_urls, list):
        stats["filled:image_urls"] += 1
        image_urls = [] if image_urls is None else [image_urls]

    # Kept as null rather than "" when unknown: the Gateway projection and the
    # url enricher both distinguish "no URL found yet" from a blank one.
    store_url = metadata.get("store_url")
    if store_url is not None and not isinstance(store_url, str):
        store_url = str(store_url)
    if "store_url" not in metadata:
        stats["filled:store_url"] += 1

    raw_codes = metadata.get("mcc_codes")
    rejected = unresolvable_codes(raw_codes)
    if rejected:
        stats["mcc_rejected_values"] += len(rejected)
    mcc_codes = normalize_mcc_codes(raw_codes, fallback=FALLBACK_CATEGORY)
    if not raw_codes:
        stats["mcc_missing_filled"] += 1
    elif mcc_codes != list(raw_codes):
        stats["mcc_rewritten"] += 1

    return {"image_urls": image_urls, "mcc_codes": mcc_codes, "store_url": store_url}


def normalize_record(record: dict[str, Any], stats: Counter[str]) -> dict[str, Any]:
    oid = (record.get("_id") or {}).get("$oid") if isinstance(record.get("_id"), dict) else None
    if oid is None:
        stats["missing_oid"] += 1
        raise ValueError(f"record {record.get('id')!r} has no _id.$oid")

    for extra in set(record) - set(TOP_LEVEL_KEYS):
        stats[f"dropped_top_level:{extra}"] += 1

    return {
        "_id": {"$oid": oid},
        "id": record["id"],
        "name": record.get("name") or "",
        "name_forms": normalize_name_forms(record.get("name_forms")),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "metadata": normalize_metadata(record.get("metadata"), stats),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(RESOURCES_DIR / "stores.json"))
    parser.add_argument("--check", action="store_true", help="Report changes without writing")
    args = parser.parse_args()

    path = Path(args.file)
    original = path.read_text(encoding="utf-8")
    records = json.loads(original)

    stats: Counter[str] = Counter()
    normalized = [normalize_record(record, stats) for record in records]

    output = json.dumps(normalized, ensure_ascii=False, indent=4)
    changed = output != original

    print(f"records: {len(records)}")
    for key in sorted(stats):
        print(f"  {key}: {stats[key]}")
    print(f"changed: {changed}")

    if changed and not args.check:
        path.write_text(output, encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
