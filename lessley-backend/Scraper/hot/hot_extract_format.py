import json
import re
from datetime import datetime, timezone

def deduce_discount_mechanics(main, info_text):
    """
    Analyzes the text and pricing to map the promotion into one of the 6 recognized schemas:
    bogo, tiered_amount_off, fixed_price_bundle, percentage_off, statement_credit_cashback, bonus_value_wallet_credit
    """
    title = str(main.get("title", "") or "")
    desc = str(main.get("description", "") or "")
    free_text = str(main.get("free_text", "") or "")
    cashback_desc = str(main.get("cashback_description", "") or "")
    
    # Combine text fields for easier regex searching
    combined_text = f"{title} {desc} {free_text} {info_text} {cashback_desc}".lower()

    price_before = float(main.get("price_before_discount") or 0)
    price_after = float(main.get("price_after_discount") or 0)

    discount_types = []
    condition = {"type": "min_quantity", "value": 1}
    reward = {}

    # 1. Statement Credit / Cashback
    if "בחיוב" in combined_text or "cashback" in combined_text:
        discount_types.append("statement_credit_cashback")
        # Attempt to extract exact percentage from text like "5% הנחה בחיוב"
        match = re.search(r'(\d+)%', cashback_desc)
        val = float(match.group(1))/100 if match else 0.0
        reward = {"type": "percentage_cashback", "value": val}

    # 2. Buy One Get One (BOGO)
    elif "1+1" in combined_text or "1 + 1" in combined_text:
        discount_types.append("bogo")
        condition = {"type": "min_quantity", "value": 2}
        reward = {"type": "item_off", "value": 1}

    # 3. Tiered Amount Off
    elif re.search(r'קנה ב-?\s*(\d+).*שלם.*(\d+)', combined_text) or re.search(r'שווי.*(\d+).*ב-?\s*(\d+)', combined_text):
        discount_types.append("tiered_amount_off")
        match = re.search(r'שווי.*?(\d+).*ב-?\s*(\d+)', combined_text)
        if match:
            condition = {"type": "min_spend", "value": float(match.group(1))}
            reward = {"type": "fixed_price", "value": float(match.group(2))}
        else:
            reward = {"type": "amount_off", "value": price_before - price_after}

    # 4. Fixed Price / Bundle Discounts
    elif re.search(r'(\d+)\s*(ב-|תמורת)\s*(\d+)', combined_text) or "מארז" in combined_text or "זוגי" in combined_text or re.match(r'^\d+\s', title):
        discount_types.append("fixed_price_bundle")
        qty_match = re.match(r'^(\d+)\s', title)
        if qty_match:
            condition = {"type": "min_quantity", "value": int(qty_match.group(1))}
        reward = {"type": "fixed_price", "value": price_after if price_after else price_before}

    # 5. Percentage Off
    elif "%" in combined_text:
        discount_types.append("percentage_off")
        match = re.search(r'(\d+)%', combined_text)
        val = float(match.group(1))/100 if match else round(1 - (price_after / price_before), 2) if price_before > 0 else 0
        reward = {"type": "percentage_off", "value": val}

    # 6. Bonus Value / Wallet Credit
    elif "מתנה" in combined_text or "תוספת" in combined_text:
        discount_types.append("bonus_value_wallet_credit")
        reward = {"type": "gift_item", "value": "bonus"}

    # Fallback to defaults based strictly on price if text matching fails
    if not discount_types:
        if price_before > 0 and price_after > 0:
            discount_types.append("fixed_price_bundle")
            reward = {"type": "fixed_price", "value": price_after}
        elif price_before > 0 and price_after == 0:
            discount_types.append("percentage_off")
            reward = {"type": "percentage_off", "value": 1.0}

    # Append standard delivery mechanism
    if main.get("isCoupon"):
        discount_types.append("coupon")

    return discount_types, condition, reward


def convert_hot_to_template(hot_data):
    converted_deals = []
    
    # Generate unified timestamp for the batch conversion
    current_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    for item in hot_data:
        main = item.get("data", {}).get("main", {})
        info = item.get("data", {}).get("information", [])
        
        # Extract Terms and Conditions text for the analyzer
        terms = ""
        for section in info:
            if section.get("title") == "תנאי ההטבה":
                terms = section.get("content", "")
                break
                
        # Deduce logic components dynamically
        discount_types, condition, reward = deduce_discount_mechanics(main, terms)
        
        deal = {
            "_id": f"deal_{main.get('id')}",
            "source_id": "src_hot",
            "external_id": main.get("id"),
            
            "store_id": f"store_{str(main.get('item_brand', 'unknown')).replace(' ', '_')}",
            "club_id": "club_hot",
            "category_id": main.get("item_category"),
            "product_id": None,
            
            "title": main.get("title"),
            "description": main.get("description") or main.get("free_text", ""),
            "terms_and_conditions": terms,
            
            "store_url": main.get("supplierWebsite", ""),
            "benefit_url": main.get("dynamicLink", ""),
            "image_url": f"https://www.hot.co.il{main.get('imagePath', '')}" if main.get('imagePath') else "",
            
            "trigger_type": "coupon" if main.get("isCoupon") else "credit_card",
            "coupon_code": "HOT", 
            
            # Populating unified discount schema fields
            "discount_type": discount_types,
            "condition": condition,
            "reward": reward,
            
            "is_specific_items_only": False,
            "is_stackable": False,
            
            "valid_from": main.get("exposure_start_date"),
            "valid_until": f"{main.get('benefit_deadline_date')}Z" if main.get('benefit_deadline_date') else None,
            
            "redeem_channels": ["online", "physical_store"],
            
            "constraints": {
                "club_members_only": True,
                "requires_specific_credit_card": True,
                "not_valid_with_other_promotions": True,
                "usage_limit_per_user": 1
            },
            
            "status": "active" if main.get("active") and not main.get("is_expired") else "inactive",
            
            # New Timestamps Block
            "created_at": current_time,
            "updated_at": current_time,
            "scraped_at": current_time,
            "last_seen_at": current_time
        }
        
        converted_deals.append(deal)
        
    return converted_deals

if __name__ == "__main__":
    with open("outputs\hot_details_800.json", "r", encoding="utf-8") as file:
        hot_data = json.load(file)
        
    formatted_data = convert_hot_to_template(hot_data)
    
    with open("formatted_discounts.json", "w", encoding="utf-8") as file:
        json.dump(formatted_data, file, ensure_ascii=False, indent=2)
        
    print(f"Successfully converted {len(formatted_data)} records.")