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
                               [--oid-from-id] [--mcc-source codes.json]

`--check` reports what would change without writing.

`--oid-from-id` synthesises the `_id.$oid` for records that have none, deriving
it deterministically from the business key so re-running is a no-op instead of
churning the file.  Without it a missing `_id` is an error, which is what you
want for a real Mongo export.

`--mcc-source` supplies already-saved categories for records whose `mcc_codes`
is empty, as either a store list or an `{id: [codes]}` map.  A record's own
saved codes always win; this only fills the gaps, and without it an empty
`mcc_codes` falls back to OTHER.
"""

from __future__ import annotations

import argparse
import hashlib
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


def derive_oid(store_id: str) -> str:
    """A stable 24-hex ObjectId for a record that has none.

    Derived from the business key rather than generated, so the script stays
    idempotent — a random ObjectId would rewrite every record on every run and
    make the diff useless.  Nothing reads this value back: both seeding paths
    (`upsert_seed_file` and the `deals seed` command) overwrite `_id` with the
    business key on import, so it exists purely to satisfy the export shape.
    """
    return hashlib.sha1(store_id.encode("utf-8")).hexdigest()[:24]


def load_mcc_source(path: Path) -> dict[str, list[str]]:
    """`{store_id: [category, ...]}` from a store list or an id → codes map."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return {key: list(value) for key, value in raw.items() if value}
    codes: dict[str, list[str]] = {}
    for record in raw:
        found = (record.get("metadata") or {}).get("mcc_codes")
        if found:
            codes[record["id"]] = list(found)
    return codes


def normalize_metadata(
    value: Any,
    stats: Counter[str],
    *,
    store_id: str = "",
    mcc_source: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
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

    if raw_codes:
        mcc_codes = normalize_mcc_codes(raw_codes, fallback=FALLBACK_CATEGORY)
        if mcc_codes != list(raw_codes):
            stats["mcc_rewritten"] += 1
    else:
        # The record's own saved codes always win; only reach for the external
        # source when there are none, so this can never overwrite real data.
        from_source = (mcc_source or {}).get(store_id)
        if from_source:
            mcc_codes = normalize_mcc_codes(from_source, fallback=FALLBACK_CATEGORY)
            stats["mcc_filled_from_source"] += 1
        else:
            mcc_codes = normalize_mcc_codes(None, fallback=FALLBACK_CATEGORY)
            stats["mcc_missing_fell_back"] += 1

    return {"image_urls": image_urls, "mcc_codes": mcc_codes, "store_url": store_url}


def normalize_record(
    record: dict[str, Any],
    stats: Counter[str],
    *,
    oid_from_id: bool = False,
    mcc_source: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    store_id = record["id"]
    oid = (record.get("_id") or {}).get("$oid") if isinstance(record.get("_id"), dict) else None
    if oid is None:
        if not oid_from_id:
            stats["missing_oid"] += 1
            raise ValueError(f"record {store_id!r} has no _id.$oid (pass --oid-from-id to derive one)")
        oid = derive_oid(store_id)
        stats["oid_derived"] += 1

    for extra in set(record) - set(TOP_LEVEL_KEYS):
        stats[f"dropped_top_level:{extra}"] += 1

    return {
        "_id": {"$oid": oid},
        "id": store_id,
        "name": record.get("name") or "",
        "name_forms": normalize_name_forms(record.get("name_forms")),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "metadata": normalize_metadata(
            record.get("metadata"), stats, store_id=store_id, mcc_source=mcc_source
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", default=str(RESOURCES_DIR / "stores.json"))
    parser.add_argument("--check", action="store_true", help="Report changes without writing")
    parser.add_argument(
        "--oid-from-id",
        action="store_true",
        help="Derive _id.$oid from the business key when a record has none",
    )
    parser.add_argument(
        "--mcc-source",
        help="JSON of already-saved categories used only where mcc_codes is empty",
    )
    args = parser.parse_args()

    path = Path(args.file)
    original = path.read_text(encoding="utf-8")
    records = json.loads(original)

    mcc_source = load_mcc_source(Path(args.mcc_source)) if args.mcc_source else None
    if mcc_source is not None:
        print(f"mcc source: {len(mcc_source)} stores from {args.mcc_source}")

    stats: Counter[str] = Counter()
    normalized = [
        normalize_record(record, stats, oid_from_id=args.oid_from_id, mcc_source=mcc_source)
        for record in records
    ]

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
