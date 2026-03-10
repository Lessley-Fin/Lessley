import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

def clean_html(raw_html):
    """Removes HTML tags and cleans up invisible characters/spacing."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Clean up non-breaking spaces and invisible RTL characters
    return text.replace('\xa0', ' ').replace('\u200e', '').replace('\u200f', '').strip()

def extract_links(raw_html):
    """Finds the first valid external link inside an HTML block."""
    if not raw_html:
        return None
    soup = BeautifulSoup(raw_html, "html.parser")
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith("http") and "multipass" not in href and "stepin" not in href:
            return href
    return None

def convert_hot_discount(raw_item):
    """
    Takes a single raw HOT API item and maps it to the Unified Schema.
    """
    # Depending on how you save the array, the data might be nested under "data"
    data = raw_item.get("data", raw_item) 
    main = data.get("main", {})
    
    item_id = main.get("id", "unknown")
    
    # 1. Combine and clean all textual information
    info_blocks = main.get("information", []) + data.get("information", [])
    full_text = " ".join([clean_html(block.get("content", "")) for block in info_blocks])
    
    description = clean_html(main.get("information", [{}])[0].get("content", "")) if main.get("information") else ""
    terms = clean_html(data.get("information", [{}])[0].get("content", "")) if data.get("information") else ""
    
    # 2. Extract specific constraints using Regex heuristics on the combined text
    is_stackable = "כולל כפל מבצעים" in full_text
    
    redeem_channels = ["physical_store"]
    if "לא ניתן למימוש באתר" not in full_text and "לא תקף באתר" not in full_text:
        redeem_channels.append("online")
        
    excluded_branches = ["outlet_stores"] if "חנויות העודפים" in full_text else []
    excluded_products = []
    if "פריטי עודפים" in full_text: excluded_products.append("outlet_items")
    if "כרטיס מתנה" in full_text: excluded_products.append("gift_cards")

    # Extract max monthly spend (e.g., "עד 3,000 ₪ לעמית מועדון")
    max_monthly_spend = None
    spend_match = re.search(r'עד\s*([0-9,]+)\s*₪\s*לעמית', full_text)
    if spend_match:
        max_monthly_spend = int(spend_match.group(1).replace(",", ""))

    # Extract max vouchers per transaction (e.g., "עד 2 שוברים בעסקה")
    max_vouchers = None
    voucher_match = re.search(r'עד\s*(\d+)\s*שוברים\s*בעסקה', full_text)
    if voucher_match:
        max_vouchers = int(voucher_match.group(1))

    # 3. Determine Reward Math
    # HOT usually uses "XX% הנחה" as statement credits
    reward_value = 0.0
    value_num_str = main.get("valueNum", "")
    perc_match = re.search(r'(\d+(?:\.\d+)?)%', value_num_str)
    if perc_match:
        reward_value = float(perc_match.group(1)) / 100.0

    # 4. Build the final object
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Attempt to extract store URL from the description HTML
    raw_desc_html = main.get("information", [{}])[0].get("content", "") if main.get("information") else ""
    store_url = extract_links(raw_desc_html)

    base_image_url = "https://hot.co.il"
    image_path = main.get("imagePath", "")

    unified_discount = {
        "_id": f"deal_hot_{item_id}",
        "source_id": "src_moadon_hot",
        "external_id": item_id,
        
        "store_id": f"store_{main.get('title', 'unknown').split(' ')[-1].lower()}",
        "club_id": "club_hot",
        "category_id": "cat_" + "_".join(data.get("tags", ["general"])[0].split(" ")),
        "product_id": "voucher_digital" if main.get("isCoupon") else None,
        
        "title": f"{main.get('title', '')} ב-{value_num_str}",
        "description": description,
        "terms_and_conditions": terms,
        
        "store_url": store_url,
        "benefit_url": main.get("dynamicLink"),
        "image_url": f"{base_image_url}{image_path}" if image_path else None,
        
        "trigger_type": "purchase_voucher" if main.get("isCoupon") else "auto",
        "coupon_code": None,
        
        "condition": {
            "type": "min_spend",
            "value": 0  # Standard for % based vouchers
        },
        "reward": {
            "type": "statement_credit_percentage",
            "value": reward_value
        },
        
        "is_specific_items_only": False,
        "is_stackable": is_stackable,
        
        "valid_from": None,
        "valid_until": None,
        
        "redeem_channels": redeem_channels,
        "redeem_days": ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
        "redeem_hours": [{"from": "00:00", "to": "23:59"}],
        "redeem_date_ranges": [],
        
        "applicable_branch_ids": ["national_deployment"],
        "excluded_branch_ids": excluded_branches,
        
        "applicable_product_ids": [],
        "excluded_product_ids": excluded_products,
        
        "constraints": {
            "max_discount_amount": None,
            "max_monthly_spend_limit": max_monthly_spend,
            "max_vouchers_per_transaction": max_vouchers,
            "club_members_only": True,
            "requires_specific_credit_card": True,
            "not_valid_with_other_promotions": not is_stackable,
            "usage_limit_per_user": None
        },
        
        "status": "active" if main.get("active") else "inactive",
        "scraped_at": now_iso,
        "last_seen_at": now_iso,
        "created_at": now_iso,
        "updated_at": now_iso
    }
    
    return unified_discount

def convert_file(input_filename, output_filename):
    print(f"Reading from {input_filename}...")
    
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        # Handle case where input is a single object vs a list
        if isinstance(raw_data, dict):
            # If the file looks like {"statusCode": 201, "data": {...}}
            if "data" in raw_data and isinstance(raw_data["data"], dict) and "main" in raw_data["data"]:
                 items_to_process = [raw_data]
            else:
                # Might be a dictionary containing a list under some key
                items_to_process = next((v for v in raw_data.values() if isinstance(v, list)), [raw_data])
        else:
            items_to_process = raw_data

        converted_items = []
        for item in items_to_process:
            try:
                converted_items.append(convert_hot_discount(item))
            except Exception as e:
                print(f"Skipped an item due to error: {e}")
                
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(converted_items, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Successfully converted {len(converted_items)} discounts!")
        print(f"Output saved to {output_filename}")
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find file {input_filename}")
    except json.JSONDecodeError:
        print(f"❌ Error: {input_filename} is not a valid JSON file.")

# --- EXECUTION ---
if __name__ == "__main__":
    # Assumes you have a file named 'hot_discounts_raw.json' in the same folder.
    # You can change the names below to match your actual files.
    INPUT_FILE = "outputs\hot_details_1300.json"  # Replace with your bulk file name
    OUTPUT_FILE = "outputs\hot_unified_discounts_3.json"
    
    convert_file(INPUT_FILE, OUTPUT_FILE)