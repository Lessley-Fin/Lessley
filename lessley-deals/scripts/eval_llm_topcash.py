"""Compare the llm:topcash extractor against the trusted topcash adapter.

The TopCash all-stores page is server-rendered (no JS needed) and the
hand-coded adapter parses all ``div.store-container`` blocks. This harness
feeds the same page text to the LLM and reports coverage + field-format parity
so the prompt / chunk size can be tuned until the LLM output matches.

Usage:
    python scripts/eval_llm_topcash.py
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import httpx  # noqa: E402

from lessley_deals.enrichment.llm_client import ExtractedDeal, extract_deals_from_content  # noqa: E402
from lessley_deals.scraping.base import SourceConfig  # noqa: E402
from lessley_deals.scraping.engine.llm_scraper import clean_dom, split_content  # noqa: E402
from lessley_deals.scraping.registry import _coerce_max_len, load_llm_site_configs  # noqa: E402
from lessley_deals.scraping.sources.isracard_topcash import IsracardTopcashAdapter  # noqa: E402

_URL = "https://www.topcash.co.il/all-stores"
_SITE_ID = "llm:topcash"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"


def _cfg() -> dict:
    for c in load_llm_site_configs():
        if c["site_id"] == _SITE_ID:
            return c
    raise SystemExit(f"No '{_SITE_ID}' entry in data/seed/llm_sources.json")


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _fetch_html() -> str:
    r = httpx.get(_URL, headers={"User-Agent": _UA}, follow_redirects=True, timeout=30)
    r.raise_for_status()
    return r.text


async def _ground_truth() -> list[tuple[str, str]]:
    # fetch_details=False keeps it fast; we only compare store_name + cashback.
    _stores, deals = await IsracardTopcashAdapter(
        SourceConfig(base_url=_URL), fetch_details=False
    ).scrape()
    return [(d.store_name, d.price_text) for d in deals]


def _llm_candidate(html: str, instructions: str, max_len: int) -> list[ExtractedDeal]:
    cleaned = clean_dom(html)
    chunks = split_content(cleaned, max_len=max_len)
    out: list[ExtractedDeal] = []
    for i, c in enumerate(chunks, start=1):
        try:
            out.extend(extract_deals_from_content(c, instructions).deals)
        except Exception as exc:  # noqa: BLE001
            print(f"  [chunk {i}/{len(chunks)}] LLM error: {exc}", file=sys.stderr)
    return out


async def main() -> None:
    cfg = _cfg()
    max_len = _coerce_max_len(cfg.get("max_len"))
    print(f"max_len={max_len}\nPrompt:\n  {cfg['instructions']}\n")

    html = _fetch_html()
    gt = await _ground_truth()
    llm = _llm_candidate(html, cfg["instructions"], max_len)

    gt_names = {_norm(n) for n, _ in gt}
    llm_names = {_norm(d.store_name) for d in llm}
    matched = gt_names & llm_names

    print("=" * 60)
    print(f"Ground truth (adapter): {len(gt)} deals, {len(gt_names)} stores")
    print(f"LLM candidate:          {len(llm)} deals, {len(llm_names)} stores")
    recall = len(matched) / len(gt_names) if gt_names else 0.0
    print(f"Store-name recall (exact 'Eng | Heb'): {len(matched)}/{len(gt_names)} = {recall:.0%}")
    print("-" * 60)
    print("Sample GT  price_text:", [p for _, p in gt[:6]])
    print("Sample LLM price_text:", [d.price_text for d in llm[:6]])
    print("MISSED (first 20):", sorted(gt_names - llm_names)[:20])
    print("EXTRA  (first 20):", sorted(llm_names - gt_names)[:20])


if __name__ == "__main__":
    asyncio.run(main())
