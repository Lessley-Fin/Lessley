import argparse
import json
from bidi.algorithm import get_display

def calculate_discount_savings(discount, cart_total, cart_quantity):
    """Calculates the exact savings for a given discount based on cart constraints."""
    
    # if discount.get("status") != "active":
    #     return 0

    discount_logic = discount.get('discount_logic', {})
    condition = discount_logic.get('condition', {})
    cond_type = condition.get('type')
    cond_val = condition.get('value', 0)

    # 1. Validate Conditions
    if cond_type == "min_spend" and cart_total < cond_val:
        return 0
    # Checking both "exact_spend" and the clearer "voucher_value" just in case
    elif cond_type in ["exact_spend", "voucher_value"] and cart_total < cond_val:
        return 0
    elif cond_type == "min_quantity" and cart_quantity <= cond_val:
        return 0

    # 2. Calculate Savings
    reward = discount_logic.get("reward", {})
    reward_type = reward.get("type")
    reward_val = reward.get("value", 0)
    
    calculated_savings = 0
    if reward_type == "fixed_discount_amount":
        calculated_savings = reward_val

    elif reward_type == "fixed_total_amount":
        if cond_type in ["exact_spend", "voucher_value"]:
            calculated_savings = cond_val - reward_val

    elif reward_type == "percentage_off":
        if cond_type in ["exact_spend", "voucher_value"]:
            # Percentage applies ONLY to the voucher value, not the whole cart
            calculated_savings = cond_val * (reward_val / 100.0)
        else:
            # Percentage applies to the whole cart
            calculated_savings = cart_total * (reward_val / 100.0)

    # 3. Apply Constraints
    constraints = discount_logic.get("constraints", {})
    max_discount = constraints.get("max_discount_amount")
    
    if max_discount is not None:
        calculated_savings = min(calculated_savings, max_discount)

    # Ensure we don't refund the user more money than their cart total
    calculated_savings = min(calculated_savings, cart_total)

    return calculated_savings

def get_best_deals_for_store(file_path, target_store_id, cart_total, cart_quantity):
    """Reads JSON, filters by store_id, evaluates savings, and sorts best to worst."""
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            all_deals = json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find file '{file_path}'")
        return []
    except json.JSONDecodeError:
        print(f"Error: '{file_path}' contains invalid JSON")
        return []

    # 1. Filter deals by the requested store_id — either the deal's own store_id
    #    or any member in group_member_stores (e.g. gift cards covering multiple stores).
    def deal_matches_store(deal):
        if deal.get("store_id") == target_store_id:
            return True
        for member in deal.get("group_member_stores", []):
            if member == target_store_id:
                return True
        return False

    store_deals = [deal for deal in all_deals if deal_matches_store(deal)]

    if not store_deals:
        print(f"No deals found for store_id: {target_store_id}")
        return []

    # 2. Evaluate and attach savings math to each deal
    evaluated_deals = []
    for deal in store_deals:
        savings = calculate_discount_savings(deal, cart_total, cart_quantity)
        if(savings > 0):
            # Copy the original dictionary to preserve your exact JSON format
            evaluated_deal = deal.copy()
            
            # Inject private fields to track the math (useful for the API/Frontend)
            evaluated_deal["_calculated_savings"] = savings
            evaluated_deal["_final_price"] = cart_total - savings
        
            evaluated_deals.append(evaluated_deal)

    # 3. Sort from highest savings to lowest
    evaluated_deals.sort(key=lambda x: x["_calculated_savings"], reverse=True)

    return evaluated_deals


# ==========================================
# EXECUTING AND PRINTING THE RESULTS
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find best deals for a store.")
    parser.add_argument("store_id", help="The target store_id to search deals for")
    parser.add_argument("cart_total", type=float, help="Total cart value in ILS")
    args = parser.parse_args()

    #terminal x store id - 019d209bd92a_e3cb71c9a52ce477
    #fox group store id - 019d20b5f157_c35408646278afc0
    JSON_FILE_PATH = "data/deals.json"
    MY_CART_QUANTITY = 1

    print(f"--- Searching deals for Store: {args.store_id} ---")
    print(f"Cart Total: {args.cart_total} | Items: {MY_CART_QUANTITY}\n")

    sorted_deals = get_best_deals_for_store(
        file_path=JSON_FILE_PATH,
        target_store_id=args.store_id,
        cart_total=args.cart_total,
        cart_quantity=MY_CART_QUANTITY,
    )

    for index, deal in enumerate(sorted_deals):
        rank = index + 1
        description = get_display(deal.get("title") or deal.get("deal_description", "Unnamed Deal"))
        saved = deal.get("_calculated_savings", 0)
        final_price = deal.get("_final_price", args.cart_total)

        print(f"#{rank}: {description} [{deal.get('id', 'N/A')}]")
        print(f"    You Save:    {saved:.2f}")
        print(f"    Final Price: {final_price:.2f}")

        if saved == 0:
            print("    (Did not qualify for this deal or it is inactive)")
        print("-" * 40)