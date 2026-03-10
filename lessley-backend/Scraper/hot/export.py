from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import Settings

if TYPE_CHECKING:
    from hot.hot_scraper import HotScraper

BENEFIT_TYPES = ["100", "300", "700", "800", "1100", "1200", "1300"]
DEFAULT_BENEFITS_FILE = os.getenv(
    "HOT_BENEFITS_FILE", str(Path(__file__).parent / "outputs" / "hot_getAllBenefits.json")
)


def _resolve_types(benefit_types: list[str] | None) -> list[str]:
    return benefit_types if benefit_types else BENEFIT_TYPES


def _output_suffix(types: list[str]) -> str:
    if set(types) == set(BENEFIT_TYPES):
        return "_all"
    return "_" + "_".join(types)


def _get_hot_scraper_class():
    try:
        from hot.hot_scraper import HotScraper
    except ImportError as exc:
        raise RuntimeError(
            "Missing scraper dependencies. Install them with "
            "'pip install -r lessley-backend/Scraper/requirements.txt'."
        ) from exc
    return HotScraper


def _extract_detail_id(detail: dict) -> str:
    candidates = [
        detail.get("id"),
        detail.get("benefitId"),
        detail.get("request_payload", {}).get("benefitId")
        if isinstance(detail.get("request_payload"), dict)
        else None,
        detail.get("data", {}).get("main", {}).get("id")
        if isinstance(detail.get("data"), dict)
        else None,
    ]
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value:
            return value
    return ""


def _chunk_records(records: list[dict], chunk_size: int) -> list[list[dict]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    return [records[i:i + chunk_size] for i in range(0, len(records), chunk_size)]


def _load_records_from_file(path: Path, types: list[str]) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        records = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        records = data.get("data", {}).get("records", [])
        records = [r for r in records if isinstance(r, dict)]
    else:
        records = []

    if set(types) != set(BENEFIT_TYPES):
        records = [
            r for r in records
            if str(r.get("benefit_type") or r.get("benefitType") or "") in types
        ]

    return records


async def _collect_all_records_from_api(scraper: HotScraper, benefit_type: str) -> list[dict]:
    all_records: list[dict] = []
    page = scraper.settings.page_start

    while True:
        data = await scraper.fetch_benefits(page, benefit_type=benefit_type)
        if not data:
            break
        records = data.get("data", {}).get("records", [])
        if not records:
            print(f"[{scraper.club_name}] No more records after page {page}.")
            break
        all_records.extend(records)
        print(f"[{scraper.club_name}] Page {page}: fetched {len(records)} records.")
        page += 1
        await scraper.throttle()

    return all_records


async def _fetch_details_for_records(
    scraper: HotScraper,
    records: list[dict],
    is_commerce: str,
    label: str,
    seen_ids: set[str],
) -> tuple[list[dict], list[str]]:
    all_details: list[dict] = []
    failed: list[str] = []
    total = len(records)

    for i, record in enumerate(records, 1):
        benefit_id = str(record.get("id") or "").strip()
        if not benefit_id or benefit_id in seen_ids:
            continue
        seen_ids.add(benefit_id)

        details = await scraper.fetch_benefit_details(
            benefit_id=benefit_id, is_commerce=is_commerce
        )
        if details:
            all_details.append(details)
            print(f"[{scraper.club_name}][{label}] ({i}/{total}) id={benefit_id} OK")
        else:
            failed.append(benefit_id)
            print(f"[{scraper.club_name}][{label}] ({i}/{total}) id={benefit_id} FAILED")

        await scraper.throttle()

    return all_details, failed


async def _collect_records_for_type(
    bt: str,
    source: str,
    input_file: Path,
    settings: Settings,
) -> list[dict]:
    if source == "file":
        records = _load_records_from_file(input_file, [bt])
        print(f"[collector:{bt}] Loaded {len(records)} records from file.")
        return records

    HotScraper = _get_hot_scraper_class()
    scraper = HotScraper(settings)
    try:
        await scraper.initialize_session()
        print(f"[collector:{bt}] Fetching benefit list from API...")
        records = await _collect_all_records_from_api(scraper, bt)
    finally:
        await scraper.close()

    print(f"[collector:{bt}] Collected {len(records)} records from API.")
    return records


async def export_benefits(types: list[str], output_path: Path) -> None:
    HotScraper = _get_hot_scraper_class()
    settings = Settings.from_env()
    scraper = HotScraper(settings)
    label = ", ".join(types)
    print(f"[{scraper.club_name}] Exporting benefits (types: {label})...")

    all_records: list[dict] = []
    seen_ids: set[str] = set()

    try:
        await scraper.initialize_session()
        for bt in types:
            records = await _collect_all_records_from_api(scraper, bt)
            for record in records:
                record_id = str(record.get("id") or "")
                if record_id and record_id not in seen_ids:
                    seen_ids.add(record_id)
                    all_records.append(record)
    finally:
        await scraper.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"Export completed: {len(all_records)} records.")
    print(f"Output file: {output_path.resolve()}")


async def export_benefit_details(benefit_id: str, is_commerce: str, output_path: Path) -> None:
    HotScraper = _get_hot_scraper_class()
    settings = Settings.from_env()
    scraper = HotScraper(settings)

    try:
        await scraper.initialize_session()
        details = await scraper.fetch_benefit_details(benefit_id=benefit_id, is_commerce=is_commerce)
    finally:
        await scraper.close()

    if not details:
        raise RuntimeError(f"Failed to fetch details for benefitId={benefit_id}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(details, f, ensure_ascii=False, indent=2)

    print(f"Exported details for benefitId={benefit_id}")
    if "http_status" in details and details["http_status"] >= 400:
        print(f"Endpoint returned non-2xx status: {details['http_status']}")
    print(f"Output file: {output_path.resolve()}")


async def _worker_for_chunk(
    bt: str,
    is_commerce: str,
    records: list[dict],
    settings: Settings,
    chunk_index: int = 1,
    chunk_total: int = 1,
    startup_delay: float = 0.0,
) -> tuple[str, list[dict], list[str]]:
    HotScraper = _get_hot_scraper_class()
    if startup_delay > 0:
        await asyncio.sleep(startup_delay)

    scraper = HotScraper(settings)
    label = f"benefitType={bt} chunk={chunk_index}/{chunk_total}"

    try:
        await scraper.initialize_session()
        print(
            f"[worker:{bt}:{chunk_index}/{chunk_total}] "
            f"Fetching details for {len(records)} benefits..."
        )
        details, failed = await _fetch_details_for_records(
            scraper, records, is_commerce, label, seen_ids=set()
        )
    finally:
        await scraper.close()

    return bt, details, failed


async def export_all_details(
    types: list[str],
    is_commerce: str,
    output_path: Path,
    source: str,
    input_file: Path,
    request_delay: float | None = None,
    worker_stagger: float = 1.0,
    chunk_size: int = 50,
) -> None:
    settings = Settings.from_env()
    if request_delay is not None:
        settings.request_delay_seconds = request_delay

    if source == "file" and not input_file.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_file.resolve()}\n"
            "Run 'benefits' subcommand first, or use --source api."
        )

    records_by_type: dict[str, list[dict]] = {}
    for bt in types:
        records_by_type[bt] = await _collect_records_for_type(bt, source, input_file, settings)

    worker_jobs: list[tuple[str, list[dict], int, int]] = []
    for bt in types:
        records = records_by_type[bt]
        chunks = _chunk_records(records, chunk_size)
        total_chunks = len(chunks) or 1
        for chunk_index, chunk in enumerate(chunks, 1):
            worker_jobs.append((bt, chunk, chunk_index, total_chunks))

    print(
        f"[HOT] Starting {len(worker_jobs)} worker(s) for types: {', '.join(types)}\n"
        f"      request_delay={settings.request_delay_seconds}s  "
        f"worker_stagger={worker_stagger}s  chunk_size={chunk_size}"
    )

    results = await asyncio.gather(*[
        _worker_for_chunk(
            bt=bt,
            is_commerce=is_commerce,
            records=chunk,
            settings=settings,
            chunk_index=chunk_index,
            chunk_total=chunk_total,
            startup_delay=i * worker_stagger,
        )
        for i, (bt, chunk, chunk_index, chunk_total) in enumerate(worker_jobs)
    ])

    seen_ids: set[str] = set()
    combined_details: list[dict] = []
    combined_failed: list[str] = []

    for _, details, failed in results:
        for detail in details:
            detail_id = _extract_detail_id(detail)
            if detail_id and detail_id not in seen_ids:
                seen_ids.add(detail_id)
                combined_details.append(detail)
        combined_failed.extend(failed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(combined_details, f, ensure_ascii=False, indent=2)

    print(f"\n{'-' * 60}")
    print(f"Workers: {len(worker_jobs)}  |  Types: {', '.join(types)}")
    print(f"Export completed: {len(combined_details)} details saved, {len(combined_failed)} failed.")
    if combined_failed:
        print(f"Failed ids: {', '.join(combined_failed)}")
    print(f"Output file: {output_path.resolve()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="export.py",
        description=(
            "HOT scraper export tools.\n\n"
            "Subcommands:\n"
            "  benefits     Fetch the benefits list from the HOT API and save to JSON.\n"
            "  details      Fetch full details for a single benefit by id.\n"
            "  details-all  Fetch full details for every benefit and save to one JSON.\n\n"
            "Quick start:\n"
            "  python export.py benefits\n"
            "  python export.py benefits --benefit-type 1100 800\n\n"
            "  python export.py details 59373\n\n"
            "  python export.py details-all\n"
            "  python export.py details-all --benefit-type 1100 800\n"
            "  python export.py details-all --source api --benefit-type 1100 800\n\n"
            "Benefit types: " + " | ".join(BENEFIT_TYPES)
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    benefit_type_kwargs = dict(
        nargs="+",
        choices=BENEFIT_TYPES,
        default=None,
        metavar="TYPE",
        help=(
            "One or more benefit types to include. "
            "Allowed: " + ", ".join(BENEFIT_TYPES) + ". "
            "Default: all types."
        ),
    )

    p_benefits = sub.add_parser(
        "benefits",
        help="Fetch the HOT benefits list from the API and save to JSON.",
    )
    p_benefits.add_argument("--benefit-type", **benefit_type_kwargs)
    p_benefits.add_argument(
        "--output",
        default=os.getenv("HOT_BENEFITS_OUTPUT", "./outputs/hot_getAllBenefits.json"),
        help="Path for the output JSON file.",
    )

    p_details = sub.add_parser(
        "details",
        help="Fetch and save full details for a single HOT benefit.",
    )
    p_details.add_argument("benefit_id", help="HOT benefit id.")
    p_details.add_argument("--is-commerce", default="0", help="isCommerce payload value.")
    p_details.add_argument(
        "--output",
        default=None,
        help="Path for the output JSON file.",
    )

    p_all = sub.add_parser(
        "details-all",
        help="Fetch full details for every benefit and save them all to one JSON.",
    )
    p_all.add_argument("--benefit-type", **benefit_type_kwargs)
    p_all.add_argument("--is-commerce", default="0", help="isCommerce payload value.")
    p_all.add_argument(
        "--source",
        choices=["api", "file"],
        default=os.getenv("HOT_DETAILS_SOURCE", "file"),
        help="Read the benefit list from the API or a local JSON file.",
    )
    p_all.add_argument(
        "--input",
        default=DEFAULT_BENEFITS_FILE,
        help="Path to the local benefits JSON used when --source=file.",
    )
    p_all.add_argument(
        "--output",
        default=os.getenv("HOT_DETAILS_OUTPUT", "./outputs/hot_details_all.json"),
        help="Path for the combined output JSON file.",
    )
    p_all.add_argument(
        "--request-delay",
        type=float,
        default=None,
        help="Seconds to wait between each detail request inside a worker.",
    )
    p_all.add_argument(
        "--worker-stagger",
        type=float,
        default=float(os.getenv("HOT_WORKER_STAGGER", "1.0")),
        help="Seconds to stagger each worker startup.",
    )
    p_all.add_argument(
        "--chunk-size",
        type=int,
        default=int(os.getenv("HOT_DETAILS_CHUNK_SIZE", "50")),
        help="Number of benefits per detail worker chunk.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "benefits":
        types = _resolve_types(args.benefit_type)
        asyncio.run(export_benefits(types, Path(args.output)))
        return

    if args.command == "details":
        output = args.output or f"./outputs/hot_benefit_{args.benefit_id}.json"
        asyncio.run(export_benefit_details(args.benefit_id, args.is_commerce, Path(output)))
        return

    if args.command == "details-all":
        types = _resolve_types(args.benefit_type)
        output = Path(args.output)
        if output.name == "hot_details_all.json":
            output = output.with_name(f"hot_details{_output_suffix(types)}.json")
        asyncio.run(
            export_all_details(
                types=types,
                is_commerce=args.is_commerce,
                output_path=output,
                source=args.source,
                input_file=Path(args.input),
                request_delay=args.request_delay,
                worker_stagger=args.worker_stagger,
                chunk_size=args.chunk_size,
            )
        )


if __name__ == "__main__":
    main()
