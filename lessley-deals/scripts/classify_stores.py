"""
Manual MCC classification for Israeli stores.
Rule-based: keyword matching on name + URL domain patterns.
Run: python scripts/classify_stores.py [--dry-run] [--limit N]
"""
from __future__ import annotations
import json, re, sys, argparse
from pathlib import Path

# ── MCC rule engine ──────────────────────────────────────────────────────────

def classify(name: str, url: str | None) -> tuple[list[int], str, str]:
    """Return (mcc_codes, official_name, confidence)."""
    n = name.lower().strip()
    u = (url or "").lower()
    dom = re.sub(r"https?://(www\.)?", "", u).split("/")[0]  # e.g. ksp.co.il

    # ── BRAND / DOMAIN exact lookups ─────────────────────────────────────────
    brand_map: dict[str, tuple[list[int], str, str]] = {
        # ── Electronics / Computers ──
        "ksp": ([5732, 5734], "KSP", "HIGH"),
        "ksp.co.il": ([5732, 5734], "KSP", "HIGH"),
        "easytech": ([5734, 5732], "Easy Tech", "HIGH"),
        "easytech.co.il": ([5734, 5732], "Easy Tech", "HIGH"),
        "ctop": ([5734, 5732], "C-TOP", "HIGH"),
        "ctop.co.il": ([5734, 5732], "C-TOP", "HIGH"),
        "itoutlet": ([5734, 5732], "IT Outlet", "HIGH"),
        "itoutlet.co.il": ([5734, 5732], "IT Outlet", "HIGH"),
        "m2-pc": ([5734, 5732], "M2 Computers", "HIGH"),
        "m2-pc.co.il": ([5734, 5732], "M2 Computers", "HIGH"),
        "sel.co.il": ([5732, 5734], "Sirius Electronics", "HIGH"),
        "lenovo": ([5734, 5732, 5045], "Lenovo", "HIGH"),
        "lytrade.co.il": ([5734, 5045], "Lenovo Israel", "HIGH"),
        "xiaomi": ([5732, 5734], "Xiaomi", "HIGH"),
        "anker": ([5732, 5734], "Anker", "HIGH"),
        "bissell": ([5722, 5732], "Bissell", "HIGH"),
        "bissell-il.co.il": ([5722, 5732], "Bissell", "HIGH"),
        "kidiwatch": ([5732, 5945], "KiDi Watch", "HIGH"),
        "kidiwatch.co.il": ([5732, 5945], "KiDi Watch", "HIGH"),
        "nycharger": ([5732, 5734], "NY Charger", "HIGH"),
        "nycharger.co.il": ([5732, 5734], "NY Charger", "HIGH"),
        "rakhashmal.co.il": ([5065, 5732], "Rakhashmal", "HIGH"),
        "smartwallaby": ([5734, 5732], "Smart Wallaby", "HIGH"),
        "smartwallaby.co.il": ([5734, 5732], "Smart Wallaby", "HIGH"),
        "walty": ([5732, 5734], "Walty", "HIGH"),
        "walty.co.il": ([5732, 5734], "Walty", "HIGH"),
        "tweaky": ([5734, 5732], "Tweaky", "MEDIUM"),

        # ── Fashion / Clothing ──
        "terminal x": ([5651, 5699], "Terminal X", "HIGH"),
        "terminalx": ([5651, 5699], "Terminal X", "HIGH"),
        "fox": ([5651, 5699], "FOX", "HIGH"),
        "foxhome": ([5719, 5712], "FOX Home", "HIGH"),
        "foxhome.co.il": ([5719, 5712], "FOX Home", "HIGH"),
        "renuar": ([5651, 5699], "Renuar", "HIGH"),
        "golf": ([5651, 5699], "Golf", "HIGH"),
        "golf kids": ([5641, 5651], "Golf Kids", "HIGH"),
        "golf&co": ([5651, 5699], "Golf & Co", "HIGH"),
        "polgat": ([5651, 5699], "Polgat", "HIGH"),
        "billabong": ([5651, 5941], "Billabong", "HIGH"),
        "american eagle": ([5651, 5699], "American Eagle", "HIGH"),
        "the children's place": ([5641, 5651], "The Children's Place", "HIGH"),
        "flying tiger": ([5947, 5999], "Flying Tiger", "HIGH"),
        "foot locker": ([5661, 5941], "Foot Locker", "HIGH"),
        "mango": ([5651, 5699], "Mango", "HIGH"),
        "kenneth cole": ([5651, 5661], "Kenneth Cole", "HIGH"),
        "reserved": ([5651, 5699], "Reserved", "HIGH"),
        "lee jeans": ([5651, 5699], "Lee Jeans", "HIGH"),
        "wrangler": ([5651, 5699], "Wrangler", "HIGH"),
        "new era": ([5651, 5699], "New Era", "HIGH"),
        "karen millen": ([5651, 5699], "Karen Millen", "HIGH"),
        "michael kors": ([5651, 5699], "Michael Kors", "HIGH"),
        "siksilk": ([5651, 5699], "SikSilk", "HIGH"),
        "cupshe": ([5651, 5699], "Cupshe", "HIGH"),
        "zaful": ([5651, 5699], "Zaful", "HIGH"),
        "newchic": ([5651, 5699], "NewChic", "HIGH"),
        "chicme": ([5651, 5699], "ChicMe", "HIGH"),
        "rotita": ([5651, 5699], "Rotita", "HIGH"),
        "dresslily": ([5651, 5699], "DressLily", "HIGH"),
        "rosewe": ([5651, 5699], "Rosewe", "HIGH"),
        "modlily": ([5651, 5699], "Modlily", "HIGH"),
        "lilicloth": ([5651, 5699], "LiliCloth", "HIGH"),
        "cotosen": ([5651, 5699], "Cotosen", "HIGH"),
        "tfnc london": ([5651, 5699], "TFNC London", "HIGH"),
        "amiclubwear": ([5651, 5699], "AMIClubwear", "HIGH"),
        "tbdress": ([5651, 5699], "TBDress", "HIGH"),
        "ericdress": ([5651, 5699], "EricDress", "HIGH"),
        "j.ing": ([5651, 5699], "J.ING", "HIGH"),
        "just fashion now": ([5651, 5699], "Just Fashion Now", "HIGH"),
        "stylewe": ([5651, 5699], "StyleWe", "HIGH"),
        "milanoo": ([5651, 5699], "Milanoo", "HIGH"),
        "casetify": ([5732, 5699], "Casetify", "HIGH"),
        "carter's": ([5641, 5651], "Carter's", "HIGH"),
        "patpat": ([5641, 5651], "PatPat", "HIGH"),
        "mania jeans": ([5651, 5699], "Mania Jeans", "HIGH"),
        "intima": ([5651, 5699], "Intima", "HIGH"),
        "spiral direct": ([5651, 5699], "Spiral Direct", "HIGH"),
        "techwear club": ([5651, 5699], "Techwear Club", "HIGH"),
        "leonisa": ([5651, 5699], "Leonisa", "HIGH"),
        "modibodi": ([5651, 5699], "Modibodi", "HIGH"),
        "urban": ([5651, 5699], "Urban", "MEDIUM"),
        "coggles": ([5651, 5699], "Coggles", "HIGH"),
        "onlys": ([5651, 5699], "Onlys", "HIGH"),
        "kahol lavan": ([5651, 5699], "Kahol Lavan", "HIGH"),
        "ivory": ([5651, 5699], "Ivory", "MEDIUM"),
        "skechers": ([5661, 5941], "Skechers", "HIGH"),
        "shoes online": ([5661, 5699], "Shoes Online", "HIGH"),
        "vivaia": ([5661, 5699], "Vivaia", "HIGH"),
        "wigsbuy": ([5699, 5977], "WigsBuy", "HIGH"),
        "shein": ([5651, 5699], "Shein", "HIGH"),
        "asos": ([5651, 5699], "ASOS", "HIGH"),
        "shopbop": ([5651, 5699], "Shopbop", "HIGH"),
        "ador": ([5651, 5699], "Ador", "MEDIUM"),
        "dyn store": ([5651, 5699], "Dyn Store", "MEDIUM"),
        "weshoes": ([5661, 5699], "WeShoes", "HIGH"),
        "pandazzz": ([5651, 5699], "Pandazzz", "MEDIUM"),
        "whatwears": ([5651, 5699], "WhatWears", "HIGH"),

        # ── Shoes ──
        "comfort shoes": ([5661, 5999], "Comfort Shoes", "MEDIUM"),
        "public desire": ([5661, 5699], "Public Desire", "HIGH"),
        "foot steps": ([5661, 5999], "Foot Steps", "MEDIUM"),
        "ronarifashion.com": ([5651, 5699], "Ronari Fashion", "HIGH"),

        # ── Sportswear / Sport ──
        "adidas": ([5941, 5661, 5651], "Adidas", "HIGH"),
        "nike": ([5941, 5661, 5651], "Nike", "HIGH"),
        "adidas.co.il": ([5941, 5661, 5651], "Adidas", "HIGH"),
        "morie": ([5651, 5699], "Morie Swimwear", "HIGH"),
        "morie.co.il": ([5651, 5699], "Morie Swimwear", "HIGH"),
        "epsportwear": ([5651, 5941], "EP Sportwear", "HIGH"),
        "epsportwear.co.il": ([5651, 5941], "EP Sportwear", "HIGH"),
        "eurosport": ([5941, 5651], "Eurosport", "HIGH"),
        "kaitz activewear": ([5651, 5941], "Kaitz Activewear", "MEDIUM"),
        "myprotein": ([5941, 5912], "MyProtein", "HIGH"),
        "myvitamins": ([5912, 5999], "MyVitamins", "HIGH"),
        "exante": ([5912, 5999], "Exante", "HIGH"),
        "idealfit": ([5941, 5912], "IdealFit", "HIGH"),
        "vitacost": ([5912, 5999], "Vitacost", "HIGH"),
        "proteinunicorn": ([5912, 5941], "Protein Unicorn", "HIGH"),
        "proteinunicorn.com": ([5912, 5941], "Protein Unicorn", "HIGH"),
        "strongful": ([5941, 5999], "Strongful", "MEDIUM"),
        "sportal": ([5941, 5651], "Sportal", "MEDIUM"),
        "sporter": ([5941, 5651], "Sporter", "MEDIUM"),

        # ── Cosmetics / Beauty ──
        "laline": ([5977, 5999], "Laline", "HIGH"),
        "laline.com": ([5977, 5999], "Laline", "HIGH"),
        "sabon": ([5977, 5999], "Sabon", "HIGH"),
        "bath & body works": ([5977, 5999], "Bath & Body Works", "HIGH"),
        "bodyshop": ([5977, 5999], "The Body Shop", "HIGH"),
        "bodyshop.co.il": ([5977, 5999], "The Body Shop", "HIGH"),
        "body shop the secrets of nature": ([5977, 5999], "The Body Shop", "HIGH"),
        "revolution beauty": ([5977, 5999], "Revolution Beauty", "HIGH"),
        "illamasqua": ([5977, 5999], "Illamasqua", "HIGH"),
        "lookfantastic": ([5977, 5999], "LookFantastic", "HIGH"),
        "hqhair": ([5977, 5999], "HQhair", "HIGH"),
        "strawberrynet": ([5977, 5999], "Strawberrynet", "HIGH"),
        "strawberrynet.com": ([5977, 5999], "Strawberrynet", "HIGH"),
        "cult beauty": ([5977, 5999], "Cult Beauty", "HIGH"),
        "space nk": ([5977, 5999], "Space NK", "HIGH"),
        "grow gorgeous": ([5977, 5999], "Grow Gorgeous", "HIGH"),
        "zest beauty": ([5977, 5999], "Zest Beauty", "MEDIUM"),
        "beautiful style": ([5977, 5999], "Beautiful Style", "MEDIUM"),
        "makeup eraser": ([5977, 5999], "MakeUp Eraser", "HIGH"),
        "annzi beauty": ([5977, 5999], "Annzi Beauty", "MEDIUM"),
        "redefine hair": ([5977, 7230], "Redefine Hair", "MEDIUM"),
        "amika": ([5977, 7230], "Amika", "HIGH"),
        "eyeko uk": ([5977, 5999], "Eyeko", "HIGH"),
        "lady makeup": ([5977, 5999], "Lady Makeup", "MEDIUM"),
        "kamedis": ([5912, 5977], "Kamedis", "HIGH"),
        "sea of spa": ([5977, 7299], "Sea of Spa", "HIGH"),
        "seaofspa.com": ([5977, 7299], "Sea of Spa", "HIGH"),
        "botanifique": ([5977, 5999], "Botanifique", "HIGH"),
        "botanifique.co.il": ([5977, 5999], "Botanifique", "HIGH"),
        "nasoprofumo": ([5977, 5999], "Nasoprofumo", "HIGH"),
        "nasoprofumo.com": ([5977, 5999], "Nasoprofumo", "HIGH"),
        "fragrancex": ([5977, 5999], "FragranceX", "HIGH"),
        "the perfume spot": ([5977, 5999], "The Perfume Spot", "HIGH"),
        "musk oud perfumes": ([5977, 5999], "Musk Oud Perfumes", "MEDIUM"),
        "oliere paris": ([5977, 5999], "Oliere Paris", "MEDIUM"),
        "afrodita": ([5977, 5999], "Afrodita", "MEDIUM"),
        "afrodita.co.il": ([5977, 5999], "Afrodita", "MEDIUM"),
        "aromantica": ([5977, 5999], "Aromantica", "HIGH"),
        "aromantica.co.il": ([5977, 5999], "Aromantica", "HIGH"),
        "pelebeauty": ([5977, 7230], "Pele Beauty", "HIGH"),
        "pelebeauty.com": ([5977, 7230], "Pele Beauty", "HIGH"),
        "atlas beauty": ([5977, 7230], "Atlas Beauty", "HIGH"),
        "ry-beauty.co.il": ([5977, 7230], "Atlas Beauty", "HIGH"),
        "la mirage cosmetics": ([5977, 5999], "La Mirage Cosmetics", "MEDIUM"),
        "beautyplace": ([5977, 5999], "Beauty Place", "MEDIUM"),
        "miri lev": ([5977, 7230], "Miri Lev", "MEDIUM"),
        "liron olga hedi": ([5977, 7230], "Liron Olga Hedi", "MEDIUM"),
        "hofit קוסמטיקה": ([5977, 5999], "Hofit Cosmetics", "MEDIUM"),
        "dalal cosmetics": ([5977, 5999], "Dalal Cosmetics", "MEDIUM"),
        "pele shine": ([5977, 7230], "Pele Shine", "HIGH"),
        "peleshine.com": ([5977, 7230], "Pele Shine", "HIGH"),
        "noa kirel": ([5977, 5999], "Noa Kirel", "HIGH"),

        # ── Pharma / Health ──
        "super pharm": ([5912, 5999], "Super-Pharm", "HIGH"),
        "סופר פארמ": ([5912, 5999], "Super-Pharm", "HIGH"),
        "good pharm": ([5912, 5999], "Good Pharm", "HIGH"),
        "mds pharm": ([5912, 5999], "MDS Pharm", "HIGH"),
        "dr pharm": ([5912, 5999], "Dr Pharm", "HIGH"),
        "dr gav": ([8099, 5912], "Dr. Gav", "MEDIUM"),
        "norton": ([5734, 7372], "Norton", "HIGH"),
        "avg": ([5734, 7372], "AVG", "HIGH"),
        "nordvpn": ([7372, 5734], "NordVPN", "HIGH"),
        "surfshark": ([7372, 5734], "Surfshark", "HIGH"),
        "qustodio": ([7372, 5734], "Qustodio", "HIGH"),
        "namecheap": ([7372, 5734], "Namecheap", "HIGH"),
        "godaddy": ([7372, 5734], "GoDaddy", "HIGH"),

        # ── Travel / Hotels ──
        "booking": ([4722, 7011], "Booking.com", "HIGH"),
        "agoda": ([7011, 4722], "Agoda", "HIGH"),
        "expedia": ([4722, 7011], "Expedia", "HIGH"),
        "hotels": ([7011, 4722], "Hotels.com", "HIGH"),
        "isrotel": ([7011, 4722], "Isrotel", "HIGH"),
        "hotel4u": ([4722, 7011], "Hotel4U", "HIGH"),
        "lastminute": ([4722, 7011], "LastMinute", "HIGH"),
        "edreams": ([4722, 7011], "eDreams", "HIGH"),
        "esky": ([4722, 7011], "Esky", "HIGH"),
        "cheaptickets": ([4722, 7011], "CheapTickets", "HIGH"),
        "economybookings": ([4722, 7011], "EconomyBookings", "HIGH"),
        "reservations": ([4722, 7011], "Reservations.com", "HIGH"),
        "orbitz": ([4722, 7011], "Orbitz", "HIGH"),
        "vrbo": ([4722, 7011], "VRBO", "HIGH"),
        "walla tours": ([4722, 7011], "Walla Tours", "HIGH"),
        "shilav": ([4722, 7011], "Shilav", "HIGH"),
        "trip": ([4722, 7011], "Trip.com", "HIGH"),
        "kiwi": ([4511, 4722], "Kiwi.com", "HIGH"),
        "omio": ([4722, 4511], "Omio", "HIGH"),
        "esim fly": ([4814, 4511], "eSIM Fly", "HIGH"),
        "esimple": ([4814, 4511], "eSIMple", "HIGH"),
        "wifly": ([4814, 4511], "WiFly", "HIGH"),
        "discover cars": ([7512, 4722], "Discover Cars", "HIGH"),
        "myrentacar": ([7512, 4722], "MyRentaCar", "HIGH"),
        "holiday autos": ([7512, 4722], "Holiday Autos", "HIGH"),
        "europcar": ([7512, 4722], "Europcar", "HIGH"),
        "qeeq": ([7512, 4722], "QEEQ", "HIGH"),
        "get your guide": ([7999, 4722], "GetYourGuide", "HIGH"),
        "viator": ([7999, 4722], "Viator", "HIGH"),
        "klook": ([7999, 4722], "Klook", "HIGH"),
        "tiqets": ([7999, 4722], "Tiqets", "HIGH"),
        "go city": ([7999, 4722], "Go City", "HIGH"),
        "kkday": ([7999, 4722], "KKday", "HIGH"),
        "airhelp": ([4511, 7299], "AirHelp", "HIGH"),
        "hoppa": ([4722, 7512], "Hoppa", "HIGH"),
        "eurowings": ([4511, 4722], "Eurowings", "HIGH"),
        "mona tours": ([4722, 7011], "Mona Tours", "MEDIUM"),
        "geshertours": ([4722, 7999], "Tiyulei Gesher", "HIGH"),
        "geshertours.co.il": ([4722, 7999], "Tiyulei Gesher", "HIGH"),
        "caminos": ([4722, 7999], "Caminos", "HIGH"),
        "caminos.co.il": ([4722, 7999], "Caminos", "HIGH"),
        "genesis-tours": ([4722, 7999], "Genesis Tours", "HIGH"),
        "genesis-tours.co.il": ([4722, 7999], "Genesis Tours", "HIGH"),
        "luna tours": ([4722, 7999], "Luna Tours", "MEDIUM"),
        "rider.travel": ([4722, 7011], "Rider 21", "HIGH"),
        "altos.co.il": ([4722, 7999], "Al Tours", "HIGH"),
        "israelunlimited": ([4722, 7999], "Israel Unlimited", "HIGH"),
        "milanuno": ([4722, 7999], "Milanuno", "HIGH"),
        "milanuno.co.il": ([4722, 7999], "Milanuno", "HIGH"),
        "brownhotels": ([7011, 4722], "Brown Hotels", "HIGH"),
        "brownhotels.com": ([7011, 4722], "Brown Hotels", "HIGH"),
        "vistaeilat": ([7011, 4722], "Hotel Vista Eilat", "HIGH"),
        "vistaeilat.co.il": ([7011, 4722], "Hotel Vista Eilat", "HIGH"),
        "shenkinhotel": ([7011, 4722], "Hotel Shenkin", "HIGH"),
        "shenkinhotel.co.il": ([7011, 4722], "Hotel Shenkin", "HIGH"),
        "shefhotel": ([7011, 4722], "Hotel Shefayim", "HIGH"),
        "shefhotel.co.il": ([7011, 4722], "Hotel Shefayim", "HIGH"),
        "soleil-eilathotel": ([7011, 4722], "Canada Israel Hotels", "HIGH"),
        "soleil-eilathotel.co.il": ([7011, 4722], "Canada Israel Hotels", "HIGH"),
        "davidsharphotels": ([7011, 4722], "David Sharp Hotels", "HIGH"),
        "davidsharphotels.com": ([7011, 4722], "David Sharp Hotels", "HIGH"),
        "sea-hotel": ([7011, 4722], "Sea Executive Suites", "HIGH"),
        "sea-hotel.co.il": ([7011, 4722], "Sea Executive Suites", "HIGH"),
        "ultra-hotels": ([7011, 4722], "Ultra Hotel", "HIGH"),
        "ultra-hotels.com": ([7011, 4722], "Ultra Hotel", "HIGH"),
        "roxonhotels": ([7011, 7298], "Roxon Urban Spa Hotel", "HIGH"),
        "roxonhotels.co.il": ([7011, 7298], "Roxon Urban Spa Hotel", "HIGH"),
        "kfarkinneret": ([7011, 7032], "Kfar Hanofesh Dariya", "HIGH"),
        "kfarkinneret.co.il": ([7011, 7032], "Kfar Hanofesh Dariya", "HIGH"),
        "ella eilat": ([7011, 4722], "Ella Eilat", "HIGH"),
        "ellasun.co.il": ([7011, 4722], "Ella Eilat Villas", "HIGH"),
        "fogolapark": ([7996, 7999], "Fogo La Park", "HIGH"),
        "fogolapark.com": ([7996, 7999], "Fogo La Park", "HIGH"),
        "babylonpark": ([7996, 7999], "Babylon Park", "HIGH"),
        "babylonpark.co.il": ([7996, 7999], "Babylon Park", "HIGH"),

        # ── Food Delivery ──
        "wolt": ([5812, 7299], "Wolt", "HIGH"),
        "mishloha": ([5812, 7299], "Mishloha", "HIGH"),
        "mishloha.co.il": ([5812, 7299], "Mishloha", "HIGH"),
        "10bis": ([5812, 7299], "10bis", "HIGH"),
        "spicesonline": ([5812, 5999], "Spices", "HIGH"),
        "spicesonline.co.il": ([5812, 5999], "Spices", "HIGH"),
        "4chef": ([5812, 5999], "4Chef", "HIGH"),
        "4שף": ([5812, 5999], "4Chef", "HIGH"),

        # ── Restaurants (known chains) ──
        "dominos": ([5812, 5814], "Domino's", "HIGH"),
        "domino's": ([5812, 5814], "Domino's", "HIGH"),
        "burger station": ([5812, 5814], "Burger Station", "HIGH"),
        "אצה": ([5812, 5814], "Atza Sushi", "HIGH"),
        "רשת אצה": ([5812, 5814], "Atza Sushi", "HIGH"),
        "sushi": ([5812, 5814], "Sushi", "MEDIUM"),
        "pizza": ([5812, 5814], "Pizza", "MEDIUM"),
        "yummi": ([5812, 5814], "Yummi", "HIGH"),
        "yummi.co.il": ([5812, 5814], "Yummi", "HIGH"),
        "dosabar": ([5812, 5814], "Dosa Bar", "HIGH"),
        "dosabar.co.il": ([5812, 5814], "Dosa Bar", "HIGH"),
        "pokebar": ([5812, 5814], "Poke Bar", "HIGH"),
        "pokebar.co.il": ([5812, 5814], "Poke Bar", "HIGH"),
        "chopchop": ([5812, 5814], "Chop Chop", "HIGH"),
        "chopchop.co.il": ([5812, 5814], "Chop Chop", "HIGH"),
        "chikenpoint": ([5812, 5814], "Chicken Point", "HIGH"),
        "chikenpoint.co.il": ([5812, 5814], "Chicken Point", "HIGH"),
        "extreme-pizza": ([5812, 5814], "Extreme Pizza", "HIGH"),
        "extreme-pizza.co.il": ([5812, 5814], "Extreme Pizza", "HIGH"),
        "pizza-story": ([5812, 5814], "Pizza Story", "HIGH"),
        "pizza-story.co.il": ([5812, 5814], "Pizza Story", "HIGH"),
        "pizza-baleno": ([5812, 5814], "Pizza Baleno", "HIGH"),
        "pizza-baleno.co.il": ([5812, 5814], "Pizza Baleno", "HIGH"),
        "moryopizza": ([5812, 5814], "Moryo Pizza", "HIGH"),
        "moryopizza.co.il": ([5812, 5814], "Moryo Pizza", "HIGH"),
        "haflaa": ([5812, 5813], "Hafla", "HIGH"),
        "haflaa.co.il": ([5812, 5813], "Hafla", "HIGH"),
        "zaafran": ([5812, 5814], "Zaafran", "HIGH"),
        "zaafran.co.il": ([5812, 5814], "Zaafran", "HIGH"),
        "moses": ([5812, 5813], "Moses", "HIGH"),
        "mosesrest.co.il": ([5812, 5813], "Moses", "HIGH"),
        "mulhaagam": ([5812, 5813], "Mul HaAgam", "HIGH"),
        "mulhaagam.co.il": ([5812, 5813], "Mul HaAgam", "HIGH"),
        "bologna": ([5812, 5813], "Bologna", "HIGH"),
        "bologna.co.il": ([5812, 5813], "Bologna", "HIGH"),
        "memphis": ([5812, 5813], "Memphis", "HIGH"),
        "memphis.co.il": ([5812, 5813], "Memphis", "HIGH"),
        "schnitzlan": ([5812, 5814], "Schnitzelan", "HIGH"),
        "schnitzlan.co.il": ([5812, 5814], "Schnitzelan", "HIGH"),
        "wokaway": ([5812, 5814], "Wok Away", "HIGH"),
        "wokaway.co.il": ([5812, 5814], "Wok Away", "HIGH"),
        "gregcafe": ([5812, 5813], "Greg Cafe", "HIGH"),
        "gregcafe.co.il": ([5812, 5813], "Greg Cafe", "HIGH"),
        "beginscoffee": ([5812, 5813], "Begins Coffee", "HIGH"),
        "beginscoffee.co.il": ([5812, 5813], "Begins Coffee", "HIGH"),
        "thai-time": ([5812, 7298], "Thai Time", "HIGH"),
        "thai-time.co.il": ([5812, 7298], "Thai Time", "HIGH"),
        "foodboutique": ([5812, 5814], "Sushi Boutique", "HIGH"),
        "foodboutique.co.il": ([5812, 5814], "Sushi Boutique", "HIGH"),
        "mevashlim": ([5812, 7999], "Mevashlim Experience", "HIGH"),
        "mevashlim.co.il": ([5812, 7999], "Mevashlim Experience", "HIGH"),
        "granitegourmet": ([5812, 5813], "Granite Gourmet", "HIGH"),
        "granitegourmet.co.il": ([5812, 5813], "Granite Gourmet", "HIGH"),
        "pastoralgroup": ([5812, 5813], "Pastoral", "HIGH"),
        "pastoralgroup.co.il": ([5812, 5813], "Pastoral", "HIGH"),
        "hazangehalim": ([5812, 5813], "Hazan Gehalim", "HIGH"),
        "hazangehalim.com": ([5812, 5813], "Hazan Gehalim", "HIGH"),
        "lollip": ([5812, 5945], "Lollip", "HIGH"),
        "lollip.co.il": ([5812, 5945], "Lollip", "HIGH"),
        "chocolat": ([5812, 5441], "Chocolati", "HIGH"),
        "chocolat.co.il": ([5812, 5441], "Chocolati", "HIGH"),
        "shuk-daniela": ([5812, 7299], "Spa Daniela", "HIGH"),
        "shuk-daniela.co.il": ([7298, 5812], "Spa Daniela", "HIGH"),

        # ── Grocery / Supermarket ──
        "shufersal": ([5411, 5310], "Shufersal", "HIGH"),
        "victory": ([5411, 5310], "Victory", "HIGH"),
        "ויקטורי": ([5411, 5310], "Victory", "HIGH"),
        "tiv taam": ([5411, 5812], "Tiv Taam", "HIGH"),
        "טיב טעם": ([5411, 5812], "Tiv Taam", "HIGH"),
        "zer4u": ([5411, 5310], "Zer4U", "HIGH"),
        "gali": ([5310, 5411], "Gali", "HIGH"),
        "mega sport": ([5941, 5310], "Mega Sport", "HIGH"),
        "מגה ספורט": ([5941, 5310], "Mega Sport", "HIGH"),
        "extra retail": ([5311, 5310], "Extra Retail", "HIGH"),
        "אקסטרה ריטייל": ([5311, 5310], "Extra Retail", "HIGH"),
        "home center": ([5251, 5719], "Home Center", "HIGH"),
        "ace": ([5251, 5261], "ACE", "HIGH"),
        "סנו": ([5411, 5999], "Sano", "HIGH"),
        "mamamarket": ([5411, 5999], "Mama Market", "HIGH"),
        "mamamarket.co.il": ([5411, 5999], "Mama Market", "HIGH"),
        "gvinotberamot": ([5411, 5812], "Gvinot Beramot", "HIGH"),
        "gvinotberamot.co.il": ([5411, 5812], "Gvinot Beramot", "HIGH"),

        # ── Discount / Variety ──
        "חצי חינמ": ([5310, 5999], "Hatzi Hinam", "HIGH"),
        "הסטוק": ([5310, 5999], "HaStock", "HIGH"),
        "stock-home": ([5310, 5719], "Stock Home", "HIGH"),
        "stock-home.co.il": ([5310, 5719], "Stock Home", "HIGH"),
        "sodo stream": ([5722, 5999], "SodaStream", "HIGH"),
        "sodestream": ([5722, 5999], "SodaStream", "HIGH"),
        "sodastream": ([5722, 5999], "SodaStream", "HIGH"),
        "sodastream.co.il": ([5722, 5999], "SodaStream", "HIGH"),
        "temu": ([5310, 5999], "Temu", "HIGH"),
        "alibaba": ([5310, 5999], "Alibaba", "HIGH"),
        "ebay": ([5999, 5310], "eBay", "HIGH"),
        "etsy": ([5947, 5999], "Etsy", "HIGH"),
        "banggood": ([5732, 5999], "Banggood", "HIGH"),
        "geekbuying": ([5732, 5999], "GeekBuying", "HIGH"),
        "tomtop": ([5732, 5999], "TomTop", "HIGH"),
        "tvc mall": ([5732, 5999], "TVC Mall", "HIGH"),
        "joom": ([5999, 5310], "Joom", "HIGH"),
        "sunsky": ([5732, 5999], "Sunsky", "HIGH"),
        "giztop": ([5732, 5999], "GizTop", "HIGH"),
        "ghgate": ([5732, 5999], "GHGate", "HIGH"),
        "chinavasion": ([5732, 5999], "Chinavasion", "HIGH"),
        "opensky": ([5999, 5310], "OpenSky", "HIGH"),
        "peggybuy": ([5999, 5310], "PeggyBuy", "HIGH"),
        "365mashbir": ([5311, 5310], "365 Mashbir", "HIGH"),
        "bit2hul": ([5310, 5999], "Bit2Hul", "HIGH"),
        "hacontainer": ([5310, 5719], "HaContainer", "HIGH"),
        "hacontainer.co.il": ([5310, 5719], "HaContainer", "HIGH"),

        # ── Furniture / Home ──
        "damir": ([5712, 5719], "Damir Furniture", "HIGH"),
        "damir.co.il": ([5712, 5719], "Damir Furniture", "HIGH"),
        "buycarpet": ([5713, 5719], "BuyCarpet", "HIGH"),
        "buycarpet.co.il": ([5713, 5719], "BuyCarpet", "HIGH"),
        "vardinon": ([5719, 5712], "Vardinon", "HIGH"),
        "homeat": ([5719, 5712], "Homeat", "HIGH"),
        "homeat.co.il": ([5719, 5712], "Homeat", "HIGH"),
        "yldesign": ([5712, 5719], "Y.L Design", "HIGH"),
        "yldesign.co.il": ([5712, 5719], "Y.L Design", "HIGH"),
        "hogacarpets": ([5713, 5719], "Hoga Carpets", "HIGH"),
        "hogacarpets.com": ([5713, 5719], "Hoga Carpets", "HIGH"),
        "carmelfloor": ([5713, 5719], "Carmel Floor", "HIGH"),
        "carmelfloor.co.il": ([5713, 5719], "Carmel Floor", "HIGH"),
        "olimpiya": ([5712, 5719], "Olympia Furniture", "HIGH"),
        "olimpiya.co.il": ([5712, 5719], "Olympia Furniture", "HIGH"),
        "balance-israel": ([5712, 5719], "Balance Furniture", "HIGH"),
        "balance-israel.com": ([5712, 5719], "Balance Furniture", "HIGH"),
        "rehinet": ([5712, 5719], "Rehitov", "HIGH"),
        "rehinet.co.il": ([5712, 5719], "Rehitov", "HIGH"),
        "etz-alon": ([5712, 5999], "Etz Alon", "HIGH"),
        "etz-alon.co.il": ([5712, 5999], "Etz Alon", "HIGH"),
        "octostyle": ([5712, 5999], "Octo Style", "HIGH"),
        "octostyle.co.il": ([5712, 5999], "Octo Style", "HIGH"),
        "kashtyparketim": ([5713, 5719], "Kashti Parquet", "HIGH"),
        "kashtyparketim.co.il": ([5713, 5719], "Kashti Parquet", "HIGH"),
        "daliadrapes": ([5719, 5999], "Dalia Drapes", "HIGH"),
        "daliadrapes.co.il": ([5719, 5999], "Dalia Drapes", "HIGH"),
        "bia homedesign": ([5712, 5719], "Bia Home Design", "MEDIUM"),
        "house design": ([5712, 5719], "House Design", "MEDIUM"),
        "art home": ([5712, 5719], "Art Home", "MEDIUM"),
        "keter": ([5999, 5712], "Keter", "HIGH"),

        # ── Toys / Kids ──
        "toysrus": ([5945, 5999], "Toys R Us", "HIGH"),
        "toy store": ([5945, 5999], "Toy Store", "HIGH"),
        "toystore.co.il": ([5945, 5999], "Toy Store", "HIGH"),
        "american toys": ([5945, 5999], "American Toys", "HIGH"),
        "super toys": ([5945, 5999], "Super Toys", "HIGH"),
        "toys4us": ([5945, 5999], "Toys 4 Us", "HIGH"),
        "toys4us.co.il": ([5945, 5999], "Toys 4 Us", "HIGH"),
        "bubybloom": ([5641, 5945], "Buby Bloom", "HIGH"),
        "bubybloom.co.il": ([5641, 5945], "Buby Bloom", "HIGH"),
        "fixt": ([5945, 5947], "Fixt", "HIGH"),
        "fixt.co.il": ([5945, 5947], "Fixt", "HIGH"),
        "my toy": ([5945, 5999], "My Toy", "MEDIUM"),
        "agalease-baby": ([5641, 5945], "Agalease Baby", "HIGH"),
        "agalease-baby.co.il": ([5641, 5945], "Agalease Baby", "HIGH"),
        "my 1st years": ([5641, 5945], "My 1st Years", "HIGH"),
        "elysiumbaby": ([5641, 5945], "Elysium Baby", "HIGH"),
        "elysiumbaby.com": ([5641, 5945], "Elysium Baby", "HIGH"),
        "mon-bebe": ([5641, 5945], "Mon Bebe", "HIGH"),
        "mon-bebe.co.il": ([5641, 5945], "Mon Bebe", "HIGH"),
        "bigidea": ([7999, 5945], "Big Idea", "HIGH"),
        "bigidea.co.il": ([7999, 5945], "Big Idea", "HIGH"),
        "novakid": ([8299, 7999], "Novakid", "HIGH"),
        "futurelearn": ([8299, 7999], "FutureLearn", "HIGH"),
        "tutorials point": ([8299, 7999], "Tutorials Point", "HIGH"),
        "udemy": ([8299, 7999], "Udemy", "HIGH"),
        "preply": ([8299, 7999], "Preply", "HIGH"),
        "anglitlaam": ([8299, 7999], "Anglit LaAm", "HIGH"),
        "anglitlaam.com": ([8299, 7999], "Anglit LaAm", "HIGH"),
        "speax": ([8299, 7999], "Speax English", "HIGH"),
        "speax.co.il": ([8299, 7999], "Speax English", "HIGH"),
        "justmusic": ([7929, 8299], "Just Music Academy", "HIGH"),
        "justmusic.co.il": ([7929, 8299], "Just Music Academy", "HIGH"),
        "music-retreat": ([7929, 7999], "Music Retreat", "HIGH"),
        "music-retreat.com": ([7929, 7999], "Music Retreat", "HIGH"),
        "bigzolfreegluten": ([5411, 5999], "Big Zol Free Gluten", "HIGH"),
        "bigzolfreegluten.com": ([5411, 5999], "Big Zol Free Gluten", "HIGH"),
        "lovimals": ([5995, 742], "Lovimals", "HIGH"),
        "morsdogs": ([5995, 742], "Mors Dogs", "HIGH"),
        "morsdogs.com": ([5995, 742], "Mors Dogs", "HIGH"),

        # ── Jewelry ──
        "marina-jewelry": ([5944, 5999], "Marina Jewelry", "HIGH"),
        "marina-jewelry.com": ([5944, 5999], "Marina Jewelry", "HIGH"),
        "goldiam": ([5944, 5999], "Goldiam", "HIGH"),
        "goldiam.co.il": ([5944, 5999], "Goldiam", "HIGH"),
        "italo jewerly": ([5944, 5999], "Italo Jewelry", "HIGH"),
        "the jewel hut": ([5944, 5999], "The Jewel Hut", "HIGH"),
        "argento": ([5944, 5999], "Argento", "HIGH"),
        "bijou jewelry": ([5944, 5999], "Bijou Jewelry", "MEDIUM"),
        "hadasgross": ([5944, 5999], "Hadas Gross Jewelry", "HIGH"),
        "hadasgross.com": ([5944, 5999], "Hadas Gross Jewelry", "HIGH"),
        "edelshteinjewelry": ([5944, 5999], "Edelshtein Jewelry", "HIGH"),
        "edelshteinjewelry.com": ([5944, 5999], "Edelshtein Jewelry", "HIGH"),
        "feranya": ([5944, 5999], "Feranya Jewelry", "HIGH"),
        "feranya.com": ([5944, 5999], "Feranya Jewelry", "HIGH"),

        # ── Optics ──
        "dr-sherman": ([8042, 5999], "Dr. Sherman Optics", "HIGH"),
        "dr-sherman.co.il": ([8042, 5999], "Dr. Sherman Optics", "HIGH"),
        "smartbuyglasses": ([8042, 5999], "SmartBuyGlasses", "HIGH"),
        "vision direct": ([8042, 5999], "Vision Direct", "HIGH"),
        "glasseslit": ([8042, 5999], "GlassesLit", "HIGH"),
        "i-optic": ([8042, 5999], "I-Optic", "HIGH"),

        # ── Books ──
        "צומת ספרים": ([5942, 5945], "Tzomet Sfarim", "HIGH"),
        "wordery": ([5942, 5999], "Wordery", "HIGH"),
        "better world books": ([5942, 5999], "Better World Books", "HIGH"),
        "abebooks": ([5942, 5999], "AbeBooks", "HIGH"),
        "תלתנ ספרימ": ([5942, 5999], "Taltanim Books", "HIGH"),

        # ── Gifts / Novelty ──
        "gifta": ([5947, 5999], "Gifta", "HIGH"),
        "gift-presentation": ([5947, 5999], "Gifta", "HIGH"),
        "gift-presentation.com": ([5947, 5999], "Gifta", "HIGH"),
        "junes מתנות": ([5947, 5999], "Junes Gifts", "MEDIUM"),
        "chesem": ([5947, 5999], "Chesem", "HIGH"),
        "chemp.co.il": ([5947, 5999], "Champ Gifts", "HIGH"),
        "maaraz": ([5947, 5999], "Maaraz", "HIGH"),
        "maaraz.com": ([5947, 5999], "Maaraz", "HIGH"),
        "photo-gift": ([5947, 7395], "Photo Gift", "HIGH"),
        "photo-gift.co.il": ([5947, 7395], "Photo Gift", "HIGH"),

        # ── Auto ──
        "adi-system": ([5533, 5732], "Adi Systems", "HIGH"),
        "adi-system.co.il": ([5533, 5732], "Adi Systems", "HIGH"),
        "carpix": ([7542, 7531], "Carpix", "HIGH"),
        "carpix.co.il": ([7542, 7531], "Carpix", "HIGH"),
        "britax": ([5533, 5641], "Britax", "HIGH"),
        "britax.co.il": ([5533, 5641], "Britax", "HIGH"),
        "4x4u": ([5533, 5571], "4X4U", "HIGH"),
        "4x4u.co.il": ([5533, 5571], "4X4U", "HIGH"),
        "autodepot": ([5533, 5531], "AutoDepot", "HIGH"),
        "motorshop": ([5571, 5533], "Motor Shop", "HIGH"),
        "motorshop.co.il": ([5571, 5533], "Motor Shop", "HIGH"),
        "porazany": ([5511, 5521], "Nissan Porazany", "HIGH"),
        "porazany.co.il": ([5511, 5521], "Nissan Porazany", "HIGH"),
        "admotorsport": ([5533, 7999], "AD Motorsport", "HIGH"),
        "admotorsport.co.il": ([5533, 7999], "AD Motorsport", "HIGH"),
        "adirgalgalim": ([7538, 5533], "Adir Galgalim", "HIGH"),
        "adirgalgalim.co.il": ([7538, 5533], "Adir Galgalim", "HIGH"),
        "tal-limousine": ([4111, 7512], "Tal Limousine", "HIGH"),
        "tal-limousine.com": ([4111, 7512], "Tal Limousine", "HIGH"),

        # ── Health / Wellness ──
        "wellnessclinic": ([8099, 7298], "Wellness Clinic", "HIGH"),
        "wellnessclinic.co.il": ([8099, 7298], "Wellness Clinic", "HIGH"),
        "minus417": ([5977, 7298], "Minus 417", "HIGH"),
        "minus417.com": ([5977, 7298], "Minus 417", "HIGH"),
        "taburit": ([8099, 5999], "Taburit", "HIGH"),
        "taburit.co.il": ([8099, 5999], "Taburit", "HIGH"),
        "maagal-haim": ([8099, 7298], "Maagal Haim", "HIGH"),
        "maagal-haim.com": ([8099, 7298], "Maagal Haim", "HIGH"),
        "breeut-pinuk": ([7298, 8099], "Breeut Pinuk", "HIGH"),
        "breeut-pinuk.com": ([7298, 8099], "Breeut Pinuk", "HIGH"),
        "urban-spa": ([7298, 7999], "Urban Spa TLV", "HIGH"),
        "urban-spa.co.il": ([7298, 7999], "Urban Spa TLV", "HIGH"),
        "raindropspa": ([7298, 7999], "Rain Drop Spa", "HIGH"),
        "raindropspa.co.il": ([7298, 7999], "Rain Drop Spa", "HIGH"),
        "dr-la": ([8099, 7298], "Dr. LA Aesthetics", "HIGH"),
        "dr-la.co.il": ([8099, 7298], "Dr. LA Aesthetics", "HIGH"),
        "topaznoy": ([8099, 7298], "Topaz Noy Aesthetic", "HIGH"),
        "topaznoy.co.il": ([8099, 7298], "Topaz Noy Aesthetic", "HIGH"),
        "faceitdg": ([8099, 7298], "FaceIt Clinic", "HIGH"),
        "faceitdg.co.il": ([8099, 7298], "FaceIt Clinic", "HIGH"),
        "hilaser": ([8099, 7298], "Hi Laser", "HIGH"),
        "hilaser.ngf.co.il": ([8099, 7298], "Hi Laser", "HIGH"),
        "laserstreet": ([8099, 7298], "Laser Street", "HIGH"),
        "laserstreet.co.il": ([8099, 7298], "Laser Street", "HIGH"),
        "holderdent": ([8021, 8099], "Dr. Holder Dental", "HIGH"),
        "holderdent.com": ([8021, 8099], "Dr. Holder Dental", "HIGH"),
        "mident4u": ([8021, 8099], "MiDent", "HIGH"),
        "mident4u.com": ([8021, 8099], "MiDent", "HIGH"),
        "hasan-garage": ([7538, 5533], "Hasan Garage", "HIGH"),
        "nutritionist": ([8099, 5912], "Nutritionist", "MEDIUM"),
        "dietamir": ([8099, 5912], "Diet Amir", "HIGH"),
        "dietamir.co.il": ([8099, 5912], "Diet Amir", "HIGH"),
        "heli-group": ([8099, 5912], "Heli Diet", "HIGH"),
        "heli-group.co.il": ([8099, 5912], "Heli Diet", "HIGH"),

        # ── Flowers / Plants ──
        "lovenroses": ([5992, 5999], "Love and Roses", "HIGH"),
        "lovenroses.co.il": ([5992, 5999], "Love and Roses", "HIGH"),
        "kflowers": ([5992, 5999], "K-Flowers", "HIGH"),
        "kflowers.co.il": ([5992, 5999], "K-Flowers", "HIGH"),
        "flowers-katzrin": ([5992, 5999], "Flowers Katzrin", "HIGH"),
        "flowers-katzrin.co.il": ([5992, 5999], "Flowers Katzrin", "HIGH"),
        "binibouquet": ([5992, 5999], "Bini Bouquet", "HIGH"),
        "binibouquet.com": ([5992, 5999], "Bini Bouquet", "HIGH"),
        "organicrishpon": ([5261, 5411], "Organic Rishpon", "HIGH"),
        "organicrishpon.com": ([5261, 5411], "Organic Rishpon", "HIGH"),
        "flowernet": ([5992, 5999], "Flowernet", "HIGH"),
        "plant it": ([5261, 5992], "Plant It", "MEDIUM"),

        # ── Printing / Signage ──
        "dfusoutlet": ([7338, 5999], "Dfus Outlet", "HIGH"),
        "dfusoutlet.co.il": ([7338, 5999], "Dfus Outlet", "HIGH"),
        "net-print": ([7338, 5999], "Net Print", "HIGH"),
        "net-print.co.il": ([7338, 5999], "Net Print", "HIGH"),
        "tamuzline": ([7338, 5999], "Tamuzline", "HIGH"),
        "tamuzline.co.il": ([7338, 5999], "Tamuzline", "HIGH"),
        "asigraf": ([7338, 5999], "Asi Graf", "HIGH"),
        "asigraf.co.il": ([7338, 5999], "Asi Graf", "HIGH"),
        "alegraf": ([7338, 5999], "Alegraf", "HIGH"),
        "alegraf.co.il": ([7338, 5999], "Alegraf Signage", "HIGH"),
        "alegra.co.il": ([7338, 5999], "Alegra Signage", "HIGH"),
        "hanin": ([7338, 5999], "Hanin Print", "HIGH"),
        "hanin.co.il": ([7338, 5999], "Hanin Print", "HIGH"),
        "kesemdigital": ([7338, 5999], "Kesem Digital", "HIGH"),
        "kesemdigital.com": ([7338, 5999], "Kesem Digital", "HIGH"),
        "levi-mp": ([7311, 5999], "Levi Promotions", "HIGH"),
        "levi-mp.co.il": ([7311, 5999], "Levi Promotions", "HIGH"),

        # ── Building / Hardware ──
        "michlol": ([5251, 5065], "Michlol 2000", "HIGH"),
        "michlol.co.il": ([5251, 5065], "Michlol 2000", "HIGH"),
        "electra-air": ([5722, 1711], "Electra Air Conditioning", "HIGH"),
        "electra-air.co.il": ([5722, 1711], "Electra Air Conditioning", "HIGH"),
        "aresco": ([5065, 5999], "Aresco EV", "HIGH"),
        "aresco.co.il": ([5065, 5999], "Aresco EV", "HIGH"),
        "venta": ([5722, 5065], "Venta", "HIGH"),
        "venta.co.il": ([5722, 5065], "Venta", "HIGH"),
        "3dstep": ([5999, 7372], "3DStep", "HIGH"),
        "3dstep.co.il": ([5999, 7372], "3DStep", "HIGH"),

        # ── Laundry / Cleaning ──
        "buotlaundry": ([7211, 7299], "Buot Laundry", "HIGH"),
        "buotlaundry.com": ([7211, 7299], "Buot Laundry", "HIGH"),
        "goldiclean": ([7211, 7216], "Goldi Clean", "HIGH"),
        "goldiclean.co.il": ([7211, 7216], "Goldi Clean", "HIGH"),
        "touchonline": ([5999, 7216], "Touch Cleaning", "HIGH"),
        "touchonline.co.il": ([5999, 7216], "Touch Cleaning", "HIGH"),

        # ── Sports / Fitness ──
        "reform": ([7997, 7299], "Reform Pilates", "HIGH"),
        "reform.co.il": ([7997, 7299], "Reform Pilates", "HIGH"),
        "zionapilates": ([7997, 7299], "Tziona Fitness", "HIGH"),
        "zionapilates.co.il": ([7997, 7299], "Tziona Fitness", "HIGH"),
        "vitkin": ([7997, 7999], "Vitkin Pool", "HIGH"),
        "vitkin.atarix.co.il": ([7997, 7999], "Vitkin Pool", "HIGH"),
        "karate-itkf": ([7999, 7997], "Karate Rokach", "HIGH"),
        "karate-itkf.co.il": ([7999, 7997], "Karate Rokach", "HIGH"),

        # ── Events / Entertainment ──
        "porat-theater": ([7922, 7999], "Porat Theater", "HIGH"),
        "porat-theater.co.il": ([7922, 7999], "Porat Theater", "HIGH"),
        "lev.co.il": ([7832, 7999], "Lev Cinema", "HIGH"),
        "cwc.co.il": ([7832, 7999], "Cinema World", "HIGH"),
        "herzl.org.il": ([7999, 8641], "Herzl Museum", "HIGH"),
        "andalusit": ([7929, 7999], "Andalusian Orchestra", "HIGH"),
        "andalusit.co.il": ([7929, 7999], "Andalusian Orchestra", "HIGH"),
        "davai-group": ([7922, 7999], "Davai Theater", "HIGH"),
        "davai-group.org": ([7922, 7999], "Davai Theater", "HIGH"),
        "suzannedellal": ([7922, 7999], "Suzanne Dellal", "HIGH"),
        "suzannedellal.org.il": ([7922, 7999], "Suzanne Dellal", "HIGH"),
        "ticketmaster": ([7922, 7999], "Ticketmaster", "HIGH"),
        "ticket network": ([7922, 7999], "Ticket Network", "HIGH"),
        "ticket liquidator": ([7922, 7999], "Ticket Liquidator", "HIGH"),
        "viagogo": ([7922, 7999], "Viagogo", "HIGH"),
        "fun": ([7922, 7999], "Fun", "MEDIUM"),
        "g2a": ([5816, 7994], "G2A", "HIGH"),
        "gamersgate": ([5816, 7994], "GamersGate", "HIGH"),
        "green man gaming": ([5816, 7994], "Green Man Gaming", "HIGH"),
        "cdkeys": ([5816, 7994], "CDKeys", "HIGH"),
        "fanatical": ([5816, 7994], "Fanatical", "HIGH"),
        "kinguin": ([5816, 7994], "Kinguin", "HIGH"),
        "just geek": ([5947, 5999], "Just Geek", "HIGH"),
        "halloween costumes": ([5947, 5699], "Halloween Costumes", "HIGH"),

        # ── Telecom ──
        "partner": ([4814, 5732], "Partner", "HIGH"),
        "hot mobile": ([4814, 5732], "HOT Mobile", "HIGH"),
        "icon סלולר": ([4814, 5732], "Icon Cellular", "HIGH"),

        # ── Financial / Other Services ──
        "isracard": ([6300, 6411], "Isracard", "HIGH"),
        "delta": ([4511, 4722], "Delta Airlines", "HIGH"),
        "fiverr": ([7372, 7399], "Fiverr", "HIGH"),
        "wonder share": ([7372, 5734], "Wondershare", "HIGH"),
        "naaman": ([5999, 5947], "Naaman", "HIGH"),
        "jacobi": ([5999, 5411], "Jacobi", "MEDIUM"),
        "gravitee": ([7276, 7399], "Gravitee Tax", "HIGH"),
        "gravitee.co.il": ([7276, 7399], "Gravitee Tax", "HIGH"),
        "rozenfeld": ([5999, 5411], "Rozenfeld", "MEDIUM"),
        "noizz": ([5999, 5651], "Noizz", "MEDIUM"),
        "boomerang": ([7999, 5999], "Boomerang", "MEDIUM"),
        "tracknow": ([7399, 7372], "TrackNow", "MEDIUM"),
        "milega": ([5999, 5310], "Milega", "MEDIUM"),
        "guliver": ([4722, 7011], "Gulliver", "HIGH"),
        "play smart": ([5945, 7999], "Play Smart", "MEDIUM"),

        # ── Bakery specific ──
        "chocolat.co.il": ([5812, 5441], "Chocolati", "HIGH"),
        "ravivsagiv": ([5462, 5999], "Raviv Sagiv Bakery", "HIGH"),
        "ravivsagiv.co.il": ([5462, 5999], "Raviv Sagiv Bakery", "HIGH"),
        "sharon-oats-bakery": ([5462, 5999], "Shibilet HaSharon Bakery", "HIGH"),
        "sharon-oats-bakery.com": ([5462, 5999], "Shibilet HaSharon Bakery", "HIGH"),
        "delapaix": ([5812, 5441], "De La Paix", "HIGH"),
        "delapaix.co.il": ([5812, 5441], "De La Paix", "HIGH"),
        "alma-delice": ([5812, 5441], "Alma Delice", "HIGH"),
        "alma-delice.co.il": ([5812, 5441], "Alma Delice", "HIGH"),
        "thefreshpasta": ([5812, 5411], "Fresh Pasta", "HIGH"),
        "thefreshpasta.co.il": ([5812, 5411], "Fresh Pasta", "HIGH"),

        # ── Misc ──
        "nava": ([5999, 5651], "Nava", "MEDIUM"),
        "mybag": ([5699, 5999], "MyBag", "HIGH"),
        "the luxury closet": ([5699, 5651], "The Luxury Closet", "HIGH"),
        "uniplaces": ([7011, 6513], "Uniplaces", "HIGH"),
        "apartments4you": ([6513, 7011], "Apartments4You", "HIGH"),
        "vrbo.com": ([4722, 7011], "VRBO", "HIGH"),
        "base": ([5651, 5999], "Base", "MEDIUM"),
        "esimo": ([7372, 5999], "Esimo", "MEDIUM"),
        "napo": ([5995, 5999], "Napo", "MEDIUM"),
        "libra": ([5999, 5651], "Libra", "MEDIUM"),
        "panta rei": ([5999, 5651], "Panta Rei", "MEDIUM"),
        "street smart": ([5999, 5651], "Street Smart", "MEDIUM"),
        "afnu": ([5999, 5651], "Afnu", "MEDIUM"),
        "afnu.co.il": ([5999, 5651], "Afnu", "MEDIUM"),
        "dafni": ([5999, 5651], "Dafni", "MEDIUM"),
        "dafni.co": ([5999, 5651], "Dafni", "MEDIUM"),
        "bonauf": ([5999, 5651], "Bonauf", "MEDIUM"),
        "bonauf.co.il": ([5999, 5651], "Bonauf", "MEDIUM"),
        "midrasim.shop": ([5942, 5999], "Midrasim", "HIGH"),
        "botta": ([5661, 5999], "Botta", "MEDIUM"),
        "botta.co.il": ([5661, 5999], "Botta", "MEDIUM"),
        "nimrod": ([5999, 5941], "Nimrod", "MEDIUM"),
        "nimrod.co.il": ([5999, 5941], "Nimrod", "MEDIUM"),
        "star shop": ([5999, 5311], "Star Shop", "MEDIUM"),
        "starshop.co.il": ([5999, 5311], "Star Shop", "MEDIUM"),
        "isrp": ([5999, 5941], "ISRP", "MEDIUM"),
        "isrpstore.com": ([5999, 5941], "ISRP Store", "MEDIUM"),
        "esektools": ([5999, 5251], "Esek Tools", "HIGH"),
        "esektools.com": ([5999, 5251], "Esek Tools", "HIGH"),
        "tami4": ([5722, 5999], "Tami 4", "HIGH"),
        "tami4.co.il": ([5722, 5999], "Tami 4", "HIGH"),
        "arcosteel": ([5251, 5211], "Arcosteel", "MEDIUM"),
        "ve-ahavta": ([8699, 5999], "Ve-Ahavta", "HIGH"),
        "ve-ahavta.co.il": ([8699, 5999], "Ve-Ahavta", "HIGH"),
        "herbology": ([5912, 5999], "Herbology", "HIGH"),
        "herbology.org.il": ([5912, 5999], "Herbology", "HIGH"),
        "technokat": ([5734, 5999], "Technokat", "HIGH"),
        "technokat.shop": ([5734, 5999], "Technokat", "HIGH"),
        "shalhevetlight": ([5065, 5999], "Shalvevet Light", "HIGH"),
        "shalhevetlight.com": ([5065, 5999], "Shalvevet Light", "HIGH"),
        "mataf-kibui": ([5999, 5065], "Lahavot", "HIGH"),
        "mataf-kibui.co.il": ([5999, 5065], "Lahavot", "HIGH"),
        "ashop": ([5732, 5734], "Merkaz HaElectronika", "HIGH"),
        "ashop.co.il": ([5732, 5734], "Merkaz HaElectronika", "HIGH"),
        "dfusoutlet.co.il": ([7338, 5999], "Dfus Outlet", "HIGH"),
        "כלל": ([6300, 6411], "Clal Insurance", "MEDIUM"),
        "shop-lilya": ([5651, 5699], "Lilya", "HIGH"),
        "shop-lilya.co.il": ([5651, 5699], "Lilya", "HIGH"),
        "shilav.co.il": ([4722, 7011], "Shilav", "HIGH"),
        "emilyelodie": ([5651, 5977], "Emily Elodie Paris", "HIGH"),
        "emilyelodie.co.il": ([5651, 5977], "Emily Elodie Paris", "HIGH"),
        "discreet-hila": ([5651, 5699], "Discreet & Hila Fashion", "HIGH"),
        "discreet-hila.co.il": ([5651, 5699], "Discreet & Hila Fashion", "HIGH"),
        "angelina-boutique": ([5651, 5699], "Angelina Boutique", "HIGH"),
        "angelina-boutique.com": ([5651, 5699], "Angelina Boutique", "HIGH"),
        "ronarifashion": ([5651, 5699], "Ronari Fashion", "HIGH"),
        "onlights": ([5065, 5999], "On Lights", "HIGH"),
        "onlights.co.il": ([5065, 5999], "On Lights", "HIGH"),
        "laguna-scent": ([5999, 5947], "Laguna Scent", "HIGH"),
        "laguna-scent.co.il": ([5999, 5947], "Laguna Scent", "HIGH"),
        "propets": ([5995, 742], "Pro Pets", "HIGH"),
        "propets.co.il": ([5995, 742], "Pro Pets", "HIGH"),
        "myzoo": ([5995, 742], "My Zoo", "HIGH"),
        "myzoo.co.il": ([5995, 742], "My Zoo", "HIGH"),
        "petsfood": ([5995, 742], "Pets Food", "HIGH"),
        "petsfood.co.il": ([5995, 742], "Pets Food", "HIGH"),
        "efish": ([5812, 5411], "Efish", "HIGH"),
        "efish.co.il": ([5812, 5411], "Efish", "HIGH"),
        "jerusalem-nanobible": ([5947, 8641], "Jerusalem Nano Bible", "HIGH"),
        "jerusalemnanobible.com": ([5947, 8641], "Jerusalem Nano Bible", "HIGH"),
        "merkazhakdusha": ([5947, 8641], "Merkaz HaKdusha", "HIGH"),
        "merkazhakdusha.co.il": ([5947, 8641], "Merkaz HaKdusha", "HIGH"),
        "mimaamakim-judaica": ([5947, 8641], "Mimaamakim Judaica", "HIGH"),
        "mimaamakim-judaica.co.il": ([5947, 8641], "Mimaamakim Judaica", "HIGH"),
        "bsarig": ([5651, 5944], "Bat Chen Boutique", "HIGH"),
        "bsarig.com": ([5651, 5944], "Bat Chen Boutique", "HIGH"),
        "shilatboutique": ([5651, 5699], "Shilat Boutique", "HIGH"),
        "shilatboutique.com": ([5651, 5699], "Shilat Boutique", "HIGH"),
        "jetlek": ([7534, 5533], "Jetlek", "HIGH"),
        "jetlek.co.il": ([7534, 5533], "Jetlek", "HIGH"),
        "4kdrinks": ([5813, 5812], "4K Drinks", "HIGH"),
        "4kdrinks.shop": ([5813, 5812], "4K Drinks", "HIGH"),
        "wineandfriends": ([5813, 5912], "Wine & Friends", "HIGH"),
        "wineandfriends.co.il": ([5813, 5912], "Wine & Friends", "HIGH"),
        "mizraney-olympia": ([5941, 5999], "Olympia Sports", "HIGH"),
        "mizraney-olympia.co.il": ([5941, 5999], "Olympia Sports", "HIGH"),
        "blackjet": ([7538, 5533], "Black Jet", "HIGH"),
        "blackjet.co.il": ([7538, 5533], "Black Jet", "HIGH"),
        "savak": ([5999, 5251], "Sava", "HIGH"),
        "savak.co.il": ([5999, 5251], "Sava", "HIGH"),
        "darya": ([5699, 5651], "Darya Workwear", "HIGH"),
        "darya.co.il": ([5699, 5651], "Darya Workwear", "HIGH"),
        "camera8200": ([5946, 5732], "Cameras 8200", "HIGH"),
        "camera8200.co.il": ([5946, 5732], "Cameras 8200", "HIGH"),
        "clickit": ([5732, 5734], "Clickit", "HIGH"),
        "clickit.co.il": ([5732, 5734], "Clickit", "HIGH"),
        "sel.co.il": ([5732, 5734], "Sirius Electronics", "HIGH"),
        "marmos": ([5211, 5251], "Marmos Building", "HIGH"),
        "marmos.co.il": ([5211, 5251], "Marmos Building", "HIGH"),
        "kobiatia": ([5947, 5999], "Atia Clocks & Design", "HIGH"),
        "kobiatia.co.il": ([5947, 5999], "Atia Clocks & Design", "HIGH"),
        "diklasartstudio": ([7999, 5999], "Dikla Art Studio", "HIGH"),
        "diklasartstudio.com": ([7999, 5999], "Dikla Art Studio", "HIGH"),
        "antonyoni": ([7999, 5999], "Antoni Art", "HIGH"),
        "antonyoni.com": ([7999, 5999], "Antoni Art", "HIGH"),
        "wood studio": ([5999, 5712], "Wood Studio", "HIGH"),
        "woodstudio.co.il": ([5999, 5712], "Wood Studio", "HIGH"),
        "milanodesign": ([5712, 5719], "Milano Design", "HIGH"),
        "milano-il": ([5712, 5719], "Milano Design", "HIGH"),
        "milano-il.com": ([5712, 5719], "Milano Design", "HIGH"),
        "ruby bay": ([5651, 5699], "Ruby Bay", "MEDIUM"),
        "food appeal": ([5812, 5999], "Food Appeal", "HIGH"),
        "dream card": ([5999, 5947], "Dream Card", "MEDIUM"),
        "בקבוצת golf": ([5651, 5699], "Golf Group", "HIGH"),
        "kingzoo": ([5995, 7999], "King Zoo", "HIGH"),
        "kingzoo.co.il": ([5995, 7999], "King Zoo", "HIGH"),
        "tarbuyotolami": ([7922, 7999], "Tarbuyot Olami", "HIGH"),
        "tarbuyotolami.com": ([7922, 7999], "Tarbuyot Olami", "HIGH"),
        "etl.co.il": ([7399, 7372], "ETL", "HIGH"),
        "vipbengurion": ([4511, 7299], "Aero VIP", "HIGH"),
        "vipbengurion.co.il": ([4511, 7299], "Aero VIP", "HIGH"),
        "afrimoshotelchain": ([7011, 4722], "Africa Israel Hotels", "HIGH"),
        "areen.center": ([7999, 5999], "Areen Center", "HIGH"),
        "tattoomoreno": ([7299, 5999], "Tattoo Moreno", "HIGH"),
        "tattoomoreno.com": ([7299, 5999], "Tattoo Moreno", "HIGH"),
        "nativtattoo": ([7299, 5999], "Nativ Tattoo", "HIGH"),
        "nativtattoo.net": ([7299, 5999], "Nativ Tattoo", "HIGH"),
        "gidatattoo": ([7299, 5999], "Gida Tattoo", "HIGH"),
        "gidatattoo.com": ([7299, 5999], "Gida Tattoo", "HIGH"),
        "bhuka-tours": ([5812, 4722], "Buka Food Tours", "HIGH"),
        "bhuka-tours.com": ([5812, 4722], "Buka Food Tours", "HIGH"),
        "battleblankson": ([5977, 5999], "Batel Blankson Skincare", "MEDIUM"),
        "judithlutvak": ([7011, 5812], "Judith Lutvak B&B", "HIGH"),
        "judithlutvak.co.il": ([7011, 5812], "Judith Lutvak B&B", "HIGH"),
        "irenayofi": ([7230, 5977], "Irena Beauty Salon", "HIGH"),
        "irenayofi.co.il": ([7230, 5977], "Irena Beauty Salon", "HIGH"),
        "shiralle": ([5651, 5699], "Shiralle", "HIGH"),
        "shiralle.com": ([5651, 5699], "Shiralle", "HIGH"),
        "li-la.co.il": ([5651, 5699], "Lila Fashion", "HIGH"),
        "moulindore": ([5812, 5813], "Moulin Dore", "HIGH"),
        "moulindore.co.il": ([5812, 5813], "Moulin Dore", "HIGH"),
        "ronaclogs": ([5661, 5699], "Rona Clogs", "HIGH"),
        "ronaclogs.co.il": ([5661, 5699], "Rona Clogs", "HIGH"),
        "pelle-sg": ([5651, 5699], "Pella Gafni", "HIGH"),
        "pelle-sg.co.il": ([5651, 5699], "Pella Gafni", "HIGH"),
        "ormistika": ([5977, 8641], "Or Mistika", "HIGH"),
        "ormistika.com": ([5977, 8641], "Or Mistika", "HIGH"),
        "maaaz.com": ([5999, 5947], "Maaraz", "HIGH"),
        "loveamika": ([5977, 7230], "Amika Hair", "HIGH"),
        "loveamika.co.il": ([5977, 7230], "Amika Hair", "HIGH"),
        "ceremonietea": ([5812, 5999], "Ceremony Tea", "HIGH"),
        "ceremonietea.co.il": ([5812, 5999], "Ceremony Tea", "HIGH"),
        "sipil.co.il": ([5813, 5912], "The Whisky Embassy", "HIGH"),
        "gabimiara": ([7538, 5533], "Gabi Miara Garage", "HIGH"),
        "gabimiara.com": ([7538, 5533], "Gabi Miara Garage", "HIGH"),
        "hibart": ([7538, 5533], "Hiba Garage", "HIGH"),
        "hibart.co.il": ([7538, 5533], "Hiba Garage", "HIGH"),
        "tamarsys": ([4953, 7399], "Tamar Recycling", "HIGH"),
        "tamarsys.com": ([4953, 7399], "Tamar Recycling", "HIGH"),
        "sfaradimarketing": ([5999, 5999], "Sfaradi Marketing", "MEDIUM"),
        "sfaradimarketing.co.il": ([5999, 5999], "Sfaradi Marketing", "MEDIUM"),
        "online-import": ([5999, 5310], "HaYavan", "HIGH"),
        "online-import.co.il": ([5999, 5310], "HaYavan", "HIGH"),
        "zaafran.co.il": ([5812, 5814], "Zaafran", "HIGH"),
        "mashotim": ([5999, 5941], "Mashotim", "HIGH"),
        "mashotim.co.il": ([5999, 5941], "Mashotim", "HIGH"),
        "bbettere": ([8099, 7298], "Bazalife", "HIGH"),
        "bbettere.com": ([8099, 7298], "Bazalife", "HIGH"),
        "Olympia": ([5941, 5999], "Olympia", "MEDIUM"),
        "mizraney-olympia": ([5941, 5999], "Mizraney Olympia", "HIGH"),
        "la-chocolita": ([5812, 5441], "La Chocolita", "HIGH"),
        "garineiafula": ([5411, 5999], "Garinei Afula Seeds", "HIGH"),
        "garineiafula.co.il": ([5411, 5999], "Garinei Afula Seeds", "HIGH"),
        "ofaimme": ([5261, 5411], "Ofaim Organic", "HIGH"),
        "ofaimme.com": ([5261, 5411], "Ofaim Organic", "HIGH"),
        "mithaberet": ([5999, 7299], "Mithaberet", "HIGH"),
        "mithaberet.co.il": ([5999, 7299], "Mithaberet", "HIGH"),
        "meshekmeller": ([5411, 5261], "Meshek Meller", "HIGH"),
        "meshekmeller.co.il": ([5411, 5261], "Meshek Meller", "HIGH"),
        "bumpersisrael": ([5661, 5999], "Bumpers", "HIGH"),
        "bumpersisrael.com": ([5661, 5999], "Bumpers", "HIGH"),
        "yael-fruits": ([5411, 5261], "Yael Fruits", "HIGH"),
        "yael-fruits.co.il": ([5411, 5261], "Yael Fruits", "HIGH"),
        "trigon-yam": ([5065, 5999], "Trigon Lighting", "HIGH"),
        "trigon-yam.com": ([5065, 5999], "Trigon Lighting", "HIGH"),
        "source-israel": ([5661, 5999], "Sandali Shoresh", "HIGH"),
        "source-israel.co.il": ([5661, 5999], "Sandali Shoresh", "HIGH"),
        "super-front-natanya": ([5411, 5999], "Super Front", "HIGH"),
        "super-front-natanya.co.il": ([5411, 5999], "Super Front", "HIGH"),
        "morie.co.il": ([5651, 5699], "Morie Swimwear", "HIGH"),
        "etzhachaim.co.il": ([5912, 5999], "Etz HaChaim Health", "HIGH"),
        "etzhachaim": ([5912, 5999], "Etz HaChaim Health", "HIGH"),
        "dr-yakubov-julien": ([8021, 8099], "Dental Clinic", "HIGH"),
        "dr-yakubov-julien.com": ([8021, 8099], "Dental Clinic", "HIGH"),
        "kaktusashdod": ([5999, 5812], "Cactus Ashdod", "HIGH"),
        "kaktusashdod.co.il": ([5999, 5812], "Cactus Ashdod", "HIGH"),
        "oyy.co.il": ([5999, 5651], "Vapartzta", "HIGH"),
        "michlol.co.il": ([5251, 5065], "Michlol 2000", "HIGH"),
    }

    # check exact name match
    result = brand_map.get(n)
    if result:
        return result

    # check domain match
    if dom:
        result = brand_map.get(dom)
        if result:
            return result
        # bare domain without extension
        dom_bare = dom.split(".")[0]
        result = brand_map.get(dom_bare)
        if result:
            return result

    # ── KEYWORD RULES (order matters — most specific first) ─────────────────

    # Dental
    if any(k in n for k in ["שיניים", "שיניימ", "דנטל", "dental", "dent ", "dentist", "ortho", "אורתו"]):
        return [8021, 8099], name.strip(), "HIGH"

    # Doctor / Medical Clinic
    if any(k in n for k in ["מרפאה", "מרפאת", "קליניק", "clinic", "רפואה", "רפואת", "medical", "ד\"ר", "dr ", "doctor"]):
        if any(k in n for k in ["שיניים", "שיניימ", "dental", "dent"]):
            return [8021, 8099], name.strip(), "HIGH"
        if any(k in n for k in ["וטרינר", "vet", "חיות"]):
            return [742, 8099], name.strip(), "HIGH"
        if any(k in n for k in ["יופי", "אסתטיק", "לייזר", "beauty", "aesthetic", "laser"]):
            return [8099, 7298], name.strip(), "HIGH"
        return [8099, 8011], name.strip(), "HIGH"

    # Hospital / Health service
    if any(k in n for k in ["בית חולים", "hospital"]):
        return [8062, 8099], name.strip(), "HIGH"

    # Pharmacy
    if any(k in n for k in ["בית מרקחת", "פארמ", "pharm", "apteka"]):
        return [5912, 5999], name.strip(), "HIGH"

    # Veterinary
    if any(k in n for k in ["וטרינר", "veterinar", "vet "]):
        return [742, 8099], name.strip(), "HIGH"

    # Hotels
    if any(k in n for k in ["מלון", "hotel", "hostel", "מוטל", "motel", "resort", "suite", "בוטיק אחסון", "וילות", "בית הארחה", "צימר", "נופש"]):
        if any(k in n for k in ["ספא", "spa"]):
            return [7011, 7298], name.strip(), "HIGH"
        return [7011, 4722], name.strip(), "HIGH"

    # Travel agencies
    if any(k in n for k in ["סוכנות נסיעות", "תיירות", "טיולים", "טיולי", "tours", "tour ", "טורס", "נסיעות"]):
        return [4722, 7999], name.strip(), "HIGH"

    # Airlines
    if any(k in n for k in ["airline", "airways", "aviation", "flight", "טיסה"]):
        return [4511, 4722], name.strip(), "HIGH"

    # eSIM / Telecom
    if any(k in n for k in ["esim", "eSIM"]):
        return [4814, 4511], name.strip(), "HIGH"

    # Restaurant / Food (specific)
    if any(k in n for k in ["פיצה", "pizza", "פיצריה"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["שווארמה", "שיפוד", "shawarma", "grill", "גריל", "על האש", "גחלים"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["המבורגר", "burger", "בורגר"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["סושי", "sushi", "ווק", "wok"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["פלאפל", "falafel", "חומוס", "hummus", "humus"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["שניצל", "schnitzel"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["מסעדה", "מסעדת", "restaurant", "gourmet", "bistro"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["קייטרינג", "catering"]):
        return [5812, 7299], name.strip(), "HIGH"
    if any(k in n for k in ["בית קפה", "קפה ", "coffee", "cafe", "caffee", "קפי", "אספרסו", "espresso"]):
        return [5812, 5813], name.strip(), "HIGH"
    if any(k in n for k in ["בר ", "bar ", " bar", "lounge", "לאונג'"]):
        if any(k in n for k in ["יין", "wine", "wine", "ויסקי", "whisky", "beer", "בירה", "אלכוהול"]):
            return [5813, 5812], name.strip(), "HIGH"
        return [5812, 5813], name.strip(), "HIGH"
    if any(k in n for k in ["סנדביץ", "sandwich", "sandwich", "סנדוויץ", "סנדויץ"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["בורקס"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["מאפייה", "מאפיית", "bakery", "לחם", "bread", "אחסנת", "בייקרי"]):
        return [5462, 5812], name.strip(), "HIGH"
    if any(k in n for k in ["גלידה", "גלידריה", "ice cream", "frozen yogurt", "frozen"]):
        return [5812, 5814], name.strip(), "HIGH"
    if any(k in n for k in ["ממתקים", "ממתקי", "candy", "sweet", "chocolate", "שוקולד"]):
        return [5812, 5441], name.strip(), "HIGH"
    if any(k in n for k in ["אטליז", "קצביה", "קצבי", "butcher", "meat", "בשר", "עוף"]):
        return [5411, 5812], name.strip(), "HIGH"
    if any(k in n for k in ["דגים", "דגי", "fish", "ים תיכוני", "seafood"]):
        return [5812, 5411], name.strip(), "HIGH"
    if any(k in n for k in ["ירקניה", "פירות וירקות", "ירק ", "greengrocer", "organic"]):
        return [5411, 5261], name.strip(), "HIGH"
    if any(k in n for k in ["גרעינים", "גרעיני", "פיצוח", "seeds", "nuts"]):
        return [5411, 5999], name.strip(), "HIGH"
    if any(k in n for k in ["מינימרקט", "minimarket", "מכולת", "צרכניה", "מרקט", "market", "super ", "סופר "]):
        return [5411, 5999], name.strip(), "HIGH"

    # Alcohol / Drinks
    if any(k in n for k in ["יין", "wine", "winery", "יקב", "whisky", "ויסקי", "ounce", "בר שתייה"]):
        return [5813, 5912], name.strip(), "HIGH"

    # Clothing / Fashion
    if any(k in n for k in ["אופנה", "בגדים", "בגדי", "fashion", "boutique", "בוטיק", "clothing", "apparel"]):
        if any(k in n for k in ["ים", "swim", "beach", "bikini"]):
            return [5651, 5699], name.strip(), "HIGH"
        if any(k in n for k in ["כלה", "bride", "ערב", "evening"]):
            return [5621, 5699], name.strip(), "HIGH"
        if any(k in n for k in ["גברים", "men", "man "]):
            return [5611, 5699], name.strip(), "HIGH"
        if any(k in n for k in ["ילד", "kids", "child", "baby", "תינוק"]):
            return [5641, 5651], name.strip(), "HIGH"
        return [5651, 5699], name.strip(), "HIGH"
    if any(k in n for k in ["נעליים", "נעלי", "shoes", "shoe ", "footwear", "sandal", "boot", "סנדל"]):
        return [5661, 5699], name.strip(), "HIGH"
    if any(k in n for k in ["תיק", "תיקים", "bag ", "bags", "luggage", "מזוודה", "מזוודות"]):
        return [5699, 5947], name.strip(), "HIGH"
    if any(k in n for k in ["ספורטר", "sport", "ספורט"]) and any(k in n for k in ["חנות", "shop", "store"]):
        return [5941, 5651], name.strip(), "HIGH"

    # Electronics
    if any(k in n for k in ["אלקטרוניקה", "electronics", "חשמל", "electrical"]) and not any(k in n for k in ["קבלן", "contractor"]):
        if any(k in n for k in ["מחשב", "computer", "laptop", "סלולר", "phone", "mobile"]):
            return [5734, 5732], name.strip(), "HIGH"
        return [5732, 5065], name.strip(), "HIGH"
    if any(k in n for k in ["מחשב", "computer", "laptop", "pc "]):
        return [5734, 5732], name.strip(), "HIGH"
    if any(k in n for k in ["סלולר", "cellular", "mobile", "phone", "פון", "iphone", "samsung"]):
        return [5732, 4814], name.strip(), "HIGH"
    if any(k in n for k in ["תאורה", "lighting", "light", "לד", "led"]):
        return [5065, 5999], name.strip(), "HIGH"

    # Cosmetics / Beauty salons
    if any(k in n for k in ["קוסמטיקה", "cosmetic", "beauty", "יופי", "ביוטי", "אסתטיקה"]):
        if any(k in n for k in ["מכון", "institute", "קליניק", "clinic", "salon", "מספרה"]):
            return [7298, 7230], name.strip(), "HIGH"
        return [5977, 7230], name.strip(), "HIGH"
    if any(k in n for k in ["מספרה", "hair salon", "עיצוב שיער", "מעצב שיער", "barber", "ספר "]):
        return [7230, 7299], name.strip(), "HIGH"
    if any(k in n for k in ["ציפורניים", "nail", "מניקור", "פדיקור"]):
        return [7230, 7299], name.strip(), "HIGH"
    if any(k in n for k in ["ספא", "spa", "מסאג", "massage", "פמפר"]):
        return [7298, 7299], name.strip(), "HIGH"
    if any(k in n for k in ["פרפומריה", "בושם", "perfume", "fragrance", "parfum"]):
        return [5977, 5999], name.strip(), "HIGH"
    if any(k in n for k in ["לייזר", "laser"]) and any(k in n for k in ["שיער", "עור", "עיצוב"]):
        return [7298, 8099], name.strip(), "HIGH"

    # Jewelry
    if any(k in n for k in ["תכשיטים", "תכשיטי", "jewelry", "jewellery", "זהב", "כסף", "אמרלד", "יהלום", "diamond"]):
        return [5944, 5999], name.strip(), "HIGH"
    if any(k in n for k in ["שעון", "שעונים", "clock", "watch"]):
        return [5944, 5999], name.strip(), "HIGH"

    # Optics
    if any(k in n for k in ["אופטיקה", "optic", "eyeglass", "glasses", "משקפיים", "עינ"]):
        return [8042, 5999], name.strip(), "HIGH"

    # Furniture / Home furnishing
    if any(k in n for k in ["רהיטים", "רהיטי", "furniture", "מזרן", "מזרון", "מזרני", "ספה", "sofa"]):
        return [5712, 5719], name.strip(), "HIGH"
    if any(k in n for k in ["שטיח", "שטיחים", "carpet", "rug", "floor", "פרקט", "parquet"]):
        return [5713, 5719], name.strip(), "HIGH"
    if any(k in n for k in ["וילון", "וילונות", "curtain", "drape"]):
        return [5719, 5999], name.strip(), "HIGH"
    if any(k in n for k in ["ארון", "ארונות", "wardrobe", "closet"]):
        return [5712, 5719], name.strip(), "HIGH"
    if any(k in n for k in ["מטבח", "kitchen"]) and any(k in n for k in ["עיצוב", "design", "מרכז"]):
        return [5712, 5999], name.strip(), "HIGH"
    if any(k in n for k in ["עיצוב הבית", "home design", "home decor", "עיצוב בית", "decor"]):
        return [5719, 5712], name.strip(), "HIGH"

    # Building / Hardware
    if any(k in n for k in ["חומרי בניין", "building materials", "בנין", "בניה"]):
        return [5211, 5251], name.strip(), "HIGH"
    if any(k in n for k in ["כלי עבודה", "tools", "hardware", "חומרה"]):
        return [5251, 5999], name.strip(), "HIGH"
    if any(k in n for k in ["קרמיקה", "ceramic", "tiles", "אריח"]):
        return [5999, 5211], name.strip(), "HIGH"
    if any(k in n for k in ["צבע טרי", "paint", "צבע "]):
        return [5231, 5251], name.strip(), "HIGH"

    # Auto / Garage
    if any(k in n for k in ["מוסך", "garage", "מכונאי", "mechanic"]):
        return [7538, 5533], name.strip(), "HIGH"
    if any(k in n for k in ["שטיפת", "car wash", "wash "]) and any(k in n for k in ["רכב", "מכונית", "car"]):
        return [7542, 7299], name.strip(), "HIGH"
    if any(k in n for k in ["צמיגי", "צמיגים", "tire", "tyre"]):
        return [7534, 5533], name.strip(), "HIGH"
    if any(k in n for k in ["חלפים", "auto parts", "spare parts", "מנוע"]):
        return [5533, 5531], name.strip(), "HIGH"
    if any(k in n for k in ["אביזרי רכב", "car accessories"]):
        return [5533, 5531], name.strip(), "HIGH"
    if any(k in n for k in ["פחחות", "body shop", "צבע לרכב"]):
        return [7531, 7538], name.strip(), "HIGH"
    if any(k in n for k in ["גרר", "נגרר", "towing"]):
        return [7549, 7538], name.strip(), "HIGH"
    if any(k in n for k in ["מיזוג לרכב", "ac car"]):
        return [5533, 7538], name.strip(), "HIGH"
    if any(k in n for k in ["אופנוע", "motorcycle", "bike "]) and not any(k in n for k in ["אופניים"]):
        return [5571, 5533], name.strip(), "HIGH"
    if any(k in n for k in ["אופניים", "bicycle", "bike"]):
        return [5940, 5999], name.strip(), "HIGH"

    # Flowers
    if any(k in n for k in ["פרחים", "פרחי", "flower", "florist", "bouquet", "זר פרחים"]):
        return [5992, 5999], name.strip(), "HIGH"
    if any(k in n for k in ["משתלה", "משתלת", "nursery", "plant"]):
        return [5261, 5992], name.strip(), "HIGH"

    # Pets
    if any(k in n for k in ["חיות מחמד", "pet shop", "pet store", "כלבו לחיות", "עולם החיות"]):
        return [5995, 742], name.strip(), "HIGH"
    if any(k in n for k in ["וטרינר", "veterinar"]):
        return [742, 8099], name.strip(), "HIGH"

    # Books / Libraries
    if any(k in n for k in ["ספריית", "ספרייה", "ספרים", "bookstore", "book store", "library"]):
        return [5942, 5999], name.strip(), "HIGH"

    # Toys
    if any(k in n for k in ["צעצוע", "צעצועים", "toy", "toys", "games", "משחק"]):
        return [5945, 5999], name.strip(), "HIGH"

    # Sports / Fitness
    if any(k in n for k in ["פיטנס", "fitness", "gym ", "ג'ים", "כושר", "pilates", "פילאטיס", "yoga", "יוגה", "crossfit"]):
        return [7997, 7999], name.strip(), "HIGH"
    if any(k in n for k in ["ספורט", "sport"]):
        return [5941, 7997], name.strip(), "HIGH"
    if any(k in n for k in ["קראטה", "karate", "אגרוף", "boxing", "אומנויות לחימה", "martial"]):
        return [7999, 7997], name.strip(), "HIGH"

    # Entertainment / Theater / Cinema
    if any(k in n for k in ["תיאטרון", "theater", "theatre", "cinema", "קולנוע"]):
        return [7922, 7832], name.strip(), "HIGH"
    if any(k in n for k in ["מוסיקה", "music", "להקה", "orchestra", "band "]):
        return [7929, 7999], name.strip(), "HIGH"
    if any(k in n for k in ["גלריה", "gallery", "אמנות", "art studio", "סטודיו"]) and not any(k in n for k in ["שיער", "hair", "קעקוע", "tattoo"]):
        return [5999, 7929], name.strip(), "HIGH"

    # Photography
    if any(k in n for k in ["צילום", "photo", "photography", "photograph"]):
        return [7395, 7999], name.strip(), "HIGH"

    # Printing
    if any(k in n for k in ["דפוס", "printing", "הדפסה"]):
        return [7338, 5999], name.strip(), "HIGH"

    # Laundry / Cleaning
    if any(k in n for k in ["מכבסה", "מכבסת", "laundry", "כביסה", "ניקוי יבש", "dry clean"]):
        return [7211, 7216], name.strip(), "HIGH"
    if any(k in n for k in ["שטיפה", "ניקיון", "cleaning", "clean "]):
        if any(k in n for k in ["רכב", "מכונית", "car"]):
            return [7542, 7299], name.strip(), "HIGH"
        return [7299, 7349], name.strip(), "HIGH"

    # Gifts / Judaica
    if any(k in n for k in ["יודאיקה", "judaica", "תשמישי קדושה", "מזוזה", "ספר תורה"]):
        return [5947, 8641], name.strip(), "HIGH"
    if any(k in n for k in ["מתנות", "מתנה", "gift", "gifts", "souvenir"]):
        return [5947, 5999], name.strip(), "HIGH"

    # Supermarket / grocery
    if any(k in n for k in ["סופר", "supermarket", "grocery"]):
        return [5411, 5999], name.strip(), "HIGH"

    # Security
    if any(k in n for k in ["אבטחה", "security", "מצלמות", "cameras", "מיגון"]):
        return [7382, 5065], name.strip(), "HIGH"

    # Tattoo
    if any(k in n for k in ["קעקוע", "tattoo"]):
        return [7299, 5999], name.strip(), "HIGH"

    # Driving school
    if any(k in n for k in ["בית ספר לנהיגה", "driving school"]):
        return [7999, 8299], name.strip(), "HIGH"

    # Parking
    if any(k in n for k in ["חניון", "parking"]):
        return [7523, 7299], name.strip(), "HIGH"

    # Gas station
    if any(k in n for k in ["תחנת דלק", "דלק", "gas station", "fuel"]):
        return [5541, 5542], name.strip(), "HIGH"

    # Tax / Finance
    if any(k in n for k in ["חזרי מס", "tax ", "מס הכנסה", "ביטוח"]):
        return [7276, 6411], name.strip(), "HIGH"

    # Recycling
    if any(k in n for k in ["מחזור", "recycling"]):
        return [4953, 7399], name.strip(), "HIGH"

    # Software / Digital
    if any(k in n for k in ["software", "digital", "app", "vpn", "antivirus"]):
        return [7372, 5734], name.strip(), "HIGH"

    # Telecom
    if any(k in n for k in ["תקשורת", "telecom", "internet", "network"]) and not any(k in n for k in ["מסעדה", "restaurant"]):
        return [4814, 7372], name.strip(), "HIGH"

    # Health food / nature store
    if any(k in n for k in ["בית טבע", "health food", "טבעוני", "vegan", "אורגני", "organic", "natural"]):
        return [5912, 5411], name.strip(), "HIGH"

    # Default
    return [5999], name.strip(), "LOW"


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--data-dir", default="data")
    args = parser.parse_args()

    stores_path = Path(args.data_dir) / "seed" / "stores.json"
    stores = json.loads(stores_path.read_text(encoding="utf-8"))

    stats = {"classified": 0, "skipped": 0, "total": len(stores)}
    for store in stores:
        meta = store.setdefault("metadata", {})
        if meta.get("mcc_codes"):
            stats["skipped"] += 1
            continue
        if args.limit and stats["classified"] >= args.limit:
            break

        mcc, official, conf = classify(
            store["name"],
            meta.get("store_url"),
        )
        print(f"  {store['name']!r:50s} -> {official!r:45s} mcc={mcc} [{conf}]")

        if not args.dry_run:
            meta["mcc_codes"] = mcc
            meta["official_name"] = official
            meta["mcc_confidence"] = conf
        stats["classified"] += 1

    if not args.dry_run:
        stores_path.write_text(
            json.dumps(stores, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"\nDone. classified={stats['classified']} skipped={stats['skipped']} total={stats['total']}")


if __name__ == "__main__":
    main()
