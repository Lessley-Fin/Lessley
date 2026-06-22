#!/usr/bin/env python3
"""
MCC Batch Enricher (Israel-aware)
---------------------------------
Read a stores.json file, determine MCC codes for each store, and write them
back into metadata.mcc_codes. Skips stores that already have MCC codes by
default.

Input format (list of stores):
[
  {
    "id": "...",
    "name": "lee cooper",
    "metadata": {
      "store_url": "https://www.leecooper.co.il/",
      "mcc_codes": [5651, 5732, 5699]   // may be missing or empty
    }
  },
  ...
]

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python mcc_batch.py stores.json
    python mcc_batch.py stores.json --out stores_enriched.json
    python mcc_batch.py stores.json --top 3 --force
    python mcc_batch.py stores.json --limit 10          # only first 10 stores

Requirements:
    pip install requests beautifulsoup4 ddgs anthropic
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        print("Install search dependency: pip install ddgs", file=sys.stderr)
        sys.exit(1)

try:
    from anthropic import Anthropic
except ImportError:
    print("Install Anthropic SDK: pip install anthropic", file=sys.stderr)
    sys.exit(1)


DEFAULT_MCC_PATH = Path(__file__).with_name("mcc_codes.json")
CLAUDE_MODEL = "claude-haiku-4-5"  # faster/cheaper for batch runs
MAX_PAGE_CHARS = 10_000

IL_TLDS = (".co.il", ".org.il", ".net.il", ".ac.il", ".gov.il")

BLOCKLIST = (
    "wikipedia.org", "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "youtube.com", "crunchbase.com", "bloomberg.com",
    "glassdoor.com", "indeed.com", "yelp.com", "reddit.com",
    "dun.co.il", "d-b.co.il", "bizportal.co.il", "themarker.com",
    "calcalist.co.il", "globes.co.il", "ynet.co.il", "mako.co.il",
    "zap.co.il", "easy.co.il", "rest.co.il", "pepper.co.il",
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def has_hebrew(s: str) -> bool:
    return bool(re.search(r"[\u0590-\u05FF]", s))


def load_mcc_catalog(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    catalog: list[dict[str, str]] = []
    for entry in raw:
        mcc = str(entry.get("mcc", "")).strip()
        desc = (
            entry.get("edited_description")
            or entry.get("combined_description")
            or entry.get("irs_description")
            or entry.get("usda_description")
            or ""
        ).strip()
        if mcc and desc:
            catalog.append({"mcc": mcc, "description": desc})
    return catalog


# -----------------------------------------------------------------------------
# Web search + fetch
# -----------------------------------------------------------------------------
def find_company_website(company: str, max_results: int = 8) -> str | None:
    hebrew = has_hebrew(company)
    queries = []
    if hebrew:
        queries.append(f"{company} אתר רשמי")
        queries.append(f'"{company}" site:.co.il')
    else:
        queries.append(f"{company} official website Israel")
        queries.append(f'"{company}" site:.co.il')
        queries.append(f"{company} official website")

    all_results: list[dict] = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    batch = list(ddgs.text(q, region="il-he", max_results=max_results))
                except TypeError:
                    batch = list(ddgs.text(q, max_results=max_results))
                all_results.extend(batch)
                if len(all_results) >= max_results * 2:
                    break
    except Exception as e:
        print(f"    [!] Search failed: {e}", file=sys.stderr)
        return None

    if not all_results:
        return None

    company_token = re.sub(r"[^a-z0-9\u0590-\u05FF]", "", company.lower())
    seen: set[str] = set()
    scored: list[tuple[int, str]] = []
    for r in all_results:
        url = r.get("href") or r.get("url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        if any(b in url for b in BLOCKLIST):
            continue

        url_l = url.lower()
        score = 0
        if any(url_l.endswith(tld) or f"{tld}/" in url_l for tld in IL_TLDS):
            score += 20
        domain_chars = re.sub(r"[^a-z0-9\u0590-\u05FF]", "", url_l)
        if company_token and company_token in domain_chars:
            score += 15
        path_depth = max(0, url_l.count("/") - 2)
        score += max(0, 5 - path_depth)
        score += max(0, 100 - len(url)) // 20
        scored.append((score, url))

    if not scored:
        for r in all_results:
            url = r.get("href") or r.get("url") or ""
            if url and not any(b in url for b in BLOCKLIST):
                return url
        return None

    scored.sort(reverse=True)
    return scored[0][1]


def fetch_page_text(url: str, timeout: int = 15) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        ),
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.7,en;q=0.6",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    if resp.encoding and resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    meta_desc = ""
    md_tag = soup.find("meta", attrs={"name": "description"}) or \
             soup.find("meta", attrs={"property": "og:description"})
    if md_tag and md_tag.get("content"):
        meta_desc = md_tag["content"].strip()

    og_site = ""
    og_tag = soup.find("meta", attrs={"property": "og:site_name"})
    if og_tag and og_tag.get("content"):
        og_site = og_tag["content"].strip()

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    body_text = soup.get_text(separator=" ", strip=True)
    body_text = re.sub(r"\s+", " ", body_text)

    parts: list[str] = []
    if title:
        parts.append(f"TITLE: {title}")
    if og_site:
        parts.append(f"SITE NAME: {og_site}")
    if meta_desc:
        parts.append(f"META DESCRIPTION: {meta_desc}")
    parts.append(f"BODY: {body_text}")
    return "\n\n".join(parts)


# -----------------------------------------------------------------------------
# Claude classification
# -----------------------------------------------------------------------------
CLASSIFIER_SYSTEM_PROMPT = """You are an expert in merchant categorization and the ISO 18245 MCC (Merchant Category Code) standard.

You will be given:
1. A company name (often Israeli, in Hebrew or English)
2. Text scraped from the company's website (Hebrew, English, or mixed)
3. A JSON catalog of valid MCC codes with English descriptions

Your job: pick the MCCs from the catalog that best match the company's actual business activities, ranked by fit.

Rules:
- You understand Hebrew fluently. Match meaning, not just words.
- ONLY choose MCCs from the provided catalog. Never invent codes.
- Return JSON ONLY, no prose, no markdown fences.
- Each result must include: mcc, description (copied verbatim from the catalog), confidence (0-100), reasoning (one short sentence in English).
- Prefer specific codes over generic ones when the evidence supports it.
- Many Israeli companies operate in unique local categories (e.g. "קופת חולים" = HMO, "מכולת" = convenience store, "קונדיטוריה" = bakery). Map these to the closest MCC.
- If evidence is thin, still return best guesses with lower confidence.
- Return at most the requested number of results, ordered best-first."""


def classify_with_claude(
    client: Anthropic,
    company: str,
    page_text: str,
    catalog: list[dict[str, str]],
    top: int,
) -> list[dict[str, Any]]:
    if len(page_text) > MAX_PAGE_CHARS:
        page_text = page_text[:MAX_PAGE_CHARS] + " …[truncated]"

    catalog_json = json.dumps(catalog, ensure_ascii=False)

    volatile_text = f"""Company name: {company}

Website content (may be Hebrew/English/mixed):
---
{page_text}
---

Return the top {top} MCCs as a JSON array. Example format:
[
  {{"mcc": "5812", "description": "Eating Places, Restaurants", "confidence": 92, "reasoning": "Site advertises restaurant menus and reservations."}}
]"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=[{
            "type": "text",
            "text": CLASSIFIER_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": [
            {
                "type": "text",
                "text": f"MCC catalog (JSON array of objects with \"mcc\" and \"description\"):\n{catalog_json}",
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": volatile_text,
            },
        ]}],
    )

    usage = response.usage
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    if cache_write:
        print(f"    [cache] MISS — wrote {cache_write} tokens to cache", file=sys.stderr)
    elif cache_read:
        print(f"    [cache] HIT  — saved {cache_read} cached tokens", file=sys.stderr)

    text_out = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()
    text_out = re.sub(r"^```(?:json)?\s*|\s*```$", "", text_out, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(text_out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude returned non-JSON:\n{text_out}") from e

    if not isinstance(parsed, list):
        raise RuntimeError(f"Expected a JSON array, got: {type(parsed).__name__}")

    valid_codes = {item["mcc"] for item in catalog}
    cleaned: list[dict[str, Any]] = []
    for item in parsed:
        mcc = str(item.get("mcc", "")).strip()
        if mcc in valid_codes:
            cleaned.append({
                "mcc": mcc,
                "description": item.get("description", ""),
                "confidence": item.get("confidence", 0),
                "reasoning": item.get("reasoning", ""),
            })
    return cleaned


# -----------------------------------------------------------------------------
# Per-store processing
# -----------------------------------------------------------------------------
def enrich_store(
    store: dict[str, Any],
    client: Anthropic,
    catalog: list[dict[str, str]],
    top: int,
    force: bool,
) -> tuple[str, list[int]]:
    """
    Enrich a single store. Returns (status, mcc_codes).
    status ∈ {"skipped", "ok", "no_url", "fetch_failed", "classify_failed"}
    """
    name = store.get("name", "").strip()
    metadata = store.setdefault("metadata", {})
    existing = metadata.get("mcc_codes") or []

    if existing and not force:
        return ("skipped", existing)

    # Prefer store_url if present, otherwise search
    url = (metadata.get("store_url") or "").strip()
    if not url:
        url = find_company_website(name) or ""
    if not url:
        return ("no_url", [])

    try:
        page_text = fetch_page_text(url)
    except Exception as e:
        print(f"    [!] Fetch failed for {url}: {e}", file=sys.stderr)
        return ("fetch_failed", [])

    if not page_text.strip():
        return ("fetch_failed", [])

    try:
        results = classify_with_claude(client, name, page_text, catalog, top)
    except Exception as e:
        print(f"    [!] Classify failed: {e}", file=sys.stderr)
        return ("classify_failed", [])

    mcc_codes = [int(r["mcc"]) for r in results if r["mcc"].isdigit()]
    metadata["mcc_codes"] = mcc_codes
    # Store the url we used (so you can audit later)
    if not metadata.get("store_url"):
        metadata["store_url"] = url
    return ("ok", mcc_codes)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Batch-enrich stores.json with MCC codes.")
    parser.add_argument("stores", type=Path, help="Path to stores.json")
    parser.add_argument("--out", type=Path, help="Output path (default: overwrite input)")
    parser.add_argument("--top", type=int, default=3, help="Max MCCs per store (default: 3)")
    parser.add_argument("--force", action="store_true", help="Re-classify even if mcc_codes already set")
    parser.add_argument("--limit", type=int, help="Only process the first N stores")
    parser.add_argument("--mcc-db", type=Path, default=DEFAULT_MCC_PATH,
                        help=f"Path to MCC catalog JSON (default: {DEFAULT_MCC_PATH})")
    parser.add_argument("--sleep", type=float, default=0.5,
                        help="Seconds to sleep between stores (default: 0.5)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] Set ANTHROPIC_API_KEY in your environment.", file=sys.stderr)
        return 1
    if not args.stores.exists():
        print(f"[!] Stores file not found: {args.stores}", file=sys.stderr)
        return 1
    if not args.mcc_db.exists():
        print(f"[!] MCC database not found: {args.mcc_db}", file=sys.stderr)
        return 1

    catalog = load_mcc_catalog(args.mcc_db)
    print(f"[*] Loaded {len(catalog)} MCC entries")

    with args.stores.open("r", encoding="utf-8") as f:
        stores = json.load(f)

    if not isinstance(stores, list):
        print("[!] stores.json must be a JSON array", file=sys.stderr)
        return 1

    work = stores[: args.limit] if args.limit else stores
    total = len(work)
    print(f"[*] Processing {total} stores (force={args.force}, top={args.top})\n")

    client = Anthropic(api_key=api_key)
    out_path = args.out or args.stores

    counts = {"ok": 0, "skipped": 0, "no_url": 0, "fetch_failed": 0, "classify_failed": 0}

    try:
        for i, store in enumerate(work, 1):
            name = store.get("name", "<unnamed>")
            print(f"[{i}/{total}] {name}")
            try:
                status, codes = enrich_store(store, client, catalog, args.top, args.force)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"    [!] Unexpected error: {e}", file=sys.stderr)
                status, codes = ("classify_failed", [])

            counts[status] += 1
            if status == "ok":
                print(f"    ✓ mcc_codes: {codes}")
            elif status == "skipped":
                print(f"    ↷ skipped (already has {codes})")
            else:
                print(f"    ✗ {status}")

            # Save progress every 10 stores so a crash doesn't lose everything
            if i % 10 == 0:
                with out_path.open("w", encoding="utf-8") as f:
                    json.dump(stores, f, ensure_ascii=False, indent=2)

            time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("\n[!] Interrupted — saving progress so far...")

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)

    print(f"\n[*] Done. Wrote {out_path}")
    print(f"    ok: {counts['ok']}  skipped: {counts['skipped']}  "
          f"no_url: {counts['no_url']}  fetch_failed: {counts['fetch_failed']}  "
          f"classify_failed: {counts['classify_failed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
