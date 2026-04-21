"""
Swish.co.il benefit scraper
============================
Extracts benefit names and their supported store lists from swish.co.il.

Architecture notes
------------------
- Next.js App Router (RSC), NOT Pages Router — there is no __NEXT_DATA__ tag.
- Product data is embedded in inline `self.__next_f.push([1, "..."])` scripts
  that are part of the server-rendered HTML, so no AJAX interception is needed.
- Store list lives at: tagsChains[].chainsByWallet[].storeName
- Catalog product IDs are server-rendered as <a class="category-tile-link"> links.

Anti-bot notes
--------------
- Uses launch_persistent_context + playwright-stealth for a stable, human-like session.
- Randomised delays between requests.
- On the "אוי" popup, marks the ID blocked and applies a 20-60s cooldown.
"""

import json
import random
import re
import time
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
SCAN_LIMIT = None           # Set to None to process the entire queue each run.
DATA_FILE  = "swish_database.json"
STATE_FILE = "scan_state.json"
SESSION_DIR = "./swish_session"
CATALOG_URL = "https://swish.co.il/home/all-gifts-giftcard"
PRODUCT_URL = "https://swish.co.il/home/all-gifts-giftcard/product-{pid}"
BLOCK_TEXT  = "אוי, נראה שמשהו הפסיק לעבוד"


# ---------------------------------------------------------------------------
# STATE / PERSISTENCE
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed": [], "blocked": [], "queue": []}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_results() -> list:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_results(results: list) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# PARSING HELPERS (work on raw HTML string — no __NEXT_DATA__ on this site)
# ---------------------------------------------------------------------------
def extract_product_ids(html: str) -> list[str]:
    """
    Pull product IDs from the catalog page.
    They are server-rendered as:  href="/home/all-gifts-giftcard/product-XXXXX"
    """
    hits = re.findall(r'/product-(\d+)', html)
    return list(dict.fromkeys(hits))  # deduplicate, preserve order


def extract_product_data(html: str, pid: str) -> dict | None:
    """
    Extract benefit name + store list from a product page.

    The data lives inside inline  self.__next_f.push([1, "..."])  RSC scripts.
    Quotes inside the JS string are escaped as  \"  so we unescape once before
    running regexes — no full JSON parsing required.
    """
    # Unescape JS string escaping (\" -> ")
    unescaped = html.replace('\\"', '"')

    store_names = re.findall(r'"storeName":"([^"]+)"', unescaped)
    if not store_names:
        return None

    benefit_names = re.findall(r'"whatWillUGet":"([^"]+)"', unescaped)
    benefit_name = benefit_names[0] if benefit_names else None

    # Fallback: grab from <h1> if RSC field is missing
    if not benefit_name:
        h1 = re.search(r'<h1[^>]*>\s*([^<]+)\s*</h1>', html)
        benefit_name = h1.group(1).strip() if h1 else None

    return {
        "benefit_id": pid,
        "benefit_name": benefit_name,
        "stores": list(dict.fromkeys(store_names)),  # deduplicated, ordered
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# BLOCK DETECTION
# ---------------------------------------------------------------------------
def is_blocked(page) -> bool:
    try:
        return page.locator(f"text={BLOCK_TEXT}").count() > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def run_swish_scanner() -> None:
    state = load_state()
    results = load_results()
    already_saved_ids = {r["benefit_id"] for r in results}

    stealth = Stealth()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        stealth.apply_stealth_sync(context)
        page = context.new_page()

        # ----------------------------------------------------------------
        # STEP 1: Build queue from catalog if empty
        # ----------------------------------------------------------------
        if not state["queue"] and not state["blocked"]:
            print("Fetching catalog to build the queue…")
            page.goto(CATALOG_URL, wait_until="networkidle", timeout=60_000)

            if is_blocked(page):
                print("Blocked on catalog page. Waiting before retry…")
                time.sleep(random.uniform(20, 60))
                context.close()
                return

            html = page.content()
            ids = extract_product_ids(html)
            new_ids = [pid for pid in ids if pid not in state["processed"]]
            state["queue"] = new_ids
            save_state(state)
            print(f"Queue built: {len(new_ids)} product IDs.")

        # ----------------------------------------------------------------
        # STEP 2: Decide what to scan this run
        #   - Blocked IDs are always retried first (priority list, no shuffle)
        #   - Then shuffle the remaining queue for non-linear scanning
        # ----------------------------------------------------------------
        fresh_queue = [pid for pid in state["queue"] if pid not in state["blocked"]]
        random.shuffle(fresh_queue)
        ids_to_scan = state["blocked"] + fresh_queue

        if SCAN_LIMIT is not None:
            ids_to_scan = ids_to_scan[:SCAN_LIMIT]

        print(
            f"Starting scan — {len(ids_to_scan)} IDs this run "
            f"({len(state['blocked'])} blocked retries, {len(fresh_queue)} from queue)"
        )

        # ----------------------------------------------------------------
        # STEP 3: Scrape each product page
        # ----------------------------------------------------------------
        for pid in ids_to_scan:
            # Already have data — just reconcile state
            if pid in already_saved_ids:
                state["processed"].append(pid)
                state["queue"]   = [q for q in state["queue"]   if q != pid]
                state["blocked"] = [b for b in state["blocked"] if b != pid]
                save_state(state)
                continue

            url = PRODUCT_URL.format(pid=pid)
            print(f"  ID {pid}: {url}")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(2000)

                if is_blocked(page):
                    print(f"  -> BLOCKED. Cooling down…")
                    if pid not in state["blocked"]:
                        state["blocked"].append(pid)
                    state["queue"] = [q for q in state["queue"] if q != pid]
                    save_state(state)
                    cooldown = random.uniform(20, 60)
                    print(f"  -> Waiting {cooldown:.0f}s")
                    time.sleep(cooldown)
                    continue

                html = page.content()
                record = extract_product_data(html, pid)

                if record is None:
                    print(f"  -> Store data not found in RSC payload, skipping.")
                    # Leave in queue to retry next run
                    continue

                results.append(record)
                already_saved_ids.add(pid)
                save_results(results)

                state["processed"].append(pid)
                state["queue"]   = [q for q in state["queue"]   if q != pid]
                state["blocked"] = [b for b in state["blocked"] if b != pid]
                save_state(state)

                print(f"  -> Saved: {record['benefit_name']} ({len(record['stores'])} stores)")

            except PlaywrightTimeout:
                print(f"  -> Timeout on ID {pid}, will retry next run.")
            except Exception as e:
                print(f"  -> Error on ID {pid}: {e}")

            # Human-like delay between requests
            time.sleep(random.uniform(5, 12))

        print(f"\nScan cycle complete. {len(results)} records saved to {DATA_FILE}.")
        context.close()


if __name__ == "__main__":
    run_swish_scanner()
