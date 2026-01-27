from playwright.sync_api import sync_playwright
import json, os, re, time
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

HISTORY_FILE = "alcohol_history.json"
CONFIG_FILE = "categories.json"

# Match ml, cl, l, g, kg, tk
UNIT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(ml|cl|l|L|g|kg|tk)")

STORE_MAP = {
    "barbora": "Barbora",
    "selver": "Selver",
    "rimi": "Rimi",
    "coop": "Coop"
}

# ---------------- utilities ----------------
def get_store_name(url):
    domain = urlparse(url).netloc.lower()
    for key, display_name in STORE_MAP.items():
        if key in domain:
            return display_name
    return "Store"

def get_store_from_url(url):
    """Detect store name from URL"""
    if not url:
        return "Unknown"
    url_lower = url.lower()
    if "barbora" in url_lower:
        return "Barbora"
    elif "selver" in url_lower:
        return "Selver"
    elif "rimi" in url_lower:
        return "Rimi"
    elif "coop" in url_lower:
        return "Coop"
    return "Unknown"

def get_category_key(name, url):
    """Generate unique key for a category using store:name format"""
    store = get_store_from_url(url)
    return f"{store}:{name}"

def load_categories():
    """Load config - supports both old dict format and new list format"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Convert old dict format to new list format
        if isinstance(data, dict):
            new_format = []
            for name, info in data.items():
                if isinstance(info, dict):
                    new_format.append({
                        "name": name,
                        "url": info["url"],
                        "unit": info.get("unit", "L")
                    })
                else:
                    new_format.append({
                        "name": name,
                        "url": info,
                        "unit": "L"
                    })
            # Save in new format
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_format, f, indent=2)
            return new_format
        return data
    return []

def extract_unit_value(text, target_type):
    if not text:
        return None
    m = UNIT_RE.search(text)
    if not m:
        return None
    try:
        value = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        if target_type == "L":
            if unit == "ml": return value / 1000
            if unit == "cl": return value / 100
            if unit == "l": return value
        else:
            if unit == "g": return value / 1000
            if unit == "kg": return value
        return value
    except:
        return None

def parse_price(text):
    if not text:
        return 0.0
    m = re.search(r"\d+[.,]?\d*", text)
    return float(m.group(0).replace(",", ".")) if m else 0.0

def construct_page_url(base_url, page_num):
    if page_num == 1:
        return base_url
    u = urlparse(base_url)
    qs = parse_qs(u.query)
    qs["page"] = str(page_num)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, urlencode(qs, doseq=True), u.fragment))

# ---------------- BARBORA (FIXED) ----------------
def scrape_barbora_page(page):
    try:
        page.wait_for_selector(".product-card-next", timeout=7000)
    except:
        pass
    for _ in range(5):
        page.mouse.wheel(0, 3000)
        time.sleep(0.5)
    
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('.product-card-next')).map(card => {
            const link = card.querySelector('a[href*="/toode/"]');
            const titleEl = card.querySelector("span[id*='product-title']");
            
            // FIXED: Extract price from meta tag (most reliable)
            let price = "0";
            const metaPrice = card.querySelector('meta[itemprop="price"]');
            if (metaPrice) {
                price = metaPrice.getAttribute('content');
            } else {
                // Fallback 1: Try new aria-label format (includes "Soodushind" or "Tavahind")
                const priceDiv = card.querySelector('div[aria-label*="Hind:"]');
                if (priceDiv) {
                    const ariaLabel = priceDiv.getAttribute('aria-label');
                    // Extract first price from aria-label like "Soodushind Hind: 1,19€"
                    const match = ariaLabel.match(/Hind:\\s*([0-9,]+)€/);
                    if (match) {
                        price = match[1].replace(',', '.');
                    }
                }
                
                // Fallback 2: Look for promotional price container
                if (price === "0") {
                    const promoContainer = card.querySelector('[data-testid="promoColouredContainer"]');
                    if (promoContainer) {
                        const text = promoContainer.innerText;
                        const match = text.match(/([0-9]+)[.,]([0-9]+)/);
                        if (match) {
                            price = match[1] + '.' + match[2];
                        }
                    }
                }
            }
            
            const unitText = card.querySelector("div.text-2xs")?.innerText;
            
            return {
                name: titleEl ? titleEl.innerText.trim() : (link ? link.innerText.trim() : "Unknown"),
                url: link ? link.href : "",
                img: card.querySelector('img')?.src || "",
                price_text: price,
                unit_text: unitText || ""
            };
        })
    """)

# ---------------- SELVER ----------------
def scrape_selver_page(page):
    try:
        if page.is_visible('button:has-text("Nõustun")'):
            page.click('button:has-text("Nõustun")')
    except:
        pass
    try:
        page.wait_for_selector('.ProductCard__info', timeout=7000)
    except:
        return []
    page.mouse.wheel(0, 2000)
    time.sleep(1)
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('.ProductCard__info')).map(card => {
            const link = card.querySelector('a.ProductCard__link');
            const priceEl = card.querySelector('.ProductPrice');
            const unitEl = card.querySelector('.ProductPrice__unit-price');
            let mainPrice = "0";
            if (priceEl) {
                const clone = priceEl.cloneNode(true);
                const childSpan = clone.querySelector('.ProductPrice__unit-price');
                if(childSpan) childSpan.remove();
                mainPrice = clone.innerText.trim();
            }
            return {
                name: card.querySelector('.ProductCard__title')?.innerText.trim() || "Unknown",
                url: link ? link.href : "",
                img: card.closest('.ProductCard')?.querySelector('img')?.src || "",
                price_text: mainPrice,
                unit_text: unitEl ? unitEl.innerText.trim() : ""
            };
        })
    """)

# ---------------- RIMI (UPDATED FOR SALE PRICES) ----------------
def scrape_rimi_page(page):
    try:
        page.wait_for_selector('.card', state='visible', timeout=20000)
    except:
        print("Rimi: .card not visible")
        return []
    
    # Accept cookies if present
    try:
        if page.is_visible('button:has-text("Nõustu vajalike")', timeout=2000):
            page.click('button:has-text("Nõustu vajalike")')
    except:
        pass
    
    for _ in range(6):
        page.mouse.wheel(0, 2500)
        time.sleep(0.4)
    
    time.sleep(1)
    
    return page.evaluate("""
        () => Array.from(document.querySelectorAll('.card')).map(card => {
            const name = card.querySelector('.card__name')?.innerText.trim() || "Unknown";
            const url = card.querySelector('a')?.href || "";
            const img = card.querySelector('img')?.src || "";
            
            // Check for sale price first (in price-label overlay)
            let price = 0;
            let isSalePrice = false;
            
            const priceLabel = card.querySelector('.price-label__price');
            if (priceLabel) {
                // Sale price exists - extract from major/cents structure
                const major = priceLabel.querySelector('.major')?.innerText.trim() || "0";
                const cents = priceLabel.querySelector('.cents')?.innerText.trim() || "00";
                price = parseFloat(major + "." + cents);
                isSalePrice = true;
            } else {
                // No sale - use regular price from price-tag
                const main = card.querySelector('.price-tag > span')?.innerText.trim().replace(',', '.') || "0";
                const frac = card.querySelector('.price-tag sup')?.innerText.trim() || "00";
                price = parseFloat(main + "." + frac.replace(/\\D/g,'')) || 0;
            }
            
            // Get unit price - try both sale and regular unit price locations
            let unitText = "";
            const saleUnitPrice = card.querySelector('.price-per-unit');
            const regularUnitPrice = card.querySelector('.card__price-per');
            
            if (isSalePrice && saleUnitPrice) {
                unitText = saleUnitPrice.innerText?.replace(/\\s+/g, ' ').trim() || "";
            } else if (regularUnitPrice) {
                unitText = regularUnitPrice.innerText?.replace(/\\s+/g, ' ').trim() || "";
            }
            
            return {
                name,
                url,
                img,
                price_text: price.toString(),
                unit_text: unitText,
                is_sale: isSalePrice
            };
        }).filter(p => p.name && p.price_text !== "0");
    """)

# ---------------- general helpers ----------------
def parse_price_per_unit(text):
    if not text:
        return 0.0
    text = text.strip("() ")
    m = re.search(r"(\d+[.,]\d+)", text)
    if m:
        return float(m.group(1).replace(",", "."))
    return 0.0

# ---------------- main runner ----------------
def run_scraper():
    CATEGORIES = load_categories()
    
    single_category_key = os.environ.get("SCRAPE_SINGLE_CATEGORY")
    if single_category_key:
        matching = [cat for cat in CATEGORIES if get_category_key(cat["name"], cat["url"]) == single_category_key]
        if matching:
            print(f"🎯 Single-category mode: Only scraping '{matching[0]['name']}' from {get_store_from_url(matching[0]['url'])}")
            CATEGORIES = matching
        else:
            print(f"⚠️  Category key '{single_category_key}' not found in config. Skipping.")
            return
    
    with sync_playwright() as p:
        print("Starting browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width":1280, "height":800})
        page = context.new_page()
        
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = {"meta": {}, "products": {}}
        else:
            data = {"meta": {}, "products": {}}
        
        if "products" not in data:
            data["products"] = {}
        
        data["meta"]["generated_at"] = datetime.now().isoformat()
        
        for cat_entry in CATEGORIES:
            cat_name = cat_entry["name"]
            base_url = cat_entry["url"]
            target_unit = cat_entry.get("unit", "L")
            
            category_key = get_category_key(cat_name, base_url)
            store_name = get_store_from_url(base_url)
            
            print(f"\n--- Scanning {cat_name} ({target_unit}) on {store_name} ---")
            
            page_num = 1
            seen_names = set()
            
            while True:
                if store_name == "Barbora":
                    target_url = construct_page_url(base_url, page_num)
                elif store_name == "Selver":
                    target_url = construct_page_url(base_url, page_num)
                elif store_name == "Rimi":
                    if page_num == 1:
                        target_url = base_url
                    else:
                        u = urlparse(base_url)
                        target_url = f"{u.scheme}://{u.netloc}{u.path}?currentPage={page_num}&pageSize=40"
                else:
                    target_url = base_url
                
                print(f"  Page {page_num} -> {target_url}")
                
                try:
                    page.goto(target_url, wait_until="networkidle", timeout=60000)
                    if page.is_visible('button:has-text("Nõustun")'):
                        page.click('button:has-text("Nõustun")')
                except Exception as e:
                    print(f"  Navigation failed: {e}")
                    break
                
                if store_name == "Rimi":
                    raw_products = scrape_rimi_page(page)
                elif store_name == "Selver":
                    raw_products = scrape_selver_page(page)
                elif store_name == "Barbora":
                    raw_products = scrape_barbora_page(page)
                else:
                    raw_products = []
                
                if not raw_products:
                    print("  Page empty. Stopping category.")
                    break
                
                current_names = {p["name"] for p in raw_products}
                if current_names.issubset(seen_names):
                    print("  No new products found. Stopping category.")
                    break
                
                seen_names.update(current_names)
                count = 0
                sale_count = 0
                
                for pdt in raw_products:
                    name = pdt["name"]
                    if not name or name == "Unknown":
                        continue
                    
                    price = parse_price(pdt.get("price_text", ""))
                    
                    if price == 0:
                        continue
                    
                    # Track if this is a sale price
                    is_sale = pdt.get("is_sale", False)
                    if is_sale:
                        sale_count += 1
                    
                    unit_text = pdt.get("unit_text", "")
                    unit_price_val = parse_price_per_unit(unit_text)
                    
                    size_val = extract_unit_value(name, target_unit)
                    ppu = unit_price_val if unit_price_val > 0 else (price / size_val if size_val else 0)
                    
                    if name not in data["products"]:
                        data["products"][name] = {"category": category_key, "entries": []}
                    
                    prod = data["products"][name]
                    
                    # Check if price changed and log it
                    if prod["entries"] and prod["entries"][-1]["p"] != price:
                        old_price = prod["entries"][-1]["p"]
                        sale_marker = " 🏷️ SALE" if is_sale else ""
                        print(f"  💰 {name[:50]}... {old_price:.2f} → {price:.2f}{sale_marker}")
                    
                    if not prod["entries"] or prod["entries"][-1]["p"] != price:
                        prod["entries"].append({"t": data["meta"]["generated_at"], "p": price})
                    
                    prod.update({
                        "latest_price": price,
                        "price_per_unit": ppu,
                        "unit_label": target_unit,
                        "url": pdt.get("url", ""),
                        "img": pdt.get("img", ""),
                        "category": category_key,
                        "store": store_name,
                        "is_sale": is_sale  # Track sale status
                    })
                    count += 1
                
                sale_info = f" ({sale_count} on sale)" if sale_count > 0 else ""
                print(f"  ✓ {count} products{sale_info}")
                
                if len(raw_products) < 10 or count == 0:
                    break
                
                page_num += 1
                
                if page_num > 50:
                    print("  Safety limit reached (50 pages)")
                    break
        
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        browser.close()
        print("\n✅ Scrape Complete!")

if __name__ == "__main__":
    run_scraper()
    try:
        import build_site
        build_site.build()
        print("Success: Website updated (index.html)")
    except ImportError:
        print("Error: build_site.py not found. Website not updated.")