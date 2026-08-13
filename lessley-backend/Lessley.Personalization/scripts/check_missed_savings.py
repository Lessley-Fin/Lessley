"""
Measure missed-savings matching against real transaction feeds.

Unit tests pin the rules; this pins the *outcome* on real data, which is the thing that
actually regresses when a threshold moves. It runs the production matcher — nothing is
reimplemented here — over the reference JSON dumps and a card-feed export.

    python scripts/check_missed_savings.py \
        --resources ../../main/resources \
        --transactions ../../transaction-365.json

Add --details to list every match, --band SIMILAR to list one band.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from services.utils.store_identity import build_identities          # noqa: E402
from services.utils.store_similarity import DealShopFinder, SURFACEABLE  # noqa: E402

# What a healthy run looks like, measured when the name matcher replaced MCC categories.
# A drop means something regressed; a rise wants eyeballing before it is written in.
#
# These count only what a user would actually be shown — EXACT, STRONG and SIMILAR. WEAK
# matches are found and banded but never surfaced, so counting them would flatter the figure
# by exactly the matches we decided not to trust.
BASELINES = {
    "transaction-365.json": {"merchants": 46, "spend_share": 0.28},
    "transactions.json": {"merchants": 11, "spend_share": 0.35},
}


def read(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def as_store(row: dict):
    mongo_id = row.get("_id")
    if isinstance(mongo_id, dict):
        mongo_id = mongo_id.get("$oid")
    metadata = row.get("metadata") or {}
    return SimpleNamespace(
        store_id=row.get("id") or (str(mongo_id) if mongo_id else ""),
        name=row.get("name") or "",
        metadata=SimpleNamespace(
            mcc_codes=[str(code) for code in (metadata.get("mcc_codes") or []) if code is not None],
            official_name=metadata.get("official_name"),
        ),
    )


def read_transactions(path: Path):
    """A bare array, or the `{status, count, data}` envelope an API export comes wrapped in."""
    document = read(path)
    if isinstance(document, dict):
        document = document.get("data") or []
    return [row for row in document if isinstance(row, dict)]


def spend_of(transactions):
    total = 0.0
    for transaction in transactions:
        amount = (transaction.get("amount") or {}).get("chargedAmount") or {}
        total += abs(float(amount.get("amount") or 0.0))
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resources", default="../../main/resources")
    parser.add_argument("--transactions", action="append", required=True)
    parser.add_argument("--details", action="store_true")
    parser.add_argument("--by-store", action="store_true", help="group by shop, as the endpoint does")
    parser.add_argument("--band")
    args = parser.parse_args()

    resources = Path(args.resources)
    stores = [as_store(row) for row in read(resources / "stores.json") if (row.get("name") or "").strip()]
    aliases = [
        SimpleNamespace(store_id=row.get("store_id"), alias=row.get("alias") or "")
        for row in read(resources / "store_aliases.json")
    ]
    deals_by_store = defaultdict(list)
    for row in read(resources / "deals.json"):
        if row.get("store_id"):
            deals_by_store[row["store_id"]].append(
                SimpleNamespace(deal_id=row.get("id"), store_id=row["store_id"], title=row.get("title"))
            )

    identities = build_identities(stores, aliases, deals_by_store)
    finder = DealShopFinder(list(identities.values()))
    print(f"catalogue: {len(stores)} stores -> {len(identities)} brands, {len(finder)} running a deal\n")

    failures = 0
    for name in args.transactions:
        path = Path(name)
        transactions = read_transactions(path)

        purchases = defaultdict(list)
        for transaction in transactions:
            address = transaction.get("merchantAddress") or {}
            purchases[
                ((transaction.get("merchantName") or "").strip(), address.get("townName") or None)
            ].append(transaction)

        bands = Counter()
        reached = 0.0
        matched = 0
        rows = []
        for (merchant, town), group in purchases.items():
            category = (group[0].get("category") or {}).get("sub") or ""
            found = [m for m in finder.find(merchant, town, category) if m.band in SURFACEABLE]
            if not found:
                continue
            matched += 1
            reached += spend_of(group)
            bands[found[0].band] += 1
            rows.append((merchant, town, len(group), spend_of(group), found[0]))

        total = spend_of(transactions) or 1.0
        share = reached / total
        baseline = BASELINES.get(path.name)

        print(f"── {path.name}")
        print(f"   merchants matched : {matched} / {len(purchases)}")
        print(f"   spend reached     : {reached:,.0f} of {total:,.0f}  ({share:.0%})")
        print(f"   bands             : " + ", ".join(f"{b} {n}" for b, n in bands.most_common()))

        if baseline:
            ok = matched >= baseline["merchants"] and share >= baseline["spend_share"] - 0.01
            print(f"   baseline          : {baseline['merchants']} merchants / "
                  f"{baseline['spend_share']:.0%} spend  -> {'OK' if ok else 'REGRESSED'}")
            failures += 0 if ok else 1

        if args.details or args.band:
            print()
            for merchant, town, count, amount, match in sorted(rows, key=lambda r: -r[3]):
                if args.band and match.band != args.band:
                    continue
                print(f"   [{match.band:7}] {merchant} ({town or '-'}) x{count} {amount:,.0f}"
                      f"  ->  {match.identity.name}  ({len(match.deals)} deals)"
                      f"  shared={' '.join(match.shared_tokens)}")

        if args.by_store:
            print("\n   ── gathered by shop, the way the endpoint returns it ──")
            shops = {}
            for merchant, town, count, amount, match in rows:
                shop = shops.setdefault(
                    match.identity.store_id,
                    {"match": match, "spend": 0.0, "purchases": [], "count": 0},
                )
                shop["spend"] += amount
                shop["count"] += count
                shop["purchases"].append(merchant)
            for shop in sorted(shops.values(), key=lambda s: -s["spend"]):
                match = shop["match"]
                verdict = "you shopped here" if match.is_confident else "somewhere similar"
                print(f"\n   {match.identity.name}  ·  {len(match.deals)} deals  ·  {verdict}")
                print(f"      covers {shop['count']} purchases · {shop['spend']:,.0f}")
                for merchant in sorted(set(shop["purchases"]))[:4]:
                    print(f"        {merchant}")
        print()

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
