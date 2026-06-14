"""CLI entry point: find the optimal deal stack for a store + cart.

    python -m deal_optimizer.cli <deals.json> <store_id> <cart_total> [--quantity N] [--strict]
"""

from __future__ import annotations

import argparse

from .engine import get_optimal_deal_path


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
    args = p.parse_args()

    result = get_optimal_deal_path(
        file_path=args.file_path,
        target_store_id=args.store_id,
        cart_total=args.cart_total,
        cart_quantity=args.quantity,
        unknown_as_yes=not args.strict,
    )

    print(f"Store: {args.store_id}  |  Cart: {args.cart_total:.2f} ILS  |  Items: {args.quantity}")
    print(f"Starting price: {result['starting_price']:.2f}")
    print("-" * 48)
    if not result["per_step"]:
        print("No applicable deals found.")
    for i, step in enumerate(result["per_step"], 1):
        deal = result["path"][i - 1]
        title = deal.get("title") or deal.get("deal_description") or deal.get("id")
        print(f"  {i}. [{deal.get('deal_type', '?')}] {title}")
        print(f"     {step['price_in']:.2f} -> {step['price_out']:.2f}  (deal {step['deal_id']})")
    print("-" * 48)
    print(f"Final price:   {result['final_price']:.2f}")
    print(f"Total savings: {result['total_savings']:.2f}")


if __name__ == "__main__":
    main()
