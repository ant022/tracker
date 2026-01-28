import json, os

HISTORY_FILE = "alcohol_history.json"
CONFIG_FILE = "categories.json"
OUTPUT_FILE = "index.html"

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
    """Generate unique key for a source using store:name format"""
    store = get_store_from_url(url)
    return f"{store}:{name}"

def load_data():
    if not os.path.exists(HISTORY_FILE): 
        return [], [], [], "Never"
    
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    product_categories = []
    sources = []
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw_config = json.load(f)
        
        # Handle new format (object with productCategories and sources)
        if isinstance(raw_config, dict) and 'sources' in raw_config:
            product_categories = raw_config.get('productCategories', [])
            sources = raw_config.get('sources', [])
        # Handle old format (array of sources)
        elif isinstance(raw_config, list):
            sources = raw_config
            product_categories = []
        # Handle very old dict format
        elif isinstance(raw_config, dict):
            for name, info in raw_config.items():
                if isinstance(info, dict):
                    sources.append({
                        "name": name,
                        "url": info["url"],
                        "unit": info.get("unit", "L"),
                        "productCategory": ""
                    })
                else:
                    sources.append({
                        "name": name,
                        "url": info,
                        "unit": "L",
                        "productCategory": ""
                    })
    
    # Build source info with keys
    sources_with_stores = []
    valid_keys = set()
    for source in sources:
        store = get_store_from_url(source.get("url", ""))
        source_key = get_category_key(source["name"], source["url"])
        sources_with_stores.append({
            "name": source["name"],
            "store": store,
            "key": source_key,
            "productCategory": source.get("productCategory", "")
        })
        valid_keys.add(source_key)
    
    # Filter products by valid source keys
    raw_products = data.get("products", {})
    products = [{"name": k, **v} for k, v in raw_products.items() if v.get('category') in valid_keys]
    
    return products, sources_with_stores, product_categories, data.get("meta", {}).get("generated_at", "Unknown")

def build():
    products, sources, product_categories, last_run = load_data()
    
    # Calculate products on sale
    sale_products = []
    for p in products:
        entries = p.get('entries', [])
        if len(entries) > 1:
            current_price = p.get('latest_price', 0)
            previous_price = entries[-2].get('p', 0)
            if current_price < previous_price:
                discount_pct = ((previous_price - current_price) / previous_price) * 100
                sale_products.append({
                    **p,
                    'previous_price': previous_price,
                    'discount_pct': discount_pct,
                    'savings': previous_price - current_price
                })
    
    # Sort by discount percentage
    sale_products.sort(key=lambda x: x['discount_pct'], reverse=True)
    
    # Build product category counts
    product_category_counts = {}
    for source in sources:
        cat = source.get('productCategory', '')
        if cat:
            if cat not in product_category_counts:
                product_category_counts[cat] = 0
            # Count products in this source
            source_products = [p for p in products if p.get('category') == source['key']]
            product_category_counts[cat] += len(source_products)
    
    # Generate sidebar with collapsible categories
    sidebar_links = ""
    
    # Product Categories Section (collapsible)
    if product_categories:
        sidebar_links += '''
        <div class="filter-section">
            <div class="filter-title" onclick="toggleCategories()" style="cursor: pointer; display: flex; justify-content: space-between; align-items: center;">
                <span>🏷️ Categories</span>
                <span id="categories-arrow">▼</span>
            </div>
            <div id="product-categories" class="product-categories">'''
        
        for cat in product_categories:
            count = product_category_counts.get(cat, 0)
            sidebar_links += f'''
                <label class="filter-checkbox">
                    <input type="checkbox" checked onchange="filterByProductCategory()" data-product-category="{cat}">
                    <span>{cat}</span>
                    <span class="count">({count})</span>
                </label>'''
        
        sidebar_links += '''
            </div>
        </div>'''
    
    # Stores Filter Section
    stores = list(set([source['store'] for source in sources]))
    stores.sort()
    
    sidebar_links += '<div class="filter-section">'
    sidebar_links += '<div class="filter-title">Stores</div>'
    for store in stores:
        sidebar_links += f'''
        <label class="filter-checkbox">
            <input type="checkbox" checked onchange="filterByStore()" data-store="{store}">
            <span class="store-label-sm store-label-{store}">{store}</span>
        </label>'''
    sidebar_links += '</div>'
    
    # Quick Filters
    sidebar_links += '<div class="filter-section">'
    sidebar_links += '<div class="filter-title">Quick Filters</div>'
    sidebar_links += '''
        <label class="filter-checkbox">
            <input type="checkbox" id="filter-favorites" onchange="applyFilters()">
            <span>⭐ Favorites only</span>
        </label>
        <label class="filter-checkbox">
            <input type="checkbox" id="filter-sales" onchange="applyFilters()">
            <span>🔥 On sale</span>
        </label>
    </div>'''
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Price Tracker</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f8f9fa; margin:0; display: flex; color: #1a1a1a; }}
        
        /* Hamburger Menu */
        .hamburger {{
            display: none;
            position: fixed;
            top: 15px;
            left: 15px;
            z-index: 1001;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            width: 44px;
            height: 44px;
            cursor: pointer;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 4px;
            padding: 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        .hamburger span {{
            display: block;
            width: 20px;
            height: 2px;
            background: #374151;
            border-radius: 2px;
            transition: 0.3s;
        }}
        
        .hamburger.active span:nth-child(1) {{
            transform: rotate(45deg) translate(5px, 5px);
        }}
        
        .hamburger.active span:nth-child(2) {{
            opacity: 0;
        }}
        
        .hamburger.active span:nth-child(3) {{
            transform: rotate(-45deg) translate(6px, -6px);
        }}
        
        .sidebar-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 999;
        }}
        
        /* Sidebar */
        .sidebar {{ 
            width: 260px; 
            background: white; 
            color: #374151; 
            height: 100vh; 
            position: fixed; 
            padding: 25px 0; 
            box-sizing: border-box; 
            overflow-y: auto; 
            z-index: 10;
            border-right: 1px solid #e5e7eb;
        }}
        
        .sidebar h2 {{ 
            font-size: 18px; 
            color: #111827; 
            margin: 0 20px 5px; 
            font-weight: 700;
        }}
        
        .last-run {{ 
            font-size: 11px; 
            color: #9ca3af; 
            margin: 0 20px 25px; 
            display:block; 
        }}
        
        .filter-section {{
            padding: 15px 20px;
            border-bottom: 1px solid #f3f4f6;
        }}
        
        .filter-title {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            color: #6b7280;
            margin-bottom: 12px;
            letter-spacing: 0.5px;
        }}
        
        .product-categories {{
            max-height: 300px;
            overflow-y: auto;
            transition: max-height 0.3s ease;
        }}
        
        .product-categories.collapsed {{
            max-height: 0;
            overflow: hidden;
        }}
        
        .filter-checkbox {{
            display: flex;
            align-items: center;
            padding: 8px 0;
            cursor: pointer;
            font-size: 14px;
            color: #374151;
            transition: 0.15s;
        }}
        
        .filter-checkbox:hover {{
            color: #111827;
        }}
        
        .filter-checkbox input[type="checkbox"] {{
            width: 18px;
            height: 18px;
            margin-right: 10px;
            cursor: pointer;
            accent-color: #10b981;
        }}
        
        .filter-checkbox .count {{
            margin-left: auto;
            font-size: 12px;
            color: #9ca3af;
        }}
        
        .store-label-sm {{ 
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
            margin-left: 4px;
        }}
        
        .store-label-Barbora {{ background: #fee2e2; color: #991b1b; }}
        .store-label-Selver {{ background: #fef3c7; color: #92400e; }}
        .store-label-Rimi {{ background: #fee2e2; color: #991b1b; }}
        .store-label-Coop {{ background: #dbeafe; color: #1e40af; }}
        .store-label-Unknown {{ background: #f3f4f6; color: #6b7280; }}
        
        .main {{ margin-left: 260px; flex: 1; padding: 0 40px 40px 40px; max-width: 1600px; margin-right: auto; }}

        /* STICKY HEADER */
        .header {{ 
            position: sticky; 
            top: 0; 
            background: #f8f9fa; 
            padding: 20px 0; 
            z-index: 100; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            border-bottom: 1px solid #e5e7eb;
        }}
        
        .controls {{ 
            display: flex; 
            gap: 12px; 
            background: white; 
            padding: 6px; 
            border-radius: 12px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.05); 
            align-items: center; 
            width: 100%; 
            justify-content: space-between;
            border: 1px solid #e5e7eb;
        }}
        
        .btn {{ 
            padding: 10px 18px; 
            border-radius: 8px; 
            border: none; 
            cursor: pointer; 
            font-weight: 600; 
            font-size: 14px; 
            background: transparent; 
            color: #6b7280; 
            transition: 0.15s; 
        }}
        
        .btn-active {{ 
            background: #10b981; 
            color: white; 
        }}
        
        .btn:hover:not(.btn-active) {{
            background: #f3f4f6;
            color: #374151;
        }}
        
        .search-box {{ 
            padding: 10px 15px; 
            border-radius: 8px; 
            border: 1px solid #e5e7eb; 
            width: 300px; 
            font-size: 14px; 
            outline: none; 
        }}
        
        .search-box:focus {{ 
            border-color: #10b981; 
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1); 
        }}

        /* FAVORITES/SALES SECTIONS */
        .favorites-section, .sales-section {{
            margin-top: 30px;
            scroll-margin-top: 100px;
            background: white;
            border-radius: 12px;
            padding: 20px 25px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        
        .sales-section {{
            border-color: #fee2e2;
        }}
        
        .favorites-section {{
            display: none;
        }}
        
        .section-title {{
            font-size: 16px;
            font-weight: 700;
            color: #374151;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .section-subtitle {{
            color: #9ca3af;
            font-size: 13px;
            margin-bottom: 20px;
        }}
        
        .sale-badge {{
            background: #fee2e2;
            color: #991b1b;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
        }}
        
        .carousel-container {{
            position: relative;
            overflow: hidden;
            touch-action: pan-y pinch-zoom;
            cursor: grab;
        }}
        
        .carousel-container:active {{
            cursor: grabbing;
        }}
        
        .carousel-track {{
            display: flex;
            gap: 15px;
            transition: transform 0.3s ease;
            user-select: none;
        }}
        
        .carousel-card {{
            min-width: 300px;
            flex-shrink: 0;
        }}
        
        .carousel-btn {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 18px;
            color: #6b7280;
            transition: 0.15s;
            z-index: 2;
        }}
        
        .carousel-btn:hover {{
            background: #f9fafb;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .carousel-btn-left {{ left: -15px; }}
        .carousel-btn-right {{ right: -15px; }}
        
        .carousel-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        .expand-sales-btn {{
            background: white;
            border: 1px solid #e5e7eb;
            color: #6b7280;
            padding: 8px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            transition: 0.15s;
        }}
        
        .expand-sales-btn:hover {{
            background: #f9fafb;
            color: #374151;
        }}
        
        .discount-badge {{
            position: absolute;
            top: 8px;
            left: 8px;
            background: #ef4444;
            color: white;
            font-size: 12px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 6px;
        }}

        /* PRODUCT CATEGORY SECTIONS */
        .product-cat-section {{ 
            margin-top: 30px; 
            scroll-margin-top: 100px; 
        }}
        
        .product-cat-title {{ 
            font-size: 20px; 
            font-weight: 700; 
            color: #111827; 
            margin-bottom: 15px; 
            padding-left: 12px;
            border-left: 4px solid #10b981; 
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .cat-section {{ 
            margin-top: 20px; 
        }}
        
        .cat-title {{ 
            font-size: 16px; 
            font-weight: 600; 
            color: #374151; 
            margin-bottom: 12px; 
            padding-left: 10px;
            border-left: 3px solid #e5e7eb; 
        }}
        
        .grid {{ 
            display:grid; 
            grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); 
            gap: 15px; 
        }}
        
        .card {{ 
            background:white; 
            border-radius:10px; 
            padding:15px; 
            box-shadow:0 1px 3px rgba(0,0,0,0.05); 
            display:flex; 
            gap:15px; 
            text-decoration:none; 
            color:inherit; 
            height: 130px; 
            position: relative; 
            transition: 0.15s; 
            border: 1px solid #e5e7eb; 
        }}
        
        .card:hover {{ 
            transform: translateY(-2px); 
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border-color: #d1d5db;
        }}

        .store-badge {{ 
            position: absolute; 
            top: 8px; 
            right: 8px; 
            font-size: 9px; 
            padding: 3px 6px; 
            border-radius: 4px; 
            font-weight: 700; 
            text-transform: uppercase; 
        }}
        
        .store-Barbora {{ background: #fee2e2; color: #991b1b; }}
        .store-Selver {{ background: #fef3c7; color: #92400e; }}
        .store-Rimi {{ background: #fee2e2; color: #991b1b; }}
        .store-Coop {{ background: #dbeafe; color: #1e40af; }}

        .card img {{ width:70px; height:100%; object-fit:contain; }}
        .info {{ flex: 1; display: flex; flex-direction: column; justify-content: center; }}
        .name {{ font-size:13px; font-weight:600; line-height:1.4; max-height: 2.8em; overflow: hidden; margin-bottom: 5px; color: #1f2937; }}
        
        .fav-btn {{
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 14px;
            transition: 0.15s;
            z-index: 5;
            pointer-events: auto;
        }}
        
        .fav-btn:hover {{
            border-color: #fbbf24;
            background: #fffbeb;
            transform: scale(1.05);
        }}
        
        .fav-btn.active {{
            background: #fef3c7;
            border-color: #f59e0b;
        }}
        
        .price-container {{ display: flex; align-items: baseline; gap: 6px; }}
        .price {{ font-size:20px; font-weight:700; color: #111827; }}
        .price-sale {{ 
            background-color: #d1fae5;
            color: #065f46;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
        }}
        
        .price-old {{ font-size: 14px; color: #9ca3af; text-decoration: line-through; font-weight: 500; }}
        .per-l {{ color:#059669; font-weight:600; font-size:12px; }}
        
        .expand-bar {{ 
            grid-column: 1 / -1; 
            background: #f9fafb; 
            border: 1px solid #e5e7eb; 
            color: #6b7280; 
            text-align: center; 
            padding: 12px; 
            border-radius: 8px; 
            cursor: pointer; 
            font-weight: 600; 
            margin-top: 10px; 
            transition: 0.15s;
        }}
        
        .expand-bar:hover {{
            background: white;
            color: #374151;
        }}
        
        .hidden {{ display: none; }}
        
        #search-results-title {{ 
            display: none; 
            margin-top: 30px; 
            color: #374151; 
            border-left: 3px solid #10b981; 
            padding-left: 12px; 
            font-size: 18px; 
            font-weight: 700; 
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: #9ca3af;
        }}
        
        .empty-state-icon {{
            font-size: 48px;
            margin-bottom: 16px;
        }}
        
        /* MOBILE RESPONSIVE */
        @media (max-width: 768px) {{
            body {{ display: block; }}
            .hamburger {{ display: flex; }}
            
            .sidebar {{
                position: fixed;
                left: -260px;
                transition: left 0.3s ease;
                z-index: 1000;
            }}
            
            .sidebar.active {{ left: 0; }}
            .sidebar-overlay.active {{ display: block; }}
            
            .main {{
                margin-left: 0;
                padding: 80px 15px 40px 15px;
            }}
            
            .header {{ padding: 15px 0; }}
            
            .controls {{
                flex-direction: column;
                gap: 12px;
                padding: 12px;
            }}
            
            .controls > div {{
                width: 100%;
                display: flex;
                gap: 8px;
            }}
            
            .btn {{
                flex: 1;
                padding: 12px 10px;
                font-size: 15px;
            }}
            
            .search-box {{
                width: 100%;
                padding: 12px 15px;
                font-size: 16px;
            }}
            
            .grid {{
                grid-template-columns: 1fr;
                gap: 12px;
            }}
            
            .card {{
                height: 140px;
                padding: 15px;
                gap: 12px;
            }}
            
            .card img {{ width: 80px; }}
            .name {{ font-size: 14px; line-height: 1.5; }}
            .price {{ font-size: 22px; }}
            .price-old {{ font-size: 16px; }}
            .per-l {{ font-size: 13px; }}
            
            .fav-btn {{
                width: 38px;
                height: 38px;
                font-size: 16px;
            }}
            
            .carousel-card {{
                min-width: calc(100% - 70px);
                max-width: calc(100% - 70px);
            }}
            
            .carousel-track {{ padding: 0 5px; }}
            
            .carousel-btn {{
                width: 32px;
                height: 32px;
                font-size: 16px;
            }}
            
            .carousel-btn-left {{ left: 0; }}
            .carousel-btn-right {{ right: 0; }}
        }}
    </style>
</head>
<body>
    <button class="hamburger" id="hamburger" onclick="toggleMenu()">
        <span></span>
        <span></span>
        <span></span>
    </button>
    
    <div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleMenu()"></div>
    
    <div class="sidebar" id="sidebar">
        <h2>📊 Price Tracker</h2>
        <span class="last-run">Updated: {last_run[:10]}</span>
        {sidebar_links}
    </div>

    <div class="main">
        <div class="header">
            <div class="controls">
                <div>
                    <button class="btn" id="sort-unit" onclick="setSort('price_per_unit')">Best Value</button>
                    <button class="btn btn-active" id="sort-total" onclick="setSort('latest_price')">Price</button>
                </div>
                <input type="text" id="search" class="search-box" placeholder="Search products..." oninput="handleSearch()">
            </div>
        </div>
        
        <div id="search-results-title">Search Results</div>
        <div id="search-grid" class="grid" style="margin-top: 20px;"></div>

        <div id="content"></div>
    </div>

<script>
const products = {json.dumps(products)};
const sources = {json.dumps(sources)};
const productCategories = {json.dumps(product_categories)};
const saleProducts = {json.dumps(sale_products)};

let currentSort = 'latest_price';
let favorites = [];
let carouselPosition = 0;
let touchStartX = 0;
let touchEndX = 0;
let activeStores = new Set({json.dumps([source['store'] for source in sources])});
let activeProductCategories = new Set(productCategories);

// Toggle mobile menu
function toggleMenu() {{
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const hamburger = document.getElementById('hamburger');
    
    sidebar.classList.toggle('active');
    overlay.classList.toggle('active');
    hamburger.classList.toggle('active');
}}

// Toggle product categories dropdown
function toggleCategories() {{
    const categoriesDiv = document.getElementById('product-categories');
    const arrow = document.getElementById('categories-arrow');
    categoriesDiv.classList.toggle('collapsed');
    arrow.textContent = categoriesDiv.classList.contains('collapsed') ? '▶' : '▼';
}}

// Touch swipe handling
function handleTouchStart(e) {{ touchStartX = e.touches[0].clientX; }}
function handleTouchMove(e) {{ touchEndX = e.touches[0].clientX; }}
function handleTouchEnd() {{
    const swipeThreshold = 50;
    const diff = touchStartX - touchEndX;
    if (Math.abs(diff) > swipeThreshold) {{
        if (diff > 0) {{ moveCarousel(1); }} else {{ moveCarousel(-1); }}
    }}
    touchStartX = 0;
    touchEndX = 0;
}}

function initCarouselTouch() {{
    const carouselContainer = document.querySelector('.carousel-container');
    if (carouselContainer) {{
        carouselContainer.addEventListener('touchstart', handleTouchStart, {{ passive: true }});
        carouselContainer.addEventListener('touchmove', handleTouchMove, {{ passive: true }});
        carouselContainer.addEventListener('touchend', handleTouchEnd);
    }}
}}

// Load favorites
function loadFavorites() {{
    const stored = localStorage.getItem('priceTrackerFavorites');
    if (stored) {{
        try {{ favorites = JSON.parse(stored); }}
        catch(e) {{ favorites = []; }}
    }}
}}

function saveFavorites() {{
    localStorage.setItem('priceTrackerFavorites', JSON.stringify(favorites));
}}

function toggleFavorite(productName, event) {{
    event.preventDefault();
    event.stopPropagation();
    
    const index = favorites.indexOf(productName);
    if (index > -1) {{ favorites.splice(index, 1); }} 
    else {{ favorites.push(productName); }}
    saveFavorites();
    render();
    return false;
}}

// Carousel navigation
function moveCarousel(direction) {{
    const track = document.querySelector('.carousel-track');
    const cards = document.querySelectorAll('.carousel-card');
    if (!track || cards.length === 0) return;
    
    const firstCard = cards[0];
    const cardWidth = firstCard.offsetWidth + 15;
    carouselPosition += direction;
    
    const containerWidth = track.parentElement.offsetWidth;
    const visibleCards = Math.floor(containerWidth / cardWidth) || 1;
    const maxPosition = Math.max(0, cards.length - visibleCards);
    carouselPosition = Math.max(0, Math.min(carouselPosition, maxPosition));
    
    track.style.transform = `translateX(-${{carouselPosition * cardWidth}}px)`;
    
    const leftBtn = document.querySelector('.carousel-btn-left');
    const rightBtn = document.querySelector('.carousel-btn-right');
    if (leftBtn) leftBtn.disabled = carouselPosition === 0;
    if (rightBtn) rightBtn.disabled = carouselPosition >= maxPosition;
}}

// Filters
function filterByStore() {{
    const checkboxes = document.querySelectorAll('input[data-store]');
    activeStores.clear();
    checkboxes.forEach(cb => {{
        if (cb.checked) activeStores.add(cb.dataset.store);
    }});
    render();
}}

function filterByProductCategory() {{
    const checkboxes = document.querySelectorAll('input[data-product-category]');
    activeProductCategories.clear();
    checkboxes.forEach(cb => {{
        if (cb.checked) activeProductCategories.add(cb.dataset.productCategory);
    }});
    render();
}}

function applyFilters() {{ render(); }}

function setSort(key){{
    currentSort = key;
    document.querySelectorAll('.btn').forEach(b=>b.classList.remove('btn-active'));
    document.getElementById(key==='latest_price'?'sort-total':'sort-unit').classList.add('btn-active');
    render();
}}

function handleSearch() {{
    const query = document.getElementById('search').value.toLowerCase();
    const searchGrid = document.getElementById('search-grid');
    const searchTitle = document.getElementById('search-results-title');
    const content = document.getElementById('content');

    if (query.length < 2) {{
        searchGrid.innerHTML = "";
        searchTitle.style.display = "none";
        content.style.display = "block";
        return;
    }}

    const filtered = products.filter(p => p.name.toLowerCase().includes(query))
                             .sort((a,b) => (a[currentSort] || 999) - (b[currentSort] || 999));

    content.style.display = "none";
    searchTitle.style.display = "block";
    searchGrid.innerHTML = filtered.map(p => card(p)).join('');
}}

function getPriceTrend(p) {{
    const entries = p.entries || [];
    if (entries.length < 2) return {{ trend: 'stable', symbol: '➡️', class: 'price-trend-stable' }};
    
    const current = p.latest_price;
    const previous = entries[entries.length - 2].p;
    
    if (current < previous) {{
        const pct = (((previous - current) / previous) * 100).toFixed(0);
        return {{ trend: 'down', symbol: `🔻 -${{pct}}%`, class: 'price-trend-down' }};
    }} else if (current > previous) {{
        const pct = (((current - previous) / previous) * 100).toFixed(0);
        return {{ trend: 'up', symbol: `🔺 +${{pct}}%`, class: 'price-trend-up' }};
    }}
    return {{ trend: 'stable', symbol: '➡️', class: 'price-trend-stable' }};
}}

function render() {{
    const container = document.getElementById("content");
    container.innerHTML = "";
    carouselPosition = 0;
    
    // Apply filters
    const showFavoritesOnly = document.getElementById('filter-favorites')?.checked || false;
    const showSalesOnly = document.getElementById('filter-sales')?.checked || false;
    
    let filteredProducts = products.filter(p => {{
        // Filter by store
        if (!activeStores.has(p.store)) return false;
        
        // Filter by product category
        const source = sources.find(s => s.key === p.category);
        if (source && source.productCategory) {{
            if (!activeProductCategories.has(source.productCategory)) return false;
        }}
        
        return true;
    }});
    
    if (showFavoritesOnly) {{
        filteredProducts = filteredProducts.filter(p => favorites.includes(p.name));
    }}
    
    if (showSalesOnly) {{
        const saleNames = new Set(saleProducts.map(p => p.name));
        filteredProducts = filteredProducts.filter(p => saleNames.has(p.name));
    }}
    
    // RENDER FAVORITES
    renderFavorites(container, filteredProducts);
    
    // RENDER SALES
    if (saleProducts.length > 0 && !showFavoritesOnly) {{
        renderSales(container);
    }}
    
    // RENDER BY PRODUCT CATEGORY
    if (productCategories.length > 0) {{
        productCategories.forEach(prodCat => {{
            if (!activeProductCategories.has(prodCat)) return;
            
            // Get all products in this category
            const catProducts = filteredProducts.filter(p => {{
                const source = sources.find(s => s.key === p.category);
                return source && source.productCategory === prodCat;
            }});
            
            if (catProducts.length === 0) return;
            
            // Group by source within category
            const bySource = {{}};
            catProducts.forEach(p => {{
                if (!bySource[p.category]) bySource[p.category] = [];
                bySource[p.category].push(p);
            }});
            
            let html = `<div class="product-cat-section">
                <div class="product-cat-title">
                    <span>${{prodCat}}</span>
                    <span style="font-size:14px; font-weight:normal; color:#9ca3af">(${{catProducts.length}} products)</span>
                </div>`;
            
            sources.forEach((source, idx) => {{
                if (source.productCategory !== prodCat) return;
                if (!bySource[source.key]) return;
                if (!activeStores.has(source.store)) return;
                
                const sorted = bySource[source.key].sort((a,b)=> (a[currentSort] || 999) - (b[currentSort] || 999));
                const top5 = sorted.slice(0, 5);
                const rest = sorted.slice(5);
                const hiddenId = `hidden_${{prodCat}}_${{idx}}`;
                
                html += `
                    <div class="cat-section">
                        <div class="cat-title">${{source.name}} <span style="font-size:12px; font-weight:normal; color:#9ca3af">(${{sorted.length}})</span></div>
                        <div class="grid">${{top5.map(p=>card(p)).join('')}}</div>`;
                
                if (rest.length > 0) {{
                    html += `<div id="${{hiddenId}}" class="grid hidden" style="margin-top:15px">${{rest.map(p=>card(p)).join('')}}</div>
                             <div class="expand-bar" onclick="toggle('${{hiddenId}}', this)">Show ${{rest.length}} more ▾</div>`;
                }}
                
                html += `</div>`;
            }});
            
            html += `</div>`;
            container.innerHTML += html;
        }});
    }} else {{
        // No product categories - render by source
        renderBySources(container, filteredProducts);
    }}
    
    // Show empty state if no products
    if (filteredProducts.length === 0) {{
        container.innerHTML += `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <p>No products match your filters</p>
            </div>`;
    }}
    
    if (document.getElementById('search').value.length >= 2) handleSearch();
}}

function renderFavorites(container, filteredProducts) {{
    const favSection = document.getElementById('favorites-section') || document.createElement('div');
    favSection.id = 'favorites-section';
    favSection.className = 'favorites-section';
    
    if (favorites.length > 0) {{
        const favoriteProducts = filteredProducts
            .filter(p => favorites.includes(p.name))
            .sort((a, b) => (a.latest_price || 999) - (b.latest_price || 999));
        
        if (favoriteProducts.length > 0) {{
            const favCardsHtml = favoriteProducts.map(p => {{
                const trend = getPriceTrend(p);
                return `<div class="carousel-card">${{cardWithTrend(p, trend)}}</div>`;
            }}).join('');
            
            const isMobile = window.innerWidth <= 768;
            const cardsVisible = isMobile ? 1 : 3;
            const hasMultiplePages = favoriteProducts.length > cardsVisible;
            
            favSection.innerHTML = `
                <div class="section-title">
                    <span>⭐</span>
                    <span>Favorites</span>
                </div>
                <div class="section-subtitle">
                    ${{favoriteProducts.length}} tracked · Sorted by price
                </div>
                <div class="carousel-container">
                    <button class="carousel-btn carousel-btn-left" onclick="moveCarousel(-1)" disabled>←</button>
                    <div class="carousel-track">
                        ${{favCardsHtml}}
                    </div>
                    <button class="carousel-btn carousel-btn-right" onclick="moveCarousel(1)" ${{hasMultiplePages ? '' : 'disabled'}}>→</button>
                </div>
            `;
            favSection.style.display = 'block';
            
            carouselPosition = 0;
            setTimeout(() => {{
                initCarouselTouch();
                moveCarousel(0);
            }}, 100);
        }} else {{
            favSection.style.display = 'none';
        }}
    }} else {{
        favSection.style.display = 'none';
    }}
    container.appendChild(favSection);
}}

function renderSales(container) {{
    const filteredSales = saleProducts.filter(p => activeStores.has(p.store));
    if (filteredSales.length === 0) return;
    
    const top3Sales = filteredSales.slice(0, 3);
    const restSales = filteredSales.slice(3);
    
    const salesHtml = `
        <div class="sales-section" id="sales-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <div class="section-title">
                    <span>🔥</span>
                    <span>On Sale</span>
                    <span class="sale-badge">${{filteredSales.length}}</span>
                </div>
                ${{restSales.length > 0 ? 
                    `<button class="expand-sales-btn" onclick="toggleAllSales()">Show all</button>` 
                    : ''}}
            </div>
            <div class="grid" id="top-sales-grid">${{top3Sales.map(p => cardWithDiscount(p)).join('')}}</div>
            <div class="grid hidden" id="all-sales-grid" style="margin-top:15px">${{restSales.map(p => cardWithDiscount(p)).join('')}}</div>
        </div>
    `;
    container.innerHTML += salesHtml;
}}

function renderBySources(container, filteredProducts) {{
    const byCat = {{}};
    filteredProducts.forEach(p => {{
        if(!byCat[p.category]) byCat[p.category] = [];
        byCat[p.category].push(p);
    }});

    sources.forEach((source, index) => {{
        if (!byCat[source.key] || !activeStores.has(source.store)) return;
        
        const sorted = byCat[source.key].sort((a,b)=> (a[currentSort] || 999) - (b[currentSort] || 999));
        const top5 = sorted.slice(0, 5);
        const rest = sorted.slice(5);
        const hiddenId = `hidden_source_${{index}}`;

        let html = `
            <div class="cat-section">
                <div class="cat-title">${{source.name}} <span style="font-size:13px; font-weight:normal; color:#9ca3af">(${{sorted.length}})</span></div>
                <div class="grid">${{top5.map(p=>card(p)).join('')}}</div>
        `;
        if (rest.length > 0) {{
            html += `<div id="${{hiddenId}}" class="grid hidden" style="margin-top:15px">${{rest.map(p=>card(p)).join('')}}</div>
                     <div class="expand-bar" onclick="toggle('${{hiddenId}}', this)">Show ${{rest.length}} more ▾</div>`;
        }}
        html += `</div>`;
        container.innerHTML += html;
    }});
}}

function toggleAllSales() {{
    const allSalesGrid = document.getElementById('all-sales-grid');
    const btn = event.target;
    const isHidden = allSalesGrid.classList.toggle('hidden');
    btn.textContent = isHidden ? 'Show all' : 'Show less';
}}

function toggle(id, btn) {{
    const el = document.getElementById(id);
    const isHidden = el.classList.toggle('hidden');
    btn.innerHTML = isHidden ? `Show more ▾` : "Collapse ▴";
}}

function cardWithTrend(p, trend) {{
    const unitLabel = p.unit_label || 'L';
    const unitPrice = p.price_per_unit || p.price_per_litre || 0;
    const isFav = favorites.includes(p.name);
    const safeName = p.name.replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
    
    return `<a href="${{p.url}}" target="_blank" class="card">
        <span class="store-badge store-${{p.store}}">${{p.store}}</span>
        <button class="fav-btn ${{isFav ? 'active' : ''}}" onclick="toggleFavorite('${{safeName}}', event); return false;">
            ${{isFav ? '⭐' : '☆'}}
        </button>
        <img src="${{p.img}}" onerror="this.src='https://via.placeholder.com/60x90?text=No+Img'">
        <div class="info">
            <div class="name">${{p.name}}</div>
            <div class="price-container">
                <span class="price">€${{p.latest_price.toFixed(2)}}</span>
                <span style="font-size: 11px; color: #9ca3af;">${{trend.symbol}}</span>
            </div>
            <div class="per-l">€${{unitPrice.toFixed(2)}} / ${{unitLabel}}</div>
        </div>
    </a>`;
}}

function cardWithDiscount(p) {{
    const unitLabel = p.unit_label || 'L';
    const unitPrice = p.price_per_unit || p.price_per_litre || 0;
    const discountPct = p.discount_pct || 0;
    const isFav = favorites.includes(p.name);
    const safeName = p.name.replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
    
    return `<a href="${{p.url}}" target="_blank" class="card">
        <span class="discount-badge">-${{discountPct.toFixed(0)}}%</span>
        <span class="store-badge store-${{p.store}}">${{p.store}}</span>
        <button class="fav-btn ${{isFav ? 'active' : ''}}" onclick="toggleFavorite('${{safeName}}', event); return false;">
            ${{isFav ? '⭐' : '☆'}}
        </button>
        <img src="${{p.img}}" onerror="this.src='https://via.placeholder.com/60x90?text=No+Img'">
        <div class="info">
            <div class="name">${{p.name}}</div>
            <div class="price-container">
                <span class="price price-sale">€${{p.latest_price.toFixed(2)}}</span>
                <span class="price-old">€${{p.previous_price.toFixed(2)}}</span>
            </div>
            <div class="per-l">€${{unitPrice.toFixed(2)}} / ${{unitLabel}}</div>
        </div>
    </a>`;
}}

function card(p) {{
    const unitLabel = p.unit_label || 'L';
    const unitPrice = p.price_per_unit || p.price_per_litre || 0;
    const entries = p.entries || [];
    const isFav = favorites.includes(p.name);
    const safeName = p.name.replace(/'/g, "\\\\'").replace(/"/g, '&quot;');
    
    let priceDisplay = `<div class="price">€${{p.latest_price.toFixed(2)}}</div>`;
    
    if (entries.length > 1) {{
        const currentP = p.latest_price;
        const previousP = entries[entries.length - 2].p;
        
        if (currentP < previousP) {{
            priceDisplay = `
                <div class="price-container">
                    <span class="price price-sale">€${{currentP.toFixed(2)}}</span>
                    <span class="price-old">€${{previousP.toFixed(2)}}</span>
                </div>`;
        }} else if (currentP > previousP) {{
            priceDisplay = `
                <div class="price-container">
                    <span class="price">€${{currentP.toFixed(2)}}</span>
                    <span style="font-size: 10px; color: #ef4444;">▲</span>
                </div>`;
        }}
    }}

    return `<a href="${{p.url}}" target="_blank" class="card">
        <span class="store-badge store-${{p.store}}">${{p.store}}</span>
        <button class="fav-btn ${{isFav ? 'active' : ''}}" onclick="toggleFavorite('${{safeName}}', event); return false;">
            ${{isFav ? '⭐' : '☆'}}
        </button>
        <img src="${{p.img}}" onerror="this.src='https://via.placeholder.com/60x90?text=No+Img'">
        <div class="info">
            <div class="name">${{p.name}}</div>
            ${{priceDisplay}}
            <div class="per-l">€${{unitPrice.toFixed(2)}} / ${{unitLabel}}</div>
        </div>
    </a>`;
}}

loadFavorites();
render();
</script>
</body>
</html>
"""
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"Static site built: {OUTPUT_FILE}")
    print(f"Found {len(sale_products)} products on sale")
    print(f"Product categories: {', '.join(product_categories) if product_categories else 'None'}")

if __name__ == "__main__":
    build()