import json
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li", "h1", "h2", "h3"]):
        block.insert_after("\n")
    text = soup.get_text(separator=' ')
    for char in ['\xa0', '\u200e', '\u200f', '\u202a', '\u202b']:
        text = text.replace(char, ' ')
    text = re.sub(r' +', ' ', text)
    text = re.sub(r' \n', '\n', text)
    text = re.sub(r'\n ', '\n', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()

def deduce_discount_mechanics(main, info_text):
    """
    Analyzes the text and pricing to map the promotion into the unified JSON Schema
    using an if-elif fallback logic.
    """
    title = str(main.get("title", "") or "")
    desc = str(main.get("description", "") or "")
    free_text = str(main.get("free_text", "") or "")
    cashback_desc = str(main.get("cashback_description", "") or "")
    value_field = str(main.get("value", "") or "")
    value_num_field = str(main.get("valueNum", "") or "")
    
    # Combine text fields for easier regex searching
    combined_text = f"{title} {desc} {free_text} {info_text} {cashback_desc} {value_field} {value_num_field}"

    price_before = float(main.get("price_before_discount") or 0)
    price_after = float(main.get("price_after_discount") or 0)

    # Defaults
    condition = {"type": "min_quantity", "value": 1}
    reward = {"type": "percentage_off", "value": 0.0}
    constraints = {}

    benefit_type = str(main.get('benefit_type') or main.get('type') or '')

    # Type Vouchers (benefit_type 1300): Pay "after price", get "before price"
    if benefit_type == "1300" and price_before > 0 and price_after > 0:
        condition = {"type": "exact_spend", "value": price_before}
        reward = {"type": "fixed_total_amount", "value": price_after}

    # Type Vouchers (benefit_type 1300): With Percentage, Explicit title
    elif benefit_type == "1300" and (title_amount_match := re.search(r'(\d[,0-9]*)\s*₪', title)) and (percent_match := re.search(r'(\d+(?:\.\d+)?)%', value_field + " " + value_num_field + " " + combined_text)):
        total_val = int(title_amount_match.group(1).replace(",", ""))
        discount_pct = float(percent_match.group(1)) / 100.0
        condition = {"type": "exact_spend", "value": total_val}
        reward = {"type": "fixed_total_amount", "value": round(total_val * (1 - discount_pct), 2)}

    # Exact Spend / Value Voucher (Top priority over percentages. e.g "שווי X ב Y")
    elif (match_alt := re.search(r'שווי.*?(\d[,0-9]*).*?ב-?\s*(\d[,0-9]*)', combined_text)):
        val1 = int(match_alt.group(1).replace(",", ""))
        val2 = int(match_alt.group(2).replace(",", ""))
        condition = {"type": "exact_spend", "value": val1}
        reward = {"type": "fixed_total_amount", "value": val2}

    # Type F: Classic Percentage Off (Prioritize over loose texts as % match is highly specific)
    elif '%' in combined_text:
        match_percent = re.search(r'(\d+(?:\.\d+)?)%', value_field + " " + value_num_field + " " + title + " " + combined_text)
        if match_percent:
            reward = {"type": "percentage_off", "value": float(match_percent.group(1)) / 100.0}
        elif price_before > 0:
            reward = {"type": "percentage_off", "value": round(1 - (price_after / price_before), 2)}

    # Type E: Spend & Save / Tiered Amount Off (Fallback)
    elif re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?(?:ברכישת|בקניית|מעל|במינימום).*?(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', combined_text):
        match_ils = re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?(?:ברכישת|בקניית|מעל|במינימום).*?(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', combined_text)
        condition = {"type": "min_spend", "value": int(match_ils.group(2).replace(",", ""))}
        reward = {"type": "fixed_discount_amount", "value": int(match_ils.group(1).replace(",", ""))}

        # Additional constraint: If it specifies a max discount
        max_discount = re.search(r'עד\s*(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', combined_text)
        if max_discount:
            constraints["max_discount_amount"] = int(max_discount.group(1).replace(",", ""))

    # Fallback to defaults based strictly on price if text matching fails
    else:
        if price_before > 0 and price_after > 0:
            condition = {"type": "exact_spend", "value": price_before}
            reward = {"type": "fixed_total_amount", "value": price_after}
        elif price_before > 0 and price_after == 0:
            reward = {"type": "percentage_off", "value": 1.0}

    return condition, reward, constraints


def convert_hot_to_template(hot_data):
    converted_deals = []
    
    # Generate unified timestamp for the batch conversion
    current_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    for item in hot_data:
        main = item.get("data", {}).get("main", {})
        info = item.get("data", {}).get("information", [])
        main_info = main.get("information", [])
        
        # Combine all HTML content from information arrays
        all_info = info + main_info
        
        terms_html = ""
        details_html = ""
        for section in all_info:
            section_title = section.get("title", "")
            if "תנאי" in section_title or "מימוש" in section_title:
                terms_html += section.get("content", "") + " \n"
            elif "פרטי" in section_title:
                details_html += section.get("content", "") + " \n"

        terms_text = clean_html(terms_html)
        details_text = clean_html(details_html)
        combined_text_for_analysis = f"{details_text} {terms_text}"
        
        # Deduce logic components dynamically
        condition, reward, extracted_constraints = deduce_discount_mechanics(main, combined_text_for_analysis)
        
        # Stackability Extraction
        is_stackable = False
        if "לא כולל כפל" in combined_text_for_analysis or "ללא כפל" in combined_text_for_analysis or "אין כפל" in combined_text_for_analysis:
            is_stackable = False
        elif "כולל כפל" in combined_text_for_analysis:
            is_stackable = True
            
        # Redeem Channels Extraction
        redeem_channels = []
        if any(word in combined_text_for_analysis for word in ["באתר", "אונליין", "באתר הסחר", "online"]):
            redeem_channels.append("online")
        if any(word in combined_text_for_analysis for word in ["באפליקציית", "באפליקציה", "אפליקציה"]):
            redeem_channels.append("mobile_app")
        if any(word in combined_text_for_analysis for word in ["בחנויות", "בסניפי", "קופה", "בסניפים", "בקופה", "איסוף עצמי"]):
            redeem_channels.append("physical_store")
        if not redeem_channels:
            redeem_channels = ["online", "physical_store"]

        # Merge constraints with defaults
        base_constraints = {
            "max_discount_amount": None,
            "max_monthly_spend_limit": None,
            "max_vouchers_per_transaction": None,
            "club_members_only": True,
            "requires_specific_credit_card": True,
            "not_valid_with_other_promotions": not is_stackable,
            "usage_limit_per_user": 1
        }
        base_constraints.update(extracted_constraints)
        
        # Dates logic (Adding Z)
        valid_from = main.get("exposure_start_date")
        if valid_from and not valid_from.endswith("Z"):
            valid_from += "Z"
            
        valid_until = main.get("benefit_deadline_date")
        if valid_until and not valid_until.endswith("Z"):
            valid_until += "Z"

        brand_name = str(main.get('item_brand', 'unknown')).replace(' ', '_').replace('-', '_').lower()
        
        # Extract URLs
        url_obj = main.get("url")
        if isinstance(url_obj, dict):
            store_url = url_obj.get("app_link") or url_obj.get("route") or main.get("supplierWebsite", "")
        else:
            store_url = main.get("supplierWebsite", "")
            
        if isinstance(store_url, str) and store_url.strip() and not store_url.startswith("http"):
            store_url = "https://" + store_url
        if not store_url or not isinstance(store_url, str):
            store_url = ""
            
        benefit_url = main.get("dynamicLink") or f"https://www.hot.co.il/benefits/{main.get('id')}"
        
        # Extract Branches from supplierLocations
        supplier_locations = item.get("data", {}).get("supplierLocations", {})
        branches = []
        if isinstance(supplier_locations, dict):
            for city, locations in supplier_locations.items():
                if isinstance(locations, list):
                    for loc in locations:
                        if isinstance(loc, dict) and loc.get("fullAddress"):
                            branches.append(loc.get("fullAddress"))
        elif isinstance(supplier_locations, list):
            for loc in supplier_locations:
                if isinstance(loc, dict) and loc.get("fullAddress"):
                    branches.append(loc.get("fullAddress"))
        
        deal = {
            "_id": f"deal_{main.get('id')}",
            "source_id": "src_hot",
            "external_id": str(main.get("id")),
            
            "store_id": f"{brand_name}",
            "club_id": "hot",
            "category_id": main.get("item_category"),
            "product_id": None,
            
            "title": main.get("title"),
            "description": f"{main.get('description') or ''} {main.get('free_text') or ''}".strip() or details_text[:200],
            "terms_and_conditions": terms_text,
            
            "store_url": store_url,
            "benefit_url": benefit_url,
            "image_url": f"https://cdn.hot.co.il{main.get('imagePath', '')}" if main.get('imagePath') else "",
            
            "trigger_type": "coupon" if main.get("isCoupon") else "auto",
            "coupon_code": "HOT" if main.get("isCoupon") else None, 
            
            "condition": condition,
            "reward": reward,
            
            "is_specific_items_only": False,
            "is_stackable": is_stackable,
            
            "valid_from": valid_from,
            "valid_until": valid_until,
            
            "redeem_channels": redeem_channels,
            "redeem_days": ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
            "redeem_hours": [{"from": "00:00", "to": "23:59"}],
            "redeem_date_ranges": [{"from": valid_from[:10] if valid_from else "2000-01-01", "to": valid_until[:10] if valid_until else "2099-12-31"}],
            
            "applicable_branch_ids": branches if branches else ["national_deployment"],
            "excluded_branch_ids": [],
            "applicable_product_ids": [],
            "excluded_product_ids": [],
            
            "constraints": base_constraints,
            
            "status": "active" if main.get("active") and not main.get("is_expired") else "inactive",
            
            "scraped_at": current_time,
            "last_seen_at": current_time,
            "created_at": current_time,
            "updated_at": current_time
        }
        
        converted_deals.append(deal)
        
    return converted_deals

import argparse
import sys

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert scraped HOT deals JSON into the mastercard_discounts.json schema template."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to the input JSON file containing scraped HOT deals (e.g. outputs/hot_specific_deals.json)"
    )
    parser.add_argument(
        "-o", "--output",
        default="formatted_discounts.json",
        help="Path to the output formatted JSON file. Defaults to formatted_discounts.json"
    )
    
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as file:
            hot_data = json.load(file)
    except FileNotFoundError:
        print(f"Error: Input file '{args.input}' not found.")
        sys.exit(1)
        
    formatted_data = convert_hot_to_template(hot_data)
    
    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(formatted_data, file, ensure_ascii=False, indent=2)
        
    print(f"Successfully converted {len(formatted_data)} records and saved to {args.output}.")