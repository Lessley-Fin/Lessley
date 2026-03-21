from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import uuid
import re
from datetime import datetime

# --- SETTINGS & URL ---
URL = "https://www.mastercard.co.il/he-il/personal/offers-and-promotions/mastercard-day.html"

def normalize_store(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def extract_categories(soup):
    categories = set()

    for script in soup.find_all("script"):
        content = script.string or script.text
        if "inPageNavItemsData" in content:
            matches = re.findall(r'"href":"#(.*?)"', script.string)
            categories.update(matches)

    return categories

def extract_real_categories(soup):
    categories = extract_categories(soup)

    real = set()
    for cat in categories:
        if soup.find("div", {"id": cat}):
            real.add(cat)

    return real

def extract_title(clean_text):
    title_parts = re.split(r'(?:\.|\s+תקף\b|\s+תקפה\b|\s+המבצע\b|\s+ההטבה\b|\s+כולל כפל\b|\s+לא כולל\b|\s+בלעדי\b)', clean_text)
    if title_parts and title_parts[0].strip():
        return title_parts[0].strip()
    return clean_text.split('.')[0].strip()

def check_stackable(clean_text):
    if "לא כולל כפל מבצעים" in clean_text or "ללא כפל מבצעים" in clean_text:
        return False
    elif "כולל כפל" in clean_text:
        return True
    return False

def extract_redeem_channels(clean_text):
    redeem_channels = []
    if any(word in clean_text for word in ["באתר", "אונליין"]):
        redeem_channels.append("online")
    if any(word in clean_text for word in ["באפליקציית", "באפליקציה"]):
        redeem_channels.append("mobile_app")
    if any(word in clean_text for word in ["בחנויות", "בסניפי"]):
        redeem_channels.append("physical_store")
    if not redeem_channels:
        redeem_channels = ["online"]
    return redeem_channels

def extract_coupon(clean_text):
    code_match = re.search(r'קוד קופון[א-ת\s]*:?\s*([a-zA-Z0-9]{4,})', clean_text)
    return code_match.group(1) if code_match else None

def parse_discount_logic(clean_text, title):
    logic = {
        "condition": {"type": "min_quantity", "value": 1},
        "reward": {"type": "percentage_off", "value": 0.0},
        "constraints": {}
    }

    # Type E: Spend & Save / Tiered Amount (e.g., Terminal X 50 off 250)
    if re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?(?:ברכישת|בקניית|מעל).*?(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', clean_text):
        match_ils = re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?(?:ברכישת|בקניית|מעל).*?(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', clean_text)
        logic["condition"] = {"type": "min_spend", "value": int(match_ils.group(2).replace(",", ""))}
        logic["reward"] = {"type": "fixed_discount_amount", "value": int(match_ils.group(1).replace(",", ""))}
        
        # Additional constraint: If it specifies a max discount
        max_discount = re.search(r'עד\s*(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', clean_text)
        if max_discount:
            logic["constraints"]["max_discount_amount"] = int(max_discount.group(1).replace(",", ""))

    # Type F: Classic Percentage Off (Fallback)
    elif '%' in title:
        match_percent = re.search(r'(\d+)%', title)
        if match_percent:
            logic["condition"] = {"type": "min_quantity", "value": 1}
            logic["reward"] = {"type": "percentage_off", "value": int(match_percent.group(1)) / 100.0}
        else:
            return None
    else:
        return None

    return logic

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

def extract_store_url_from_script(script_text):
    if not script_text:
        return None
    try:
        start_idx = script_text.find('dxpSelector.ctaData=')
        if start_idx != -1:
            array_str = script_text[start_idx:].split('dxpSelector.ctaData=')[1]
            end_idx = array_str.find('dxpSelector.actionList')
            if end_idx != -1:
                array_str = array_str[:end_idx].strip()
            
            array_str = array_str.rstrip(';, \n')
            cta_data = json.loads(array_str)
            
            for group in cta_data:
                for cta in group.get('ctaList', []):
                    if 'לאתר' in cta.get('text', ''):
                        return cta.get('href')
    except Exception:
        pass
    return None

def extract_store_url_from_modal(modal):
    if modal:
        for a_tag in modal.find_all('a', href=True):
            href = a_tag['href']
            if "javascript" not in href.lower() and ".pdf" not in href.lower() and "mastercard" not in href.lower():
                return href
    return None

def scrape_dxp_fast(url):
    print(f"Fetching URL via Requests: {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, impersonate="chrome120")
    response.raise_for_status()

    response.encoding = 'utf-8'

    print("Compiling final JSON data from HTML...")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    categories = extract_real_categories(soup)
    current_category = None
    
    dxp_blocks = soup.find_all('dxp-content-item')
    print(f"Found {len(dxp_blocks)} offer blocks.")
    
    final_discounts = []
    idx = 0
    now = datetime.utcnow()
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    current_year = now.year
    current_month = now.month
    valid_from_str = f"{current_year}-{current_month:02d}-10T00:00:00Z"
    valid_until_str = f"{current_year}-{current_month:02d}-10T23:59:59Z"
    valid_date_only = f"{current_year}-{current_month:02d}-10"
    
    for el in soup.find_all(True):
        if el.name == "div" and el.get("id") in categories:
            current_category = el.get("id")
            continue
            
        if el.name == "dxp-content-item":
            block = el
            try:
                raw_description_html = block.get('description')
                if not raw_description_html: continue
                
                raw_text = BeautifulSoup(raw_description_html, 'html.parser').get_text(separator=' ', strip=True)
                clean_text = raw_text.replace('\xa0', ' ').replace('\u200e', '').replace('\u200f', '').replace('\u202a', '').replace('\u202b', '')
                
                store_url = None
                modal_id = None
                img_src = block.get('src')
                if img_src and not img_src.startswith("http"):
                    img_src = f"https://www.mastercard.co.il{img_src if img_src.startswith('/') else '/' + img_src}"
                
                script_tag = block.find('script')
                if script_tag and script_tag.string:
                    modal_match = re.search(r'"modal-target"\s*:\s*"([^"]+)"', script_tag.string)
                    if modal_match:
                        modal_id = modal_match.group(1)
                    store_url = extract_store_url_from_script(script_tag.string)

                if not store_url and modal_id:
                    modal = soup.find('dxp-modal', {'modal-id': modal_id})
                    store_url = extract_store_url_from_modal(modal)

                terms_text = extract_modal_text(modal_id, soup)
                
                title = extract_title(clean_text)
                logic = parse_discount_logic(clean_text, title)
                if logic is None:
                    continue

                coupon = extract_coupon(clean_text)
                is_stackable = check_stackable(clean_text)
                redeem_channels = extract_redeem_channels(clean_text)
                store_id_safe = normalize_store(modal_id or title) or f"store_mc_{idx:02d}"

                constraints = {
                    "max_discount_amount": logic["constraints"].get("max_discount_amount"),
                    "max_monthly_spend_limit": None,
                    "max_vouchers_per_transaction": None,
                    "club_members_only": True,
                    "requires_specific_credit_card": True,
                    "not_valid_with_other_promotions": not is_stackable,
                    "usage_limit_per_user": 1
                }

                mapped_discount = {
                    "_id": str(uuid.uuid4()),
                    "source_id": "src_mastercard_day",
                    "external_id": modal_id or f"mc_dxp_{idx:02d}",
                    "store_id": store_id_safe,
                    "club_id": "mastercard",
                    "category_id": current_category,
                    "product_id": None,

                    "title": title,  
                    "description": clean_text,
                    "terms_and_conditions": terms_text,

                    "store_url": store_url,
                    "benefit_url": URL,
                    "image_url": img_src,

                    "trigger_type": "coupon" if coupon else "auto",
                    "coupon_code": coupon,

                    "condition": logic["condition"],
                    "reward": logic["reward"],

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

                    "constraints": constraints,

                    "status": "active",
                    "scraped_at": now_iso,
                    "last_seen_at": now_iso,
                    "created_at": now_iso,
                    "updated_at": now_iso
                }
                
                final_discounts.append(mapped_discount)
                idx += 1
                
            except Exception as e:
                print(f"Skipping block {idx} due to error: {e}")
                idx += 1

    return final_discounts

if __name__ == "__main__":
    try:
        scraped_data = scrape_dxp_fast(URL)
        print("\n" + "="*40 + "\nCOMPLETED. FINALIZING OUTPUT\n" + "="*40 + "\n")
        
        with open("mastercard_discounts.json", "w", encoding="utf8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully scraped {len(scraped_data)} discounts!")
        
    except Exception as e:
        print(f"Critical error during scraping process: {e}")
