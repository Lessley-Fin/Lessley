from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        records = payload.get("data", {}).get("records", [])
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
    return []


def _extract_benefit_type(record: dict[str, Any]) -> str | None:
    for key in ("benefit_type", "benefitType", "type"):
        value = record.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate HOT export data and verify records for a given benefit_type."
    )
    parser.add_argument(
        "--input",
        default=os.getenv("HOT_TEST_INPUT", "./outputs/hot_getAllBenefits.json"),
        help="Path to export JSON file.",
    )
    parser.add_argument(
        "--benefit-type",
        required=True,
        help="Expected benefit_type (example: 1100).",
    )
    parser.add_argument(
        "--allow-mixed-types",
        action="store_true",
        help="Do not fail when file contains records with other benefit types.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    input_path = Path(args.input)
    expected_type = str(args.benefit_type).strip()

    if not input_path.exists():
        print(f"[FAIL] Input file not found: {input_path.resolve()}")
        raise SystemExit(1)

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAIL] Invalid JSON: {exc}")
        raise SystemExit(1)

    records = _extract_records(payload)
    if not records:
        print("[FAIL] No records found in export file.")
        raise SystemExit(1)

    missing_type = 0
    matching = 0
    non_matching = 0
    type_counts: Counter[str] = Counter()
    ids: list[str] = []

    for record in records:
        record_id = str(record.get("id") or "").strip()
        if record_id:
            ids.append(record_id)

        record_type = _extract_benefit_type(record)
        if record_type is None:
            missing_type += 1
            continue

        type_counts[record_type] += 1
        if record_type == expected_type:
            matching += 1
        else:
            non_matching += 1

    duplicate_ids = len(ids) - len(set(ids))

    print(f"[INFO] File: {input_path.resolve()}")
    print(f"[INFO] Total records: {len(records)}")
    print(f"[INFO] Records with expected benefit_type={expected_type}: {matching}")
    print(f"[INFO] Records with other benefit types: {non_matching}")
    print(f"[INFO] Records missing benefit type: {missing_type}")
    print(f"[INFO] Unique benefit types: {dict(type_counts)}")
    print(f"[INFO] Duplicate ids: {duplicate_ids}")

    errors: list[str] = []
    if matching == 0:
        errors.append(f"No records matched benefit_type={expected_type}.")
    if missing_type > 0:
        errors.append(f"{missing_type} records are missing benefit_type fields.")
    if duplicate_ids > 0:
        errors.append(f"{duplicate_ids} duplicate ids found.")
    if non_matching > 0 and not args.allow_mixed_types:
        errors.append(
            f"Found {non_matching} records with benefit type different from {expected_type}."
        )

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        raise SystemExit(1)

    print("[PASS] Export data validation passed.")


if __name__ == "__main__":
    main()

