#!/usr/bin/env python3
"""
MCC Code Finder (Israel-aware)
------------------------------
Given a company name (in English or Hebrew), search the web for the company's
website, fetch its homepage, and use Claude to pick the best-fitting MCCs
from the provided MCC database (mcc_codes.json).

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python mcc_finder.py "שופרסל"
    python mcc_finder.py "Wix"
    python mcc_finder.py "Tipalti" --top 3
    python mcc_finder.py "רמי לוי" --url https://www.rami-levy.co.il

Requirements:
    pip install requests beautifulsoup4 ddgs anthropic
"""

import argparse
import json
import os
import re
import sys
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
CLAUDE_MODEL = "claude-sonnet-4-5"  # swap to claude-sonnet-4-5 for cheaper/faster
MAX_PAGE_CHARS = 12_000

# Preference order for Israeli companies
IL_TLDS = (".co.il", ".org.il", ".net.il", ".ac.il", ".gov.il")

# Aggregators and directories we don't want as "the official site"
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


# -----------------------------------------------------------------------------
# MCC catalog loader
# -----------------------------------------------------------------------------
def load_mcc_catalog(path: Path) -> list[dict[str, str]]:
    """Load MCC entries. Prefer edited_description, fallback to combined/irs."""
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
def find_company_website(company: str, max_results: int = 10) -> str | None:
    """
    Search DDG (Israel region) and return the most likely official site URL.
    Israeli TLDs and domains containing the company name are boosted.
    """
    hebrew = has_hebrew(company)

    # Try a couple of query variants; Hebrew "אתר רשמי" = "official website"
    queries = []
    if hebrew:
        queries.append(f'{company} אתר רשמי')
        queries.append(f'"{company}" site:.co.il')
        queries.append(company)
    else:
        queries.append(f"{company} official website Israel")
        queries.append(f'"{company}" site:.co.il OR site:.com')
        queries.append(f"{company} official website")

    all_results: list[dict] = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                try:
                    # region="il-he" biases toward Israeli results
                    batch = list(ddgs.text(q, region="il-he", max_results=max_results))
                except TypeError:
                    # Older ddgs signature without `region`
                    batch = list(ddgs.text(q, max_results=max_results))
                all_results.extend(batch)
                if len(all_results) >= max_results * 2:
                    break
    except Exception as e:
        print(f"[!] Search failed: {e}", file=sys.stderr)
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

        # Strongly prefer Israeli TLDs
        if any(url_l.endswith(tld) or f"{tld}/" in url_l for tld in IL_TLDS):
            score += 20

        # Company name showing up in the domain is a strong signal
        domain_chars = re.sub(r"[^a-z0-9\u0590-\u05FF]", "", url_l)
        if company_token and company_token in domain_chars:
            score += 15

        # Homepage-ish URLs beat deep links
        path_depth = url_l.count("/") - 2  # subtract scheme's // and host slash
        score += max(0, 5 - path_depth)

        # Shorter URLs beat longer ones
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
    """Fetch a URL and return visible text. Handles Hebrew and charset detection."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0 Safari/537.36"
        ),
        # Prefer Hebrew then English so Israeli sites serve localized content
        "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.7,en;q=0.6",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    # requests sometimes guesses ISO-8859-1 for HTML; trust apparent_encoding when it differs
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
1. A company name (often Israeli, name may be Hebrew or English)
2. Text scraped from the company's website (may be in Hebrew, English, or mixed)
3. A JSON catalog of valid MCC codes with English descriptions

Your job: pick the MCCs from the catalog that best match the company's actual business activities, ranked by fit.

Rules:
- You understand Hebrew fluently. Translate mentally as needed and match meaning, not just wording.
- ONLY choose MCCs from the provided catalog. Never invent codes.
- Return JSON ONLY, no prose, no markdown fences.
- Each result must include: mcc, description (copied verbatim from the catalog), confidence (0-100), reasoning (one short sentence in English).
- Prefer specific codes over generic ones when the evidence supports it.
- Many Israeli companies operate in unique local categories (e.g. "קופת חולים" = HMO/health insurance, "מכולת" = convenience store, "קונדיטוריה" = bakery/pastry shop). Map these to the closest MCC in the catalog.
- If the website text is too thin to be confident, still return your best guesses but lower the confidence scores.
- Return at most the requested number of results, ordered best-first."""


def classify_with_claude(
    client: Anthropic,
    company: str,
    page_text: str,
    catalog: list[dict[str, str]],
    top: int,
) -> list[dict[str, Any]]:
    """Ask Claude to pick the best MCCs from the catalog."""
    if len(page_text) > MAX_PAGE_CHARS:
        page_text = page_text[:MAX_PAGE_CHARS] + " …[truncated]"

    catalog_json = json.dumps(catalog, ensure_ascii=False)

    user_message = f"""Company name: {company}

Website content (may be Hebrew/English/mixed):
---
{page_text}
---

MCC catalog (JSON array of objects with "mcc" and "description"):
{catalog_json}

Return the top {top} MCCs as a JSON array. Example format:
[
  {{"mcc": "5812", "description": "Eating Places, Restaurants", "confidence": 92, "reasoning": "Site advertises restaurant menus and reservations."}}
]"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=CLASSIFIER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text_out = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()

    text_out = re.sub(r"^```(?:json)?\s*|\s*```$", "", text_out, flags=re.MULTILINE).strip()

    try:
        parsed = json.loads(text_out)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude returned non-JSON output:\n{text_out}") from e

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
# CLI
# -----------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Find likely MCC codes for a company (Israel-aware).")
    parser.add_argument("company", help="Company name (English or Hebrew)")
    parser.add_argument("--top", type=int, default=5, help="Max MCCs to return (default: 5)")
    parser.add_argument("--url", help="Skip search and use this URL directly")
    parser.add_argument("--mcc-db", type=Path, default=DEFAULT_MCC_PATH,
                        help=f"Path to MCC JSON (default: {DEFAULT_MCC_PATH})")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] Set ANTHROPIC_API_KEY in your environment.", file=sys.stderr)
        return 1

    if not args.mcc_db.exists():
        print(f"[!] MCC database not found: {args.mcc_db}", file=sys.stderr)
        return 1

    catalog = load_mcc_catalog(args.mcc_db)
    if not args.json:
        print(f"[*] Loaded {len(catalog)} MCC entries from {args.mcc_db.name}")

    if args.url:
        url = args.url
    else:
        if not args.json:
            print(f"[*] Searching for: {args.company}")
        url = find_company_website(args.company)
        if not url:
            print("[!] Could not find a website for that company.", file=sys.stderr)
            return 1

    if not args.json:
        print(f"[*] Website: {url}")

    try:
        text = fetch_page_text(url)
    except Exception as e:
        print(f"[!] Failed to fetch page: {e}", file=sys.stderr)
        return 1

    if not text.strip():
        print("[!] No readable content on the page.", file=sys.stderr)
        return 1

    if not args.json:
        print(f"[*] Fetched {len(text)} chars. Asking Claude to classify...\n")

    client = Anthropic(api_key=api_key)
    try:
        results = classify_with_claude(client, args.company, text, catalog, args.top)
    except Exception as e:
        print(f"[!] Classification failed: {e}", file=sys.stderr)
        return 1

    if not results:
        print("[!] No valid MCC matches returned.", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"company": args.company, "url": url, "matches": results},
                         indent=2, ensure_ascii=False))
        return 0

    print(f"Top {len(results)} MCC candidates for '{args.company}':\n")
    print(f"{'MCC':<6} {'Conf':<5} Description")
    print("-" * 72)
    for r in results:
        print(f"{r['mcc']:<6} {r['confidence']:<5} {r['description']}")
        if r.get("reasoning"):
            print(f"       → {r['reasoning']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
