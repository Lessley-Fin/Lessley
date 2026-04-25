"""
Patch stores.json MCC codes using Claude-verified data from stores_enriched.json.
Run: python scripts/patch_mcc_from_enriched.py [--dry-run] [--data-dir data]
"""
from __future__ import annotations
import json, argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) / "seed"
    stores_path = data_dir / "stores.json"
    enriched_path = data_dir / "stores_enriched.json"

    stores: list[dict] = json.loads(stores_path.read_text(encoding="utf-8"))
    enriched: list[dict] = json.loads(enriched_path.read_text(encoding="utf-8"))

    enriched_by_id: dict[str, dict] = {s["id"]: s for s in enriched}
    stores_ids: set[str] = {s["id"] for s in stores}

    stats = {"updated": 0, "appended": 0, "skipped": 0}

    for store in stores:
        sid = store["id"]
        e = enriched_by_id.get(sid)
        if not e:
            stats["skipped"] += 1
            continue

        e_mcc = e.get("metadata", {}).get("mcc_codes")
        if not e_mcc:
            stats["skipped"] += 1
            continue

        s_mcc = store.setdefault("metadata", {}).get("mcc_codes")
        if s_mcc == e_mcc:
            stats["skipped"] += 1
            continue

        safe = store['name'].encode('ascii', errors='replace').decode()
        print(f"  UPDATE {safe!r:45s}  {s_mcc} -> {e_mcc}")
        if not args.dry_run:
            store["metadata"]["mcc_codes"] = e_mcc
        stats["updated"] += 1

    # append stores only in enriched (8 extras)
    for e in enriched:
        if e["id"] not in stores_ids:
            e_mcc = e.get("metadata", {}).get("mcc_codes")
            safe = e['name'].encode('ascii', errors='replace').decode()
            print(f"  APPEND {safe!r:45s}  mcc={e_mcc}")
            if not args.dry_run:
                stores.append(e)
            stats["appended"] += 1

    if not args.dry_run:
        stores_path.write_text(
            json.dumps(stores, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(
        f"\nDone. updated={stats['updated']} appended={stats['appended']} skipped={stats['skipped']}"
        + (" [DRY RUN]" if args.dry_run else "")
    )


if __name__ == "__main__":
    main()
