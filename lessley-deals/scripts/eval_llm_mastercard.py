"""Evaluate the LLM extraction prompt against the trusted Mastercard adapter.

Feeds the *same* HTML to both extractors so the comparison isolates PROMPT
quality from fetching: the Mastercard page is Akamai-protected and blocks
headless Selenium, but curl_cffi (used by the hand-coded adapter) gets through.
So we fetch once with curl_cffi and run:

  ground truth  -> MastercardAdapter (structured selectors)   [34 deals]
  candidate     -> clean_dom -> split -> extract_deals_from_content (LLM)

Edit the ``llm:mastercard-day`` entry's ``instructions`` in
``data/seed/llm_sources.json`` and re-run to see the prompt improve.

Usage:
    python scripts/eval_llm_mastercard.py
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()  # load COLLEGE_*/OPENAI keys from .env, same as the CLI

from curl_cffi import requests as curl_requests  # noqa: E402

from lessley_deals.enrichment.llm_client import ExtractedDeal, extract_deals_from_content
from lessley_deals.scraping.base import SourceConfig
from lessley_deals.scraping.engine.llm_scraper import clean_dom, split_content
from lessley_deals.scraping.registry import load_llm_site_configs
from lessley_deals.scraping.sources.mastercard import MastercardAdapter

_MC_URL = (
    "https://www.mastercard.com/il/he/personal/find-a-card/card-benefits/mastercard-day.html"
)
_SITE_ID = "llm:mastercard-day"


def _norm(name: str | None) -> str:
    return (name or "").strip().lower()


def _instructions() -> str:
    for cfg in load_llm_site_configs():
        if cfg["site_id"] == _SITE_ID:
            return cfg["instructions"]
    raise SystemExit(f"No '{_SITE_ID}' entry in data/seed/llm_sources.json")


def _fetch_html() -> str:
    resp = curl_requests.get(
        _MC_URL,
        headers={"Accept-Language": "he-IL,he;q=0.9", "Accept": "text/html,*/*;q=0.8"},
        impersonate="chrome120",
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


async def _ground_truth() -> list[tuple[str, str]]:
    """(store_name, deal_description) from the trusted adapter."""
    _stores, deals = await MastercardAdapter(SourceConfig(base_url=_MC_URL)).scrape()
    return [(d.store_name or "", d.deal_description) for d in deals]


async def _llm_candidate(html: str, instructions: str) -> list[ExtractedDeal]:
    cleaned = clean_dom(html)
    chunks = split_content(cleaned, max_len=6000)
    out: list[ExtractedDeal] = []
    for i, chunk in enumerate(chunks, start=1):
        try:
            res = await asyncio.to_thread(extract_deals_from_content, chunk, instructions)
        except Exception as exc:  # noqa: BLE001
            print(f"  [chunk {i}/{len(chunks)}] LLM error: {exc}", file=sys.stderr)
            continue
        out.extend(res.deals)
    return out


async def main() -> None:
    instructions = _instructions()
    print(f"Prompt under test:\n  {instructions}\n")

    html = _fetch_html()
    print(f"Fetched {len(html):,} chars; cleaned {len(clean_dom(html)):,} chars\n")

    gt = await _ground_truth()
    llm = await _llm_candidate(html, instructions)

    gt_names = {_norm(n) for n, _ in gt if _norm(n)}
    llm_names = {_norm(d.store_name) for d in llm if _norm(d.store_name)}

    matched = gt_names & llm_names
    missed = gt_names - llm_names
    extra = llm_names - gt_names

    print("=" * 60)
    print(f"Ground truth (adapter): {len(gt)} deals, {len(gt_names)} named stores")
    print(f"LLM candidate:          {len(llm)} deals, {len(llm_names)} named stores")
    print("-" * 60)
    recall = len(matched) / len(gt_names) if gt_names else 0.0
    precision = len(matched) / len(llm_names) if llm_names else 0.0
    print(f"Store-name recall:    {len(matched)}/{len(gt_names)} = {recall:.0%}")
    print(f"Store-name precision: {len(matched)}/{len(llm_names)} = {precision:.0%}")
    print("-" * 60)
    print(f"MISSED by LLM ({len(missed)}): {sorted(missed)}")
    print(f"EXTRA from LLM ({len(extra)}): {sorted(extra)}")
    print("=" * 60)
    print("\nLLM deals (full):")
    for d in llm:
        print(f"  - {d.store_name!r} | {d.deal_description[:70]!r} | {d.price_text!r}")


if __name__ == "__main__":
    asyncio.run(main())
