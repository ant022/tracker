from playwright.sync_api import sync_playwright
import time
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    )
    page = context.new_page()
    
    print("Loading Rimi pasta page...")
    page.goto("https://www.rimi.ee/epood/ee/tooted/kauasailivad-toidukaubad/makaronid-ja-riis/makaronid-pasta/c/SH-13-14-20", 
              wait_until="domcontentloaded", timeout=60000)
    
    # Accept cookies if present
    try:
        page.click('button:has-text("Nõustu vajalike")', timeout=3000)
        print("✓ Accepted cookies")
    except:
        pass
    
    time.sleep(2)
    
    # Scroll to load lazy content
    for _ in range(6):
        page.mouse.wheel(0, 2500)
        time.sleep(0.4)
    
    time.sleep(1)
    
    # Find La Molisana products
    result = page.evaluate("""
        () => {
            const cards = Array.from(document.querySelectorAll('.card'));
            
            // Find all La Molisana products
            const molisanaCards = cards.filter(card => {
                const text = card.innerText.toLowerCase();
                return text.includes('molisana') || text.includes('lamolisana');
            });
            
            console.log('Found', molisanaCards.length, 'La Molisana products');
            
            return molisanaCards.slice(0, 3).map(card => {
                const name = card.querySelector('.card__name')?.innerText.trim() || "Unknown";
                const url = card.querySelector('a')?.href || "";
                
                // Price extraction - current method
                const priceTag = card.querySelector('.price-tag');
                const mainSpan = card.querySelector('.price-tag > span')?.innerText.trim();
                const fracSup = card.querySelector('.price-tag sup')?.innerText.trim();
                
                // Look for sale/discount indicators
                const discountBadge = card.querySelector('.card__badge--type_discount');
                const hasDiscount = !!discountBadge;
                const discountText = discountBadge?.innerText.trim();
                
                // Look for strikethrough/old price
                const oldPriceEl = card.querySelector('.price-tag--discount');
                const hasOldPrice = !!oldPriceEl;
                const oldPriceText = oldPriceEl?.innerText.trim();
                
                // Get ALL price-related elements
                const allPrices = Array.from(card.querySelectorAll('[class*="price"]')).map(el => ({
                    tag: el.tagName,
                    classes: el.className,
                    text: el.innerText?.substring(0, 100),
                    html: el.innerHTML.substring(0, 200)
                }));
                
                // Get unit price
                const unitPrice = card.querySelector('.card__price-per')?.innerText.trim();
                
                // Get card text
                const cardText = card.innerText;
                
                // Get outer HTML (truncated)
                const cardHTML = card.outerHTML.substring(0, 4000);
                
                return {
                    name,
                    url,
                    hasDiscount,
                    discountText,
                    priceTag: {
                        mainSpan,
                        fracSup,
                        fullHTML: priceTag?.innerHTML.substring(0, 500)
                    },
                    oldPrice: {
                        hasOldPrice,
                        oldPriceText,
                        element: oldPriceEl ? {
                            classes: oldPriceEl.className,
                            html: oldPriceEl.innerHTML.substring(0, 200)
                        } : null
                    },
                    allPrices,
                    unitPrice,
                    cardText,
                    cardHTML
                };
            });
        }
    """)
    
    print("\n" + "="*80)
    print("LA MOLISANA PRODUCTS ON RIMI")
    print("="*80)
    
    if not result or len(result) == 0:
        print("\n❌ No La Molisana products found")
    else:
        for i, product in enumerate(result, 1):
            print(f"\n{'='*80}")
            print(f"PRODUCT {i}: {product['name']}")
            print(f"URL: {product['url']}")
            print("="*80)
            
            print(f"\n🏷️  DISCOUNT INFO:")
            print(f"  Has discount badge: {product['hasDiscount']}")
            print(f"  Discount text: {product['discountText']}")
            
            print(f"\n💰 CURRENT PRICE:")
            print(f"  Main span: {product['priceTag']['mainSpan']}")
            print(f"  Fraction sup: {product['priceTag']['fracSup']}")
            print(f"  Full price tag HTML:\n{product['priceTag']['fullHTML']}")
            
            print(f"\n💸 OLD PRICE:")
            print(f"  Has old price: {product['oldPrice']['hasOldPrice']}")
            print(f"  Old price text: {product['oldPrice']['oldPriceText']}")
            if product['oldPrice']['element']:
                print(f"  Classes: {product['oldPrice']['element']['classes']}")
                print(f"  HTML: {product['oldPrice']['element']['html']}")
            
            print(f"\n📊 ALL PRICE ELEMENTS:")
            for price_el in product['allPrices']:
                print(f"  <{price_el['tag']} class='{price_el['classes']}'")
                print(f"    Text: {price_el['text']}")
                print(f"    HTML: {price_el['html']}")
                print()
            
            print(f"\n📦 UNIT PRICE: {product['unitPrice']}")
            
            print(f"\n📝 FULL CARD TEXT:")
            print(product['cardText'])
            
            print(f"\n🌐 CARD HTML (first 4000 chars):")
            print(product['cardHTML'])
            print()
    
    # Also check the specific product page
    print("\n" + "="*80)
    print("CHECKING SPECIFIC PRODUCT PAGE")
    print("="*80)
    
    product_url = "https://www.rimi.ee/epood/ee/tooted/kauasailivad-toidukaubad/makaronid-ja-riis/makaronid-pasta/pasta-lamolisana-penne-500g/p/189818"
    print(f"\nLoading: {product_url}")
    
    page.goto(product_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(2)
    
    product_page_info = page.evaluate("""
        () => {
            // Get product name
            const name = document.querySelector('h1')?.innerText.trim();
            
            // Get all price elements
            const priceElements = Array.from(document.querySelectorAll('[class*="price"]')).map(el => ({
                tag: el.tagName,
                classes: el.className,
                text: el.innerText?.trim(),
                html: el.innerHTML.substring(0, 300)
            }));
            
            // Look for campaign/sale info
            const campaignInfo = document.querySelector('[class*="campaign"]')?.innerText;
            
            return {
                name,
                priceElements,
                campaignInfo,
                bodyText: document.body.innerText.substring(0, 2000)
            };
        }
    """)
    
    print(f"\n✅ Product page loaded")
    print(f"Name: {product_page_info['name']}")
    print(f"\nCampaign info: {product_page_info['campaignInfo']}")
    print(f"\n📊 Price elements on product page:")
    for el in product_page_info['priceElements']:
        print(f"  <{el['tag']} class='{el['classes']}'")
        print(f"    Text: {el['text']}")
        print()
    
    print(f"\n📝 Body text sample:")
    print(product_page_info['bodyText'])
    
    browser.close()
    
    print("\n" + "="*80)
    print("✅ Diagnostic complete!")