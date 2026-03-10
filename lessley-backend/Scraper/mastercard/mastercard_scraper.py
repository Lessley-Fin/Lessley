
##################################################################
##################################################################
#working version except of the store_url
##################################################################
##################################################################


#################################################################
# need to add store_id, product_id, club_id, category_code
################################################################

from curl_cffi import requests
#import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# --- SETTINGS & URL ---
URL = "https://www.mastercard.co.il/he-il/personal/offers-and-promotions/mastercard-day.html"

def parse_cleaned_text(clean_text, idx, block, raw_description_html, terms_text, store_link_from_modal):
    """
    Takes cleaned-up Hebrew text, modal data, and maps it to our JSON structure.
    """
    id_date = datetime.now().strftime("%Y%m")
    unique_id = f"mc_dxp_{id_date}_{idx:02d}"

    # 1. Stackability Logic
    if "לא כולל כפל" in clean_text or "ללא כפל" in clean_text:
        is_stackable = False
    else:
        is_stackable = "כפל" in clean_text

    # 2. Merchant Logic
    merchant = "Unknown"
    merchant_regex = r'(?:באתר|בחנויות|בסניפי|באפליקציית)(?:\s+ו?[א-ת]+)?\s+([a-zA-Zא-ת0-9\s&]+?)(?=\.|,|-|תקף|כולל|ללא|לא כולל|בכפוף|\(|$)'
    merchant_match = re.search(merchant_regex, clean_text)
    if merchant_match:
        merchant = merchant_match.group(1).strip()

    # 3. Store URL Logic (We only care about the Store link now, as Terms are scraped)
    store_url = None

    def extract_links_from_soup(soup_obj):
        nonlocal store_url
        for a_tag in soup_obj.find_all('a', href=True):
            link_text = a_tag.get_text(strip=True)
            if 'אתר' in link_text and not store_url:
                if "javascript" not in a_tag['href'].lower():
                    store_url = a_tag['href']

    if raw_description_html:
        desc_soup = BeautifulSoup(raw_description_html, 'html.parser')
        extract_links_from_soup(desc_soup)
    extract_links_from_soup(block)

    if not store_url:
        store_url = block.get('cta-link') or block.get('cta-url') or block.get('primary-cta-link')


    # 4. Build JSON Structure
    discount_obj = {
        "id": unique_id,
        "name": "Unknown Offer",  
        "merchant": merchant,
        "description": clean_text,
        "store_url": store_url,
        "terms_and_conditions": terms_text,
        "rules": {
            "is_stackable": is_stackable,
            "priority": 2, 
            "scope": "cart_level",
            "trigger": "auto",
            "coupon_code": None
        },
        "eligibility": {
            "start_date": f"{datetime.now().year}-{datetime.now().month:02d}-10T00:00:00Z",
            "end_date": f"{datetime.now().year}-{datetime.now().month:02d}-10T23:59:59Z",
            "target_audiences": ["mastercard_holders"]
        },
        "targeting": {
            "applicable_product_ids": ["all"],
            "excluded_product_ids": []
        },
        "condition": {
            "type": "min_quantity",
            "value": 1
        },
        "reward": {
            "type": "percentage_off",
            "value": 0.0
        }
    }

    # 5. Extract Details via Heuristics
    title_match = re.search(r'^(.*?[₪%])(.*?)$', clean_text, re.DOTALL)
    if title_match:
        discount_obj["name"] = title_match.group(1).strip()
        
    match_ils = re.search(r'(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?.*?(?:ברכישת|בקניית|מעל).*?(?:₪\s*)?(\d[,0-9]*)(?:\s*₪)?', clean_text)
    if match_ils:
        discount_obj["reward"]["type"] = "fixed_discount_amount"
        discount_obj["reward"]["value"] = int(match_ils.group(1).replace(",", "")) 
        discount_obj["condition"]["type"] = "min_spend"
        discount_obj["condition"]["value"] = int(match_ils.group(2).replace(",", "")) 
        discount_obj["rules"]["priority"] = 1 
        
    elif '%' in discount_obj["name"]:
        match_percent = re.search(r'(\d+)%', discount_obj["name"])
        if match_percent:
            discount_obj["reward"]["value"] = int(match_percent.group(1)) / 100.0
            
    code_match = re.search(r'קוד קופון[א-ת\s]*:?\s*([a-zA-Z0-9]{4,})', clean_text)
    if code_match:
        discount_obj["rules"]["trigger"] = "coupon"
        discount_obj["rules"]["coupon_code"] = code_match.group(1)

    return discount_obj


def extract_modal_data(modal_id, soup):
    """
    Finds the correct modal by ID and extracts the terms text and store link.
    """
    terms_text = None
    store_link = None
    
    if not modal_id:
        return terms_text, store_link

    # Find the specific modal matching the ID
    modal = soup.find('dxp-modal', {'modal-id': modal_id})
    
    if modal:
        # Extract text, separating paragraphs cleanly
        raw_text = modal.get_text(separator='\n', strip=True)
        terms_text = raw_text.replace('\xa0', ' ').replace('\u200e', '').replace('\u200f', '').replace('\u202a', '').replace('\u202b', '')
        
        # Look for the store link inside the modal
        for a_tag in modal.find_all('a', href=True):
            href = a_tag['href']
            # Ignore PDF links and javascript links
            if "javascript" not in href.lower() and ".pdf" not in href.lower():
                store_link = href
                break # Grab the first valid link

    return terms_text, store_link


def scrape_dxp_fast(url):
    print(f"🚀 Fetching URL via Requests: {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers, impersonate="chrome120")
    response.raise_for_status()

    response.encoding = 'utf-8'

    # --- PARSE AND EXTRACT ---
    print("📝 Compiling final JSON data from HTML...")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 1. Extract all offer blocks
    dxp_blocks = soup.find_all('dxp-content-item')
    print(f"✅ Found {len(dxp_blocks)} offer blocks.")
    
    final_discounts = []
    
    for idx, block in enumerate(dxp_blocks):
        try:
            # 2. Get raw description
            raw_description_html = block.get('description')
            if not raw_description_html: continue
            
            clean_text = BeautifulSoup(raw_description_html, 'html.parser').get_text(separator=' ', strip=True)
            
            # 3. Find the modal ID!
            # The ID is buried inside the ctaData script block. We use regex to find it.
            modal_id = None
            script_tag = block.find('script')
            if script_tag and script_tag.string:
                # Search for "modal-target":"some-id"
                modal_match = re.search(r'"modal-target"\s*:\s*"([^"]+)"', script_tag.string)
                if modal_match:
                    modal_id = modal_match.group(1)

            # 4. Extract data from that specific modal
            terms_text, store_link = extract_modal_data(modal_id, soup)
            
            # 5. Map everything
            mapped_discount = parse_cleaned_text(clean_text, idx, block, raw_description_html, terms_text, store_link)
            final_discounts.append(mapped_discount)
            
        except Exception as e:
            print(f"Skipping block {idx} due to error: {e}")

    return {"discounts": final_discounts}

if __name__ == "__main__":
    try:
        scraped_data = scrape_dxp_fast(URL)
        print("\n" + "="*40 + "\nCOMPLETED. FINALIZING OUTPUT\n" + "="*40 + "\n")
        
        with open("mastercard_discounts.json", "w", encoding="utf8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Successfully scraped {len(scraped_data['discounts'])} discounts!")
        
    except Exception as e:
        print(f"❌ Critical error during scraping process: {e}")