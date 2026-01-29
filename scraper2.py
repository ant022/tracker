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
    if not url or not isinstance(url, str):
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
    """Load config - supports both old and new formats"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Handle new format (object with productCategories and sources)
        if isinstance(data, dict) and 'sources' in data:
            return data.get('sources', [])
        
        # Handle old format (array of sources)
        elif isinstance(data, list):
            return data
        
        # Handle very old dict format
        elif isinstance(data, dict):
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
            return new_format
    
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

# ---------------- RIMI (UPDATED WITH DEBUG) ----------------
def debug_rimi_page(page):
    """Debug function to see what's actually on the page"""
    print("\n=== RIMI DEBUG ===")
    
    # Save screenshot
    try:
        page.screenshot(path="rimi_debug.png")
        print("Screenshot saved to rimi_debug.png")
    except Exception as e:
        print(f"Could not save screenshot: {e}")
    
    # Check for common selectors
    selectors_to_check = [
        '.card',
        '.product-card',
        '[data-testid="product-card"]',
        '.product',
        '.product-grid',
        '.js-product-container',
        '[class*="product"]',
        '[class*="card"]'
    ]
    
    for selector in selectors_to_check:
        count = page.locator(selector).count()
        if count > 0:
            print(f"  ✓ {selector}: {count} elements found")
        else:
            print(f"  ✗ {selector}: 0 elements")
    
    # Get page HTML snippet
    try:
        html_snippet = page.evaluate("() => document.body.innerHTML.substring(0, 3000)")
        print(f"\nFirst 3000 chars of HTML:\n{html_snippet}\n")
        
        # Save full HTML for inspection
        with open("rimi_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        print("Full HTML saved to rimi_debug.html")
    except Exception as e:
        print(f"Could not get HTML: {e}")
    
    return True

def scrape_rimi_page(page, debug_mode=False):
    """Updated Rimi scraper with better error handling and debug mode"""
    if debug_mode:
        debug_rimi_page(page)
    
    print("  [Rimi] Waiting for content...")
    
    # Try multiple possible selectors
    selectors = [
        '.card',
        '[data-testid="product-card"]',
        '.product-card',
        '.product-item',
        '[class*="ProductCard"]'
    ]
    
    found_selector = None
    for selector in selectors:
        try:
            page.wait_for_selector(selector, state='visible', timeout=5000)
            count = page.locator(selector).count()
            if count > 0:
                found_selector = selector
                print(f"  [Rimi] Found {count} products using selector: {selector}")
                break
        except:
            continue
    
    if not found_selector:
        print("  [Rimi] ERROR: No product cards found with any known selector")
        # Save debug info
        try:
            page.screenshot(path="rimi_error.png")
            with open("rimi_error.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("  [Rimi] Saved rimi_error.png and rimi_error.html for debugging")
        except:
            pass
        return []
    
    # Accept cookies if present
    try:
        cookie_buttons = [
            'button:has-text("Nõustu")',
            'button:has-text("Nõustun")',
            'button:has-text("Accept")',
            '[data-testid="cookie-accept"]'
        ]
        for btn in cookie_buttons:
            if page.is_visible(btn, timeout=2000):
                page.click(btn)
                time.sleep(1)
                break
    except:
        pass
    
    # Scroll to load lazy content
    for i in range(6):
        page.mouse.wheel(0, 2500)
        time.sleep(0.4)
    
    time.sleep(1)
    
    # Use the found selector
    return page.evaluate(f"""
        () => {{
            const cards = Array.from(document.querySelectorAll('{found_selector}'));
            console.log('Found cards:', cards.length);
            
            return cards.map(card => {{
                // Try multiple ways to get the name
                const name = card.querySelector('.card__name')?.innerText.trim() ||
                             card.querySelector('[data-testid="product-name"]')?.innerText.trim() ||
                             card.querySelector('h3')?.innerText.trim() ||
                             card.querySelector('.product-name')?.innerText.trim() ||
                             card.querySelector('[class*="name"]')?.innerText.trim() ||
                             "Unknown";
                
                const url = card.querySelector('a')?.href || "";
                const img = card.querySelector('img')?.src || "";
                
                // Price extraction - try multiple methods
                let price = 0;
                let isSalePrice = false;
                
                // Method 1: Sale price in price-label
                const priceLabel = card.querySelector('.price-label__price');
                if (priceLabel) {{
                    const major = priceLabel.querySelector('.major')?.innerText.trim() || "0";
                    const cents = priceLabel.querySelector('.cents')?.innerText.trim() || "00";
                    price = parseFloat(major + "." + cents);
                    isSalePrice = true;
                }}
                
                // Method 2: Regular price-tag
                if (price === 0) {{
                    const priceTag = card.querySelector('.price-tag');
                    if (priceTag) {{
                        const main = priceTag.querySelector('span')?.innerText.trim().replace(',', '.') || "0";
                        const frac = priceTag.querySelector('sup')?.innerText.trim() || "00";
                        price = parseFloat(main + "." + frac.replace(/\\D/g,'')) || 0;
                    }}
                }}
                
                // Method 3: Any element with price-like class
                if (price === 0) {{
                    const priceEl = card.querySelector('[class*="price"]');
                    if (priceEl) {{
                        const priceText = priceEl.innerText.replace(/[^0-9.,]/g, '').replace(',', '.');
                        price = parseFloat(priceText) || 0;
                    }}
                }}
                
                // Method 4: Look for any number that looks like a price
                if (price === 0) {{
                    const allText = card.innerText;
                    const priceMatch = allText.match(/€?\\s*(\\d+)[.,](\\d{{2}})/);
                    if (priceMatch) {{
                        price = parseFloat(priceMatch[1] + '.' + priceMatch[2]);
                    }}
                }}
                
                // Unit price
                let unitText = "";
                const saleUnitPrice = card.querySelector('.price-per-unit');
                const regularUnitPrice = card.querySelector('.card__price-per');
                
                if (isSalePrice && saleUnitPrice) {{
                    unitText = saleUnitPrice.innerText?.replace(/\\s+/g, ' ').trim() || "";
                }} else if (regularUnitPrice) {{
                    unitText = regularUnitPrice.innerText?.replace(/\\s+/g, ' ').trim() || "";
                }}
                
                return {{
                    name,
                    url,
                    img,
                    price_text: price.toString(),
                    unit_text: unitText,
                    is_sale: isSalePrice
                }};
            }}).filter(p => p.name !== "Unknown" && p.price_text !== "0");
        }}
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
    
    if not CATEGORIES:
        print("❌ No categories found in categories.json")
        return
    
    print(f"📋 Loaded {len(CATEGORIES)} categories")
    
    # Check if running in GitHub Actions or locally
    is_github = os.environ.get("GITHUB_ACTIONS") == "true"
    debug_mode = os.environ.get("DEBUG_MODE") == "true" or not is_github
    
    if debug_mode:
        print("🔍 Running in DEBUG mode (will save screenshots and HTML)")
    
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
        
        # Configure browser for both local and GitHub Actions
        launch_options = {
            "headless": True
        }
        
        # Add args for GitHub Actions environment
        if is_github:
            launch_options["args"] = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        
        browser = p.chromium.launch(**launch_options)
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
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
                    
                    # Try to accept cookies for all stores
                    try:
                        if page.is_visible('button:has-text("Nõustun")', timeout=2000):
                            page.click('button:has-text("Nõustun")')
                            time.sleep(1)
                    except:
                        pass
                        
                except Exception as e:
                    print(f"  Navigation failed: {e}")
                    break
                
                if store_name == "Rimi":
                    # Enable debug mode for first page of Rimi
                    raw_products = scrape_rimi_page(page, debug_mode=(page_num == 1 and debug_mode))
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
                        "is_sale": is_sale
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