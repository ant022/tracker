from playwright.sync_api import sync_playwright
import json

def diagnose_barbora_selectors(page, product_name_filter="molisana"):
    """Diagnose what selectors work on Barbora's current site"""
    
    # Wait for products to load
    try:
        page.wait_for_selector(".product-card-next", timeout=10000)
    except:
        print("❌ Could not find .product-card-next selector")
        return
    
    # Scroll to load lazy content
    for _ in range(5):
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(500)
    
    # Get detailed info about product cards
    result = page.evaluate(f"""
        () => {{
            const cards = Array.from(document.querySelectorAll('.product-card-next'));
            console.log('Total cards found:', cards.length);
            
            // Find cards matching filter
            const matchingCards = cards.filter(card => {{
                const text = card.innerText.toLowerCase();
                return text.includes('{product_name_filter.lower()}');
            }});
            
            console.log('Matching cards:', matchingCards.length);
            
            return matchingCards.slice(0, 2).map(card => {{
                // Get product name
                const titleEl = card.querySelector("span[id*='product-title']");
                const name = titleEl ? titleEl.innerText.trim() : "Unknown";
                
                // Try to find ALL divs and their attributes
                const allDivs = Array.from(card.querySelectorAll('div')).map((div, idx) => {{
                    const classes = div.className;
                    const ariaLabel = div.getAttribute('aria-label');
                    const text = div.innerText ? div.innerText.substring(0, 100) : '';
                    const innerHTML = div.innerHTML.substring(0, 150);
                    
                    return {{
                        index: idx,
                        classes: classes,
                        ariaLabel: ariaLabel,
                        text: text,
                        innerHTML: innerHTML
                    }};
                }});
                
                // Get the full card HTML (truncated)
                const cardHTML = card.outerHTML.substring(0, 3000);
                
                return {{
                    name: name,
                    totalDivs: allDivs.length,
                    divs: allDivs,
                    cardHTML: cardHTML,
                    fullText: card.innerText
                }};
            }});
        }}
    """)
    
    return result

# Main execution
with sync_playwright() as p:
    print("🚀 Starting Barbora HTML diagnostics...\n")
    
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    
    url = "https://barbora.ee/kauasailivad-toidukaubad/makaronid"
    print(f"📍 Loading: {url}\n")
    
    try:
        page.goto(url, wait_until="networkidle", timeout=60000)
        print("✅ Page loaded successfully\n")
    except Exception as e:
        print(f"❌ Failed to load page: {e}")
        browser.close()
        exit(1)
    
    # Diagnose
    results = diagnose_barbora_selectors(page, "molisana")
    
    if not results:
        print("❌ No matching products found")
    else:
        print(f"✅ Found {len(results)} matching product(s)\n")
        print("=" * 100)
        
        for i, card_info in enumerate(results, 1):
            print(f"\n🔍 PRODUCT {i}: {card_info['name']}")
            print("=" * 100)
            
            print(f"\n📝 Full card text:\n{card_info['fullText']}\n")
            
            print(f"🔢 Total divs in card: {card_info['totalDivs']}\n")
            
            print("📊 DIV ANALYSIS (showing divs with aria-label or containing numbers):")
            print("-" * 100)
            
            for div in card_info['divs']:
                # Only show potentially price-related divs
                if (div['ariaLabel'] or 
                    any(char.isdigit() for char in div['text']) or
                    'price' in div['classes'].lower() or
                    'hind' in str(div['ariaLabel']).lower()):
                    
                    print(f"\nDiv #{div['index']}:")
                    if div['ariaLabel']:
                        print(f"  aria-label: '{div['ariaLabel']}'")
                    if div['classes']:
                        print(f"  classes: {div['classes']}")
                    if div['text']:
                        print(f"  text: {div['text']}")
                    print(f"  HTML: {div['innerHTML'][:100]}...")
            
            print("\n" + "=" * 100)
            print("\n🌐 FULL CARD HTML (first 3000 chars):")
            print("-" * 100)
            print(card_info['cardHTML'])
            print("-" * 100)
    
    browser.close()
    print("\n\n✅ Diagnostic complete!")