"""CLI entry point: find the optimal deal stack for a store + cart.

    python -m deal_optimizer.cli <deals.json> <store_id> <cart_total> [--quantity N] [--strict]
        [--verbose] [--top-n N] [--wallet-id user_x --wallet-file mock_wallets.json]
        [--member-clubs club_a,club_b] [--store-types online,physical]
        [--monthly-uses deal_id:2,other_deal:1]

    A wallet (--wallet-id/--wallet-file) provides a baseline user context loaded
    from a mock wallets JSON file; --member-clubs/--store-types/--monthly-uses layer
    extra ad-hoc data on top without needing to edit the file.
"""

from __future__ import annotations

import argparse

from .engine import UserContext, get_optimal_deal_path
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

    if not (args.member_clubs or args.store_types or args.monthly_uses or wallet_ctx):
        return None

    uses_this_month = dict(wallet_ctx.uses_this_month) if wallet_ctx else {}
    if args.monthly_uses:
        for pair in args.monthly_uses.split(","):
            deal_id, _, count = pair.partition(":")
            uses_this_month[deal_id.strip()] = int(count.strip() or 0)

    member_clubs = list(wallet_ctx.member_club_ids) if wallet_ctx else []
    if args.member_clubs:
        member_clubs += [c.strip() for c in args.member_clubs.split(",")]

    store_types = list(wallet_ctx.preferred_store_types) if wallet_ctx else []
    if args.store_types:
        store_types += [c.strip() for c in args.store_types.split(",")]

    return UserContext(
        member_club_ids=member_clubs, preferred_store_types=store_types, uses_this_month=uses_this_month
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
    p.add_argument("--member-clubs", help="Comma-separated club_ids the user belongs to, e.g. club_a,club_b")
    p.add_argument(
        "--store-types", help="Comma-separated preferred store types, e.g. outlets,online,physical"
    )
    p.add_argument(
        "--monthly-uses", help="Comma-separated deal_id:count already used this month, e.g. D11_coupon_capped:1"
    )
    p.add_argument("--top-n", type=int, default=5, help="Number of ranked options to show (default 5)")
    args = p.parse_args()

    results = get_optimal_deal_path(
        file_path=args.file_path,
        target_store_id=args.store_id,
        cart_total=args.cart_total,
        cart_quantity=args.quantity,
        user_context=_build_user_context(args),
        unknown_as_yes=not args.strict,
        top_n=args.top_n,
        verbose=args.verbose,
    )

    print(f"\nStore: {args.store_id}  |  Cart: {args.cart_total:.2f} ILS  |  Items: {args.quantity}")
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
                print(f"     pays for {step['ils_covered']:.2f} ILS of the bill via this instrument")
            print(f"     {step['price_in']:.2f} -> {step['price_out']:.2f}  (deal {step['deal_id']})")


if __name__ == "__main__":
    main()
