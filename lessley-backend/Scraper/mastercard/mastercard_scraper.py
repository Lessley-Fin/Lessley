
##################################################################
##################################################################
#working version except of the store_url
##################################################################
##################################################################


#################################################################
# need to add store_id, product_id, club_id, category_code
################################################################

from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# --- SETTINGS & URL ---
URL = "https://www.mastercard.co.il/he-il/personal/offers-and-promotions/mastercard-day.html"

def parse_cleaned_text(clean_text, idx, terms_text, store_url):
    """
    Takes cleaned-up Hebrew text, the scraped modal terms, the exact button URL, 
    and maps it to the UNIFIED JSON Schema.
    """
    now = datetime.utcnow()
    id_date = now.strftime("%Y%m")
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Set dates to the 10th of the current month
    current_year = now.year
    current_month = now.month
    valid_from_str = f"{current_year}-{current_month:02d}-10T00:00:00Z"
    valid_until_str = f"{current_year}-{current_month:02d}-10T23:59:59Z"
    valid_date_only = f"{current_year}-{current_month:02d}-10"
    
    unique_id = f"deal_mc_{id_date}_{idx:02d}"

    # 1. Stackability Logic (Refined)
    if "לא כולל כפל מבצעים" in clean_text or "ללא כפל מבצעים" in clean_text:
        is_stackable = False
    elif "כולל כפל" in clean_text:
        is_stackable = True
    else:
        is_stackable = False

    # 2. Merchant Logic
    merchant = "Unknown"
    merchant_regex = r'(?:באתר|בחנויות|בסניפי|באפליקציית)(?:\s+ו?[א-ת]+)?\s+([a-zA-Zא-ת0-9\s&]+?)(?=\.|,|-|תקף|כולל|ללא|לא כולל|בכפוף|\(|$)'
    merchant_match = re.search(merchant_regex, clean_text)
    if merchant_match:
        merchant = merchant_match.group(1).strip()
        
    store_id_safe = "store_" + merchant.replace(" ", "_").lower() if merchant != "Unknown" else f"store_mc_{idx:02d}"

    # 3. Dynamic Channel Logic
    redeem_channels = []
    if any(word in clean_text for word in ["באתר", "אונליין"]):
        redeem_channels.append("online")
    if any(word in clean_text for word in ["באפליקציית", "באפליקציה"]):
        redeem_channels.append("mobile_app")
    if any(word in clean_text for word in ["בחנויות", "בסניפי"]):
        redeem_channels.append("physical_store")
    if not redeem_channels:
        redeem_channels = ["online"] # Default fallback

    # 4. Build the UNIFIED JSON Structure
    discount_obj = {
        "_id": unique_id,
        "source_id": "src_mastercard_day",
        "external_id": f"mc_dxp_{idx:02d}",

        "store_id": store_id_safe,
        "club_id": "club_mastercard",
        "category_id": "cat_general",
        "product_id": None,

        "title": "Unknown Offer",  
        "description": clean_text,
        "terms_and_conditions": terms_text,

        "store_url": store_url,
        "benefit_url": URL,
        "image_url": None,

        "trigger_type": "auto",
        "coupon_code": None,

        "condition": {
            "type": "min_quantity",
            "value": 1
        },
        "reward": {
            "type": "percentage_off",
            "value": 0.0
        },

        "is_specific_items_only": False,
        "is_stackable": is_stackable,

        "valid_from": valid_from_str,
        "valid_until": valid_until_str,

        "redeem_channels": redeem_channels,
        "redeem_days": ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
        "redeem_hours": [{"from": "00:00", "to": "23:59"}],
        "redeem_date_ranges": [{"from": valid_date_only, "to": valid_date_only}],

        "applicable_branch_ids": ["national_deployment"],
        "excluded_branch_ids": [],
        "applicable_product_ids": [],
        "excluded_product_ids": [],

        "constraints": {
            "max_discount_amount": None,
            "max_monthly_spend_limit": None,
            "max_vouchers_per_transaction": None,
            "club_members_only": True,
            "requires_specific_credit_card": True,
            "not_valid_with_other_promotions": not is_stackable,
            "usage_limit_per_user": 1
        },

        "status": "active",
        "scraped_at": now_iso,
        "last_seen_at": now_iso,
        "created_at": now_iso,
        "updated_at": now_iso
    }

    # --- 5. EXTRACT MATH DETAILS VIA ADVANCED HEURISTICS ---
    title_match = re.search(r'^(.*?[₪%$€])(.*?)$', clean_text, re.DOTALL)
    if title_match:
        discount_obj["title"] = title_match.group(1).strip()
    else:
        # Fallback if no symbol is found
        discount_obj["title"] = clean_text.split('.')[0] 

    # Type A: Wallet Credit / Cashback (e.g., Booking.com)
    if "קרדיט לארנק" in clean_text or "קאשבק" in clean_text:
        perc_match = re.search(r'(\d+)%', discount_obj["title"])
        if perc_match:
            discount_obj["condition"] = {"type": "min_quantity", "value": 1}
            discount_obj["reward"] = {"type": "wallet_credit_percentage", "value": int(perc_match.group(1)) / 100.0}
        else:
            ils_match = re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?\s*קרדיט', clean_text)
            if ils_match:
                discount_obj["condition"] = {"type": "min_quantity", "value": 1}
                discount_obj["reward"] = {"type": "wallet_credit_amount", "value": int(ils_match.group(1).replace(",", ""))}

    # Type B: Bonus Value Multiplier (e.g., EV-Edge 25 NIS gift for 175 NIS)
    elif "מתנה" in clean_text and ("טעינה" in clean_text or "שובר" in clean_text):
        bonus_match = re.search(r'(?:₪|€|\$)?\s*(\d+)\s*(?:₪|€|\$)?\s*מתנה', clean_text)
        spend_match = re.search(r'(?:בעלות של|ב-)\s*(?:₪|€|\$)?\s*(\d+)', clean_text)
        if bonus_match and spend_match:
            discount_obj["condition"] = {"type": "exact_spend", "value": int(spend_match.group(1))}
            discount_obj["reward"] = {"type": "bonus_value", "value": int(bonus_match.group(1))}

    # Type C: BOGO / 1+1 (e.g., Buy 1 Get 1)
    elif re.search(r'(\d+)\+(\d+)', clean_text):
        bogo_match = re.search(r'(\d+)\+(\d+)', clean_text)
        buy = int(bogo_match.group(1))
        get_free = int(bogo_match.group(2))
        discount_obj["condition"] = {"type": "min_quantity", "value": buy + get_free}
        discount_obj["reward"] = {"type": "free_items", "value": get_free}

    # Type D: Fixed Total Amount / Bundles (e.g., Dominos 2 pizzas for 130)
    elif re.search(r'(\d+)\s+[א-ת]+.*?(?:ב-|ב\s*)(\d+)\s*₪', discount_obj["title"]):
        bundle_match = re.search(r'(\d+)\s+[א-ת]+.*?(?:ב-|ב\s*)(\d+)\s*₪', discount_obj["title"])
        discount_obj["condition"] = {"type": "min_quantity", "value": int(bundle_match.group(1))}
        discount_obj["reward"] = {"type": "fixed_total_amount", "value": int(bundle_match.group(2))}

    # Type E: Spend & Save / Tiered Amount (e.g., Terminal X 50 off 250)
    elif re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?(?:ברכישת|בקניית|מעל).*?(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', clean_text):
        match_ils = re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?(?:ברכישת|בקניית|מעל).*?(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', clean_text)
        discount_obj["condition"] = {"type": "min_spend", "value": int(match_ils.group(2).replace(",", ""))}
        discount_obj["reward"] = {"type": "fixed_discount_amount", "value": int(match_ils.group(1).replace(",", ""))}
        
        # Additional constraint: If it specifies a max discount
        max_discount = re.search(r'עד\s*(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', clean_text)
        if max_discount:
            discount_obj["constraints"]["max_discount_amount"] = int(max_discount.group(1).replace(",", ""))

    # Type F: Classic Percentage Off (Fallback)
    elif '%' in discount_obj["title"]:
        match_percent = re.search(r'(\d+)%', discount_obj["title"])
        if match_percent:
            discount_obj["condition"] = {"type": "min_quantity", "value": 1}
            discount_obj["reward"] = {"type": "percentage_off", "value": int(match_percent.group(1)) / 100.0}

    # 6. Extract Coupon Code Trigger
    code_match = re.search(r'קוד קופון[א-ת\s]*:?\s*([a-zA-Z0-9]{4,})', clean_text)
    if code_match:
        discount_obj["trigger_type"] = "coupon"
        discount_obj["coupon_code"] = code_match.group(1)

    return discount_obj

def extract_modal_text(modal_id, soup):
    """
    Finds the correct modal by ID and smartly extracts the text without breaking sentences.
    """
    if not modal_id:
        return None

    modal = soup.find('dxp-modal', {'modal-id': modal_id})
    if modal:
        text_container = modal.find(class_="text-editor") or modal
        
        # 1. Replace <br> tags with physical newlines
        for br in text_container.find_all("br"):
            br.replace_with("\n")
            
        # 2. Append newlines to the end of block elements (like paragraphs and lists)
        for block in text_container.find_all(["p", "div", "li", "h1", "h2", "h3"]):
            block.insert_after("\n")
            
        # 3. Extract text using space as separator (so inline tags like <u> don't break lines)
        raw_text = text_container.get_text(separator=' ')
        
        # 4. Clean up invisible RTL characters
        for char in ['\xa0', '\u200e', '\u200f', '\u202a', '\u202b']:
            raw_text = raw_text.replace(char, ' ')
            
        # 5. Fix up the spacing
        raw_text = re.sub(r' +', ' ', raw_text)       # Collapse multiple spaces
        raw_text = re.sub(r' \n', '\n', raw_text)     # Remove spaces before newlines
        raw_text = re.sub(r'\n ', '\n', raw_text)     # Remove spaces after newlines
        raw_text = re.sub(r'\n+', '\n', raw_text)     # Collapse multiple newlines
        
        return raw_text.strip()
    return None

def scrape_dxp_fast(url):
    print(f"🚀 Fetching URL via Requests: {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, impersonate="chrome120")
    response.raise_for_status()

    response.encoding = 'utf-8'

    print("📝 Compiling final JSON data from HTML...")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    dxp_blocks = soup.find_all('dxp-content-item')
    print(f"✅ Found {len(dxp_blocks)} offer blocks.")
    
    final_discounts = []
    
    for idx, block in enumerate(dxp_blocks):
        try:
            raw_description_html = block.get('description')
            if not raw_description_html: continue
            
            raw_text = BeautifulSoup(raw_description_html, 'html.parser').get_text(separator=' ', strip=True)
            clean_text = raw_text.replace('\xa0', ' ').replace('\u200e', '').replace('\u200f', '').replace('\u202a', '').replace('\u202b', '')
            
            store_url = None
            modal_id = None
            
            # --- FIXED JAVASCRIPT EXTRACTION ---
            script_tag = block.find('script')
            if script_tag and script_tag.string:
                # 1. Safely extract the modal-id for the T&C popup
                modal_match = re.search(r'"modal-target"\s*:\s*"([^"]+)"', script_tag.string)
                if modal_match:
                    modal_id = modal_match.group(1)
                    
                # 2. Extract the actual Javascript block, strip trailing commas, and parse it
                try:
                    start_idx = script_tag.string.find('dxpSelector.ctaData=')
                    if start_idx != -1:
                        array_str = script_tag.string[start_idx:].split('dxpSelector.ctaData=')[1]
                        end_idx = array_str.find('dxpSelector.actionList')
                        if end_idx != -1:
                            array_str = array_str[:end_idx].strip()
                        
                        # Strip the invalid trailing comma so python can parse it!
                        array_str = array_str.rstrip(';, \n')
                        
                        cta_data = json.loads(array_str)
                        for group in cta_data:
                            for cta in group.get('ctaList', []):
                                if 'לאתר' in cta.get('text', ''):
                                    store_url = cta.get('href')
                except Exception as e:
                    pass

            # If the script parsing failed, fallback to the popup modal for the link
            if not store_url and modal_id:
                modal = soup.find('dxp-modal', {'modal-id': modal_id})
                if modal:
                    for a_tag in modal.find_all('a', href=True):
                        href = a_tag['href']
                        if "javascript" not in href.lower() and ".pdf" not in href.lower() and "mastercard" not in href.lower():
                            store_url = href
                            break

            terms_text = extract_modal_text(modal_id, soup)
            
            mapped_discount = parse_cleaned_text(clean_text, idx, terms_text, store_url)
            final_discounts.append(mapped_discount)
            
        except Exception as e:
            print(f"Skipping block {idx} due to error: {e}")

    return final_discounts

if __name__ == "__main__":
    try:
        scraped_data = scrape_dxp_fast(URL)
        print("\n" + "="*40 + "\nCOMPLETED. FINALIZING OUTPUT\n" + "="*40 + "\n")
        
        with open("mastercard_discounts.json", "w", encoding="utf8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Successfully scraped {len(scraped_data)} discounts!")
        
    except Exception as e:
        print(f"❌ Critical error during scraping process: {e}")