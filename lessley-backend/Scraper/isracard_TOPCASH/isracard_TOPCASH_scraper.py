import json
import uuid
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def scrape_topcash_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all store containers in the HTML
    store_containers = soup.find_all('div', class_='store-container')
    
    discounts = []
    current_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    for store in store_containers:
        try:
            # 1. Extract title and URLs
            name_tag = store.find('div', class_='storeName').find('a')
            if not name_tag:
                continue
                
            title = name_tag.text.strip()
            details_url = name_tag.get('href', '')
            
            # Parse IDs from the URL (e.g. https://www.topcash.co.il/store/super-pharm/5167)
            external_id = None
            store_id = None
            if details_url:
                parts = details_url.rstrip('/').split('/')
                if len(parts) >= 2:
                    store_id = parts[-2]
                    external_id = parts[-1]
                    
            # 2. Extract reward text (e.g., "3% קאשבק" or "100₪ קאשבק")
            subtitle_tag = store.find('div', class_='store-block-sub-title')
            reward_text = subtitle_tag.text.strip() if subtitle_tag else ""
            
            reward_type = "unknown"
            reward_value = None
            
            # Determine if the reward is a percentage or a fixed amount
            if '%' in reward_text:
                reward_type = "percentage_off"
                match = re.search(r'([\d.]+)', reward_text)
                if match:
                    # Convert percentage to a decimal (e.g., 3 -> 0.03)
                    reward_value = float(match.group(1)) / 100.0
            elif '₪' in reward_text:
                reward_type = "fixed_discount_amount"
                match = re.search(r'([\d.]+)', reward_text)
                if match:
                    reward_value = float(match.group(1))
                    
            # 3. Extract image URL
            img_tag = store.find('img')
            image_url = ""
            if img_tag:
                image_url = img_tag.get('data-src') or img_tag.get('src')
                # Resolve relative URLs
                if image_url and image_url.startswith('/'):
                    image_url = f"https://www.topcash.co.il{image_url}"
                    
            # 4. Extract purchase URL
            buy_btn = store.find('a', class_='isracard-new-button')
            store_url = buy_btn.get('href') if buy_btn else details_url

            # 5. Build the JSON object matching the Mastercard schema
            discount_entry = {
                "_id": str(uuid.uuid4()),
                "source_id": "topcash",
                "external_id": external_id,
                "store_id": store_id,
                "club_id": "topcash",
                "category_id": None,
                "product_id": None,
                "title": f"{reward_text} באתר {title}",
                "description": f"{reward_text} באתר {title}. ההטבה מותנית במעבר דרך לינק הקאשבק.",
                "terms_and_conditions": None,
                "store_url": store_url,
                "benefit_url": details_url,
                "image_url": image_url,
                "trigger_type": "auto", # Cashback is typically applied automatically via tracking links
                "coupon_code": None,
                "condition": None,
                "reward": {
                    "type": reward_type,
                    "value": reward_value
                },
                "is_specific_items_only": False,
                "is_stackable": True,
                "valid_from": current_time,
                "valid_until": None,
                "redeem_channels": ["online"],
                "redeem_days": ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
                "redeem_hours": [{"from": "00:00", "to": "23:59"}],
                "redeem_date_ranges": [],
                "applicable_branch_ids": ["national_deployment"],
                "excluded_branch_ids": [],
                "applicable_product_ids": [],
                "excluded_product_ids": [],
                "constraints": {
                    "max_discount_amount": None,
                    "max_monthly_spend_limit": None,
                    "max_vouchers_per_transaction": None,
                    "club_members_only": True,
                    "requires_specific_credit_card": False,
                    "not_valid_with_other_promotions": False,
                    "usage_limit_per_user": None
                },
                "status": "active",
                "scraped_at": current_time,
                "last_seen_at": current_time,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            discounts.append(discount_entry)
            
        except Exception as e:
            print(f"Skipping a store due to parsing error: {e}")
            
    return json.dumps(discounts, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # Ensure you have installed beautifulsoup4: pip install beautifulsoup4
    with open('TOPCASH _ כל החנויות.html', 'r', encoding='utf-8') as f:
        html_data = f.read()
        
    extracted_json = scrape_topcash_to_json(html_data)
    
    # Save the results
    with open('topcash_discounts.json', 'w', encoding='utf-8') as out_file:
        out_file.write(extracted_json)
        
    print("Extraction complete. Check topcash_discounts.json")