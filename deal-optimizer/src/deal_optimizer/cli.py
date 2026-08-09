"""CLI entry point: find the optimal deal stack for a store + cart.

    python -m deal_optimizer.cli <deals.json> <store_id> <cart_total> [--quantity N] [--strict]
        [--verbose] [--top-n N] [--max-deals N] [--wallet-id user_x --wallet-file mock_wallets.json]
        [--sources hot,mastercard] [--store-types online,physical]
        [--monthly-uses deal_id:2,other_deal:1] [--output result.json]

    A wallet (--wallet-id/--wallet-file) provides a baseline user context loaded
    from a mock wallets JSON file; --sources/--store-types/--monthly-uses layer
    extra ad-hoc data on top without needing to edit the file.

    --output/-o writes the same ranked results returned by optimize()/
    get_optimal_deal_path() to a JSON file (wrapped with the query info), for
    an application to load and display, in addition to the normal console output.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import DEFAULT_MAX_DEALS, UserContext, build_export_payload, get_optimal_deal_path
from .wallet import load_wallets, wallet_to_user_context


def _build_user_context(args: argparse.Namespace) -> UserContext | None:
    wallet_ctx: UserContext | None = None
    if args.wallet_id:
        if not args.wallet_file:
            raise SystemExit("--wallet-id requires --wallet-file")
        wallets = load_wallets(args.wallet_file)
        wallet = wallets.get(args.wallet_id)
        if wallet is None:
            raise SystemExit(f"No wallet with user_id={args.wallet_id!r} in {args.wallet_file}")
        wallet_ctx = wallet_to_user_context(wallet)

    if not (args.sources or args.store_types or args.monthly_uses or wallet_ctx):
        return None

    uses_this_month = dict(wallet_ctx.uses_this_month) if wallet_ctx else {}
    if args.monthly_uses:
        for pair in args.monthly_uses.split(","):
            deal_id, _, count = pair.partition(":")
            uses_this_month[deal_id.strip()] = int(count.strip() or 0)

    sources = list(wallet_ctx.member_source_ids) if wallet_ctx else []
    if args.sources:
        sources += [s.strip() for s in args.sources.split(",")]

    store_types = list(wallet_ctx.preferred_store_types) if wallet_ctx else []
    if args.store_types:
        store_types += [c.strip() for c in args.store_types.split(",")]

    return UserContext(
        member_source_ids=sources, preferred_store_types=store_types, uses_this_month=uses_this_month
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Find the cheapest legal stack of deals for a cart.")
    p.add_argument("file_path", help="Path to the deals JSON file (list of deal objects)")
    p.add_argument("store_id", help="Target store_id")
    p.add_argument("cart_total", type=float, help="Total cart value in ILS")
    p.add_argument("--quantity", type=int, default=1, help="Cart item quantity (default 1)")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Treat combinability 'unknown' as 'no' (default: optimistic 'yes')",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print the eligibility prune, vertex list, DP-sweep decisions, and exclusion reasons",
    )
    p.add_argument("--wallet-id", help="user_id to load from --wallet-file as a baseline user context")
    p.add_argument("--wallet-file", help="Path to a mock wallets JSON file (required if --wallet-id is passed)")
    p.add_argument(
        "--sources", help="Comma-separated source_ids the user has access to (loyalty program/card issuer), e.g. hot,mastercard"
    )
    p.add_argument(
        "--store-types", help="Comma-separated preferred store types, e.g. outlets,online,physical"
    )
    p.add_argument(
        "--monthly-uses", help="Comma-separated deal_id:count already used this month, e.g. D11_coupon_capped:1"
    )
    p.add_argument("--top-n", type=int, default=5, help="Number of ranked options to show (default 5)")
    p.add_argument(
        "--max-deals",
        type=int,
        default=DEFAULT_MAX_DEALS,
        help=(
            f"Longest combination to search for — the most deals one option may stack "
            f"(default {DEFAULT_MAX_DEALS}; 0 = no limit)"
        ),
    )
    p.add_argument(
        "--output", "-o", help="Write the ranked results to this JSON file, for an application to load and display"
    )
    args = p.parse_args()

    results = get_optimal_deal_path(
        file_path=args.file_path,
        target_store_id=args.store_id,
        cart_total=args.cart_total,
        cart_quantity=args.quantity,
        user_context=_build_user_context(args),
        unknown_as_yes=not args.strict,
        top_n=args.top_n,
        # 0 is the CLI's way of spelling "no limit" (argparse has no natural None).
        max_deals=args.max_deals or None,
        verbose=args.verbose,
    )

    if args.output:
        payload = build_export_payload(
            results,
            store_id=args.store_id,
            cart_total=args.cart_total,
            cart_quantity=args.quantity,
            wallet_id=args.wallet_id,
        )
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(results)} ranked result(s) to {out_path}")

    print(
        f"\nStore: {args.store_id}  |  Cart: {args.cart_total:.2f} ILS  |  Items: {args.quantity}"
        f"  |  Max deals per option: {args.max_deals or 'unlimited'}"
    )
    print(f"Starting price: {args.cart_total:.2f}")
    if not results or not results[0]["per_step"]:
        print("No applicable deals found.")
        return

    print(f"Top {len(results)} option(s) (cheapest first):")
    for result in results:
        print("=" * 60)
        print(f"#{result['rank']} — Final price: {result['final_price']:.2f}  (saved {result['total_savings']:.2f})")
        print("-" * 60)
        for i, step in enumerate(result["per_step"], 1):
            deal = result["path"][i - 1]
            title = deal.get("title") or deal.get("deal_description") or deal.get("id")
            print(f"  {i}. [{deal.get('deal_type', '?')}] {title}")
            if step["ils_covered"] is not None:
                print(
                    f"     covers {step['ils_covered']:.2f} ILS of the bill at {step['discount_rate']:.0%} off "
                    f"-> pay {step['amount_paid_on_covered']:.2f} on it (saved {step['savings']:.2f})"
                )
                for segment in step["segments"] or []:
                    print(
                        f"       tier {segment['tier_index'] + 1}: {segment['ils_covered']:.2f} ILS "
                        f"at {segment['rate']:.0%} (saved {segment['savings']:.2f})"
                    )
                if step["remaining_to_allocate"]:
                    print(f"     {step['remaining_to_allocate']:.2f} ILS still unallocated after this step")
            else:
                print(f"     {step['discount_rate']:.0%} off the whole running bill (saved {step['savings']:.2f})")
            print(f"     bill: {step['bill_before']:.2f} -> {step['bill_after']:.2f}  (deal {step['deal_id']})")


if __name__ == "__main__":
    main()
