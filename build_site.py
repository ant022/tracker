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
    """Generate unique key for a category using store:name format"""
    store = get_store_from_url(url)
    return f"{store}:{name}"

def load_data():
    if not os.path.exists(HISTORY_FILE): return [], [], "Never"
    
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    config = []
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw_config = json.load(f)
            
        # Convert old dict format to new list format if needed
        if isinstance(raw_config, dict):
            for name, info in raw_config.items():
                if isinstance(info, dict):
                    config.append({
                        "name": name,
                        "url": info["url"],
                        "unit": info.get("unit", "L")
                    })
                else:
                    config.append({
                        "name": name,
                        "url": info,
                        "unit": "L"
                    })
        else:
            config = raw_config
    
    # Build categories with store info
    categories_with_stores = []
    valid_keys = set()
    for cat in config:
        store = get_store_from_url(cat.get("url", ""))
        cat_key = get_category_key(cat["name"], cat["url"])
        categories_with_stores.append({
            "name": cat["name"],
            "store": store,
            "key": cat_key
        })
        valid_keys.add(cat_key)
    
    # Filter products by valid category keys
    raw_products = data.get("products", {})
    products = [{"name": k, **v} for k, v in raw_products.items() if v.get('category') in valid_keys]
    
    return products, categories_with_stores, data.get("meta", {}).get("generated_at", "Unknown")

def build():
    products, categories, last_run = load_data()
    
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
    
    # Generate sidebar links with store badges
    sidebar_links = ""
    
    # Add favorites section link
    sidebar_links += f'''
        <a href="#favorites-section" class="nav-link nav-link-special" id="favorites-nav-link" style="display:none;">
            <span class="fav-icon">⭐</span>
            <span class="category-name">My Favorites (<span id="fav-count">0</span>)</span>
        </a>'''
    
    # Add sales section link if there are sales
    if sale_products:
        sidebar_links += f'''
        <a href="#sales-section" class="nav-link nav-link-sale">
            <span class="sale-icon">🔥</span>
            <span class="category-name">Sales ({len(sale_products)})</span>
        </a>'''
    
    sidebar_links += '<div style="border-bottom: 2px solid #2d3748; margin: 15px 0;"></div>'
    
    for i, cat in enumerate(categories):
        sidebar_links += f'''
        <a href="#cat_{i}" class="nav-link">
            <span class="store-label store-label-{cat['store']}">{cat['store']}</span>
            <span class="category-name">{cat['name']}</span>
        </a>'''
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Price Tracker</title>
    <meta charset="UTF-8">
    <style>
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background:#f0f2f5; margin:0; display: flex; color: #333; }}
        
        /* Sidebar stays fixed */
        .sidebar {{ width: 250px; background: #1a202c; color: #cbd5e0; height: 100vh; position: fixed; padding: 25px 20px; box-sizing: border-box; overflow-y: auto; z-index: 10; }}
        .sidebar h2 {{ font-size: 20px; color: white; margin-bottom: 5px; }}
        .last-run {{ font-size: 10px; color: #718096; margin-bottom: 25px; display:block; }}
        .nav-link {{ 
            display: flex;
            align-items: center;
            color: #a0aec0; 
            text-decoration: none; 
            padding: 12px 10px; 
            border-bottom: 1px solid #2d3748; 
            transition: 0.2s; 
            font-size: 14px; 
        }}
        .nav-link:hover {{ color: white; transform: translateX(5px); }}
        
        .nav-link-special {{ 
            background: linear-gradient(135deg, #805ad5 0%, #6b46c1 100%);
            border-radius: 8px;
            margin-bottom: 10px;
            border: none;
            color: white;
        }}
        .nav-link-special:hover {{ 
            transform: translateX(5px) scale(1.02); 
            box-shadow: 0 4px 12px rgba(128, 90, 213, 0.4);
        }}
        
        .nav-link-sale {{ 
            background: linear-gradient(135deg, #e53e3e 0%, #d69e2e 100%);
            border-radius: 8px;
            margin-bottom: 10px;
            border: none;
            color: white;
        }}
        .nav-link-sale:hover {{ 
            transform: translateX(5px) scale(1.02); 
            box-shadow: 0 4px 12px rgba(229, 62, 62, 0.4);
        }}
        
        .fav-icon, .sale-icon {{
            font-size: 18px;
            margin-right: 8px;
        }}
        
        .store-label {{ 
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: bold;
            text-transform: uppercase;
            width: 65px;
            text-align: center;
            flex-shrink: 0;
        }}
        .store-label-Barbora {{ background: #e53e3e; color: white; }}
        .store-label-Selver {{ background: #d69e2e; color: white; }}
        .store-label-Rimi {{ background: #e53e3e; color: white; }}
        .store-label-Coop {{ background: #2b6cb0; color: white; }}
        .store-label-Unknown {{ background: #718096; color: white; }}
        
        .category-name {{
            margin-left: 12px;
            flex: 1;
        }}
        
        .main {{ margin-left: 250px; flex: 1; padding: 0 40px 40px 40px; max-width: 1600px; margin-right: auto; }}

        /* STICKY HEADER */
        .header {{ 
            position: sticky; 
            top: 0; 
            background: #f0f2f5; 
            padding: 20px 0; 
            z-index: 100; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            border-bottom: 1px solid #e2e8f0;
        }}
        .controls {{ display: flex; gap: 10px; background: white; padding: 10px 20px; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); align-items: center; width: 100%; justify-content: space-between; }}
        
        .btn {{ padding: 8px 16px; border-radius: 6px; border: 1px solid #e2e8f0; cursor: pointer; font-weight: 600; font-size: 14px; background: white; color: #4a5568; transition: 0.2s; }}
        .btn-active {{ background: #2f855a; color: white; border-color: #2f855a; }}
        
        /* SEARCH INPUT */
        .search-box {{ padding: 8px 15px; border-radius: 6px; border: 1px solid #cbd5e0; width: 300px; font-size: 14px; outline: none; }}
        .search-box:focus {{ border-color: #2f855a; box-shadow: 0 0 0 2px rgba(47, 133, 90, 0.2); }}

        /* FAVORITES CAROUSEL SECTION */
        .favorites-section {{
            margin-top: 40px;
            scroll-margin-top: 100px;
            background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
            border-radius: 16px;
            padding: 30px;
            border: 2px solid #d6bcfa;
            box-shadow: 0 4px 12px rgba(128, 90, 213, 0.1);
            display: none;
        }}
        
        .favorites-title {{
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #805ad5 0%, #6b46c1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .favorites-subtitle {{
            color: #553c9a;
            font-size: 14px;
            margin-bottom: 25px;
        }}
        
        .carousel-container {{
            position: relative;
            overflow: hidden;
        }}
        
        .carousel-track {{
            display: flex;
            gap: 15px;
            transition: transform 0.3s ease;
        }}
        
        .carousel-card {{
            min-width: 320px;
            flex-shrink: 0;
        }}
        
        .carousel-btn {{
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid #d6bcfa;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 20px;
            color: #6b46c1;
            transition: 0.2s;
            z-index: 2;
        }}
        
        .carousel-btn:hover {{
            background: white;
            box-shadow: 0 4px 12px rgba(128, 90, 213, 0.3);
        }}
        
        .carousel-btn-left {{ left: -15px; }}
        .carousel-btn-right {{ right: -15px; }}
        
        .carousel-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
        }}
        
        .empty-favorites {{
            text-align: center;
            padding: 40px;
            color: #805ad5;
        }}
        
        .empty-favorites-icon {{
            font-size: 48px;
            margin-bottom: 10px;
        }}

        /* SALES SECTION - Compact Top 3 */
        .sales-section {{
            margin-top: 40px;
            scroll-margin-top: 100px;
            background: linear-gradient(135deg, #fff5f5 0%, #fffaf0 100%);
            border-radius: 16px;
            padding: 25px;
            border: 2px solid #feb2b2;
            box-shadow: 0 4px 12px rgba(229, 62, 62, 0.1);
        }}
        
        .sales-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .sales-title {{
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #e53e3e 0%, #d69e2e 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .expand-sales-btn {{
            background: white;
            border: 2px solid #feb2b2;
            color: #c53030;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            transition: 0.2s;
        }}
        
        .expand-sales-btn:hover {{
            background: #fff5f5;
            transform: translateY(-1px);
        }}
        
        .discount-badge {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: linear-gradient(135deg, #e53e3e 0%, #d69e2e 100%);
            color: white;
            font-size: 15px;
            font-weight: 800;
            padding: 6px 12px;
            border-radius: 6px;
            box-shadow: 0 2px 6px rgba(229, 62, 62, 0.3);
        }}
        
        .price-trend-up {{
            color: #e53e3e;
            font-size: 12px;
            font-weight: 700;
        }}
        
        .price-trend-down {{
            color: #2f855a;
            font-size: 12px;
            font-weight: 700;
        }}
        
        .price-trend-stable {{
            color: #718096;
            font-size: 12px;
            font-weight: 700;
        }}

        .cat-section {{ margin-top: 40px; scroll-margin-top: 100px; }}
        .cat-title {{ font-size: 22px; font-weight: 700; color: #2d3748; margin-bottom: 15px; padding-left: 15px; border-left: 5px solid #718096; }}
        .cat-title-Barbora {{ border-left-color: #e53e3e; }}
        .cat-title-Selver {{ border-left-color: #d69e2e; }}
        .cat-title-Rimi {{ border-left-color: #e53e3e; }}
        .cat-title-Coop {{ border-left-color: #2b6cb0; }}
        .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap: 15px; }}
        
        .card {{ background:white; border-radius:10px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.04); display:flex; gap:15px; text-decoration:none; color:inherit; height: 130px; position: relative; transition: 0.2s; border: 1px solid transparent; }}
        .card:hover {{ transform: translateY(-2px); border-color: #cbd5e0; }}

        .store-badge {{ position: absolute; top: 10px; right: 10px; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold; text-transform: uppercase; color: white; }}
        .store-Barbora {{ background: #e53e3e; }}
        .store-Selver {{ background: #d69e2e; }}
        .store-Rimi {{ background: #e53e3e; }}
        .store-Coop {{ background: #2b6cb0; }}

        .card img {{ width:70px; height:100%; object-fit:contain; }}
        .info {{ flex: 1; display: flex; flex-direction: column; justify-content: center; }}
        .name {{ font-size:12px; font-weight:700; line-height:1.4; max-height: 2.8em; overflow: hidden; margin-bottom: 5px; }}
        
        /* FAVORITE STAR BUTTON */
        .fav-btn {{
            position: absolute;
            bottom: 10px;
            right: 10px;
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 16px;
            transition: 0.2s;
            z-index: 5;
            pointer-events: auto;
        }}
        
        .fav-btn:hover {{
            border-color: #805ad5;
            transform: scale(1.1);
        }}
        
        .fav-btn.active {{
            background: #805ad5;
            border-color: #805ad5;
        }}
        
        /* PRICE STYLING */
        .price-container {{ display: flex; align-items: baseline; gap: 6px; }}
        .price {{ font-size:22px; font-weight:800; color: #2d3748; }}
        .price-sale {{ 
            background-color: #c6f6d5;
            color: inherit;
            padding: 3px 8px;
            border-radius: 5px;
            font-weight: 800;
        }}
        
        .price-old {{ font-size: 15px; color: #a0aec0; text-decoration: line-through; font-weight: 600; }}
        
        .per-l {{ color:#2f855a; font-weight:600; font-size:13px; }}
        
        .expand-bar {{ grid-column: 1 / -1; background: #fff; border: 1px solid #e2e8f0; color: #4a5568; text-align: center; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; margin-top: 10px; }}
        .hidden {{ display: none; }}
        #search-results-title {{ display: none; margin-top: 40px; color: #2f855a; border-left: 5px solid #2f855a; padding-left: 15px; font-size: 22px; font-weight: 700; }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>📊 Tracker</h2>
        <span class="last-run">Last Update: {last_run}</span>
        {sidebar_links}
    </div>

    <div class="main">
        <div class="header">
            <div class="controls">
                <div>
                    <button class="btn" id="sort-unit" onclick="setSort('price_per_unit')">Value (€/l v kg)</button>
                    <button class="btn btn-active" id="sort-total" onclick="setSort('latest_price')">Tüki hind</button>
                </div>
                <input type="text" id="search" class="search-box" placeholder="Search products (e.g. Heineken)..." oninput="handleSearch()">
            </div>
        </div>
        
        <div id="search-results-title">Search Results</div>
        <div id="search-grid" class="grid" style="margin-top: 20px;"></div>

        <div id="content"></div>
    </div>

<script>
const products = {json.dumps(products)};
const categories = {json.dumps(categories)};
const saleProducts = {json.dumps(sale_products)};
let currentSort = 'latest_price';
let favorites = [];
let carouselPosition = 0;

// Load favorites from localStorage
function loadFavorites() {{
    const stored = localStorage.getItem('priceTrackerFavorites');
    if (stored) {{
        try {{
            favorites = JSON.parse(stored);
            updateFavoritesUI();
        }} catch(e) {{
            console.error('Error loading favorites:', e);
            favorites = [];
        }}
    }}
}}

// Save favorites to localStorage
function saveFavorites() {{
    localStorage.setItem('priceTrackerFavorites', JSON.stringify(favorites));
    updateFavoritesUI();
}}

// Toggle favorite status
function toggleFavorite(productName, event) {{
    event.preventDefault();
    event.stopPropagation();
    
    const index = favorites.indexOf(productName);
    if (index > -1) {{
        favorites.splice(index, 1);
    }} else {{
        favorites.push(productName);
    }}
    saveFavorites();
    render();
    return false;
}}

// Update favorites UI
function updateFavoritesUI() {{
    const favCount = document.getElementById('fav-count');
    const favNavLink = document.getElementById('favorites-nav-link');
    
    if (favCount) favCount.textContent = favorites.length;
    if (favNavLink) {{
        favNavLink.style.display = favorites.length > 0 ? 'flex' : 'none';
    }}
}}

// Carousel navigation
function moveCarousel(direction) {{
    const track = document.querySelector('.carousel-track');
    const cards = document.querySelectorAll('.carousel-card');
    const cardWidth = 335; // 320px + 15px gap
    
    carouselPosition += direction;
    
    // Clamp position
    const maxPosition = Math.max(0, cards.length - 3);
    carouselPosition = Math.max(0, Math.min(carouselPosition, maxPosition));
    
    track.style.transform = `translateX(-${{carouselPosition * cardWidth}}px)`;
    
    // Update button states
    document.querySelector('.carousel-btn-left').disabled = carouselPosition === 0;
    document.querySelector('.carousel-btn-right').disabled = carouselPosition >= maxPosition;
}}

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
    
    // RENDER FAVORITES CAROUSEL
    const favSection = document.getElementById('favorites-section') || document.createElement('div');
    favSection.id = 'favorites-section';
    favSection.className = 'favorites-section';
    
    if (favorites.length > 0) {{
        const favoriteProducts = products.filter(p => favorites.includes(p.name));
        const favCardsHtml = favoriteProducts.map(p => {{
            const trend = getPriceTrend(p);
            return `<div class="carousel-card">${{cardWithTrend(p, trend)}}</div>`;
        }}).join('');
        
        favSection.innerHTML = `
            <div class="favorites-title">
                <span>⭐</span>
                My Favorites
            </div>
            <div class="favorites-subtitle">
                ${{favorites.length}} products tracked | Quick view of your favorite items
            </div>
            <div class="carousel-container">
                <button class="carousel-btn carousel-btn-left" onclick="moveCarousel(-1)" disabled>←</button>
                <div class="carousel-track">
                    ${{favCardsHtml}}
                </div>
                <button class="carousel-btn carousel-btn-right" onclick="moveCarousel(1)" ${{favoriteProducts.length <= 3 ? 'disabled' : ''}}>→</button>
            </div>
        `;
        favSection.style.display = 'block';
    }} else {{
        favSection.innerHTML = `
            <div class="favorites-title">
                <span>⭐</span>
                My Favorites
            </div>
            <div class="empty-favorites">
                <div class="empty-favorites-icon">🌟</div>
                <p>No favorites yet! Click the ⭐ button on any product to add it here.</p>
            </div>
        `;
        favSection.style.display = 'block';
    }}
    container.appendChild(favSection);
    
    // RENDER SALES SECTION - Top 3 only
    if (saleProducts.length > 0) {{
        const top3Sales = saleProducts.slice(0, 3);
        const restSales = saleProducts.slice(3);
        
        const salesHtml = `
            <div class="sales-section" id="sales-section">
                <div class="sales-header">
                    <div class="sales-title">
                        <span>🔥</span>
                        Top Deals
                    </div>
                    ${{restSales.length > 0 ? 
                        `<button class="expand-sales-btn" onclick="toggleAllSales()">+${{restSales.length}} more deals</button>` 
                        : ''}}
                </div>
                <div class="grid" id="top-sales-grid">${{top3Sales.map(p => cardWithDiscount(p)).join('')}}</div>
                <div class="grid hidden" id="all-sales-grid" style="margin-top:15px">${{restSales.map(p => cardWithDiscount(p)).join('')}}</div>
            </div>
        `;
        container.innerHTML += salesHtml;
    }}
    
    // RENDER REGULAR CATEGORIES
    const byCat = {{}};
    products.forEach(p => {{
        if(!byCat[p.category]) byCat[p.category] = [];
        byCat[p.category].push(p);
    }});

    categories.forEach((cat, index) => {{
        if (!byCat[cat.key]) return;
        const sorted = byCat[cat.key].sort((a,b)=> (a[currentSort] || 999) - (b[currentSort] || 999));
        const top5 = sorted.slice(0, 5);
        const rest = sorted.slice(5);
        const sectionId = "cat_" + index;
        const hiddenId = "hidden_" + index;

        let html = `
            <div class="cat-section" id="${{sectionId}}">
                <div class="cat-title cat-title-${{cat.store}}">${{cat.name}} <span style="font-size:13px; font-weight:normal; color:#718096">(${{sorted.length}} items)</span></div>
                <div class="grid">${{top5.map(p=>card(p)).join('')}}</div>
        `;
        if (rest.length > 0) {{
            html += `<div id="${{hiddenId}}" class="grid hidden" style="margin-top:15px">${{rest.map(p=>card(p)).join('')}}</div>
                     <div class="expand-bar" onclick="toggle('${{hiddenId}}', this)">Show ${{rest.length}} more deals ▾</div>`;
        }}
        html += `</div>`;
        container.innerHTML += html;
    }});
    
    if (document.getElementById('search').value.length >= 2) handleSearch();
}}

function toggleAllSales() {{
    const allSalesGrid = document.getElementById('all-sales-grid');
    const btn = event.target;
    const isHidden = allSalesGrid.classList.toggle('hidden');
    btn.textContent = isHidden ? `+${{saleProducts.length - 3}} more deals` : 'Show less';
}}

function toggle(id, btn) {{
    const el = document.getElementById(id);
    const isHidden = el.classList.toggle('hidden');
    btn.innerHTML = isHidden ? `Show more deals ▾` : "Collapse ▴";
}}

function cardWithTrend(p, trend) {{
    const unitLabel = p.unit_label || 'L';
    const unitPrice = p.price_per_unit || p.price_per_litre || 0;
    const isFav = favorites.includes(p.name);
    const safeName = p.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    
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
                <span class="${{trend.class}}">${{trend.symbol}}</span>
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
    const safeName = p.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    
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
    const safeName = p.name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
    
    let priceDisplay = `<div class="price">€${{p.latest_price.toFixed(2)}}</div>`;
    
    // LOGIC FOR PRICE CHANGES
    if (entries.length > 1) {{
        const currentP = p.latest_price;
        const previousP = entries[entries.length - 2].p;
        
        if (currentP < previousP) {{
            // PRICE DROPPED (Sale)
            priceDisplay = `
                <div class="price-container">
                    <span class="price price-sale">€${{currentP.toFixed(2)}}</span>
                    <span class="price-old">€${{previousP.toFixed(2)}}</span>
                </div>`;
        }} else if (currentP > previousP) {{
            // PRICE INCREASED
            priceDisplay = `
                <div class="price-container">
                    <span class="price">€${{currentP.toFixed(2)}}</span>
                    <span style="font-size: 10px; color: #e53e3e;">▲</span>
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

// Initialize
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
    print(f"Favorites feature enabled with localStorage")

if __name__ == "__main__":
    build()