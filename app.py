from flask import Flask, render_template_string, request, jsonify, make_response
import json, os, subprocess, sys, csv, io

app = Flask(__name__)

HISTORY_FILE = "alcohol_history.json"
CONFIG_FILE = "categories.json"

# --- DATA HELPERS ---
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

def load_config():
    """Load config - supports both old dict format and new list format"""
    if os.path.exists(CONFIG_FILE):
        try:
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
                return new_format
            return data
        except: 
            return []
    return []

def get_category_key(category_entry):
    """Generate unique key for a category using name + store"""
    store = get_store_from_url(category_entry.get("url", ""))
    return f"{store}:{category_entry['name']}"

def load_products():
    if not os.path.exists(HISTORY_FILE): return []
    try:
        config = load_config()
        # Build set of valid category keys
        valid_keys = {get_category_key(cat) for cat in config}
        
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            raw_products = data.get("products", {})
            # Filter products by valid category keys
            return [{"name": k, **v} for k, v in raw_products.items() if v.get('category') in valid_keys]
    except: 
        return []

# --- ROUTES ---

@app.route('/')
def index():
    products = load_products()
    config = load_config()
    # Build categories with store info
    categories_with_stores = []
    for cat in config:
        store = get_store_from_url(cat.get("url", ""))
        categories_with_stores.append({
            "name": cat["name"],
            "store": store,
            "key": get_category_key(cat)
        })
    
    return render_template_string(DASHBOARD_HTML, products_json=json.dumps(products), categories=categories_with_stores)

@app.route('/settings')
def settings():
    config = load_config()
    return render_template_string(SETTINGS_HTML, config=config)

@app.route('/update-config', methods=['POST'])
def update_config():
    # Save as list format
    config_list = request.json
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_list, f, indent=2)
    return jsonify({"status": "success"})

@app.route('/download-csv')
def download_csv():
    products = load_products()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Store', 'Category', 'Name', 'Price', 'Price/L'])
    for p in products:
        writer.writerow([p.get('store',''), p.get('category',''), p['name'], p.get('latest_price',0), p.get('price_per_litre',0)])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=price_export.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/run-scan', methods=['POST'])
def run_scan():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    base_path = os.path.dirname(os.path.abspath(__file__))
    scraper_path = os.path.join(base_path, "scraper2.py")
    subprocess.run([sys.executable, scraper_path], env=env)
    return jsonify({"status": "finished"})

@app.route('/run-single-scan', methods=['POST'])
def run_single_scan():
    data = request.json
    category_key = data.get('category')
    
    if not category_key:
        return jsonify({"status": "error", "message": "No category specified"}), 400
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["SCRAPE_SINGLE_CATEGORY"] = category_key  # Pass category key as env variable
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    scraper_path = os.path.join(base_path, "scraper2.py")
    subprocess.run([sys.executable, scraper_path], env=env)
    
    return jsonify({"status": "finished", "category": category_key})

@app.route('/rebuild-site', methods=['POST'])
def rebuild_site():
    try:
        import build_site
        build_site.build()
        return jsonify({"status": "success", "message": "Website rebuilt successfully"})
    except ImportError:
        return jsonify({"status": "error", "message": "build_site.py not found"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- HTML TEMPLATES ---

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Price Tracker Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background:#f0f2f5; margin:0; display: flex; color: #333; }
        .sidebar { width: 250px; background: #1a202c; color: #cbd5e0; height: 100vh; position: fixed; padding: 25px 20px; box-sizing: border-box; overflow-y: auto; }
        .sidebar h2 { font-size: 20px; color: white; margin-bottom: 25px; border-bottom: 1px solid #4a5568; padding-bottom: 10px; }
        .nav-link { display: block; color: #a0aec0; text-decoration: none; padding: 12px 10px; border-bottom: 1px solid #2d3748; transition: 0.2s; font-size: 14px; position: relative; }
        .nav-link:hover { color: white; transform: translateX(5px); }
        .store-label { 
            display: inline-block;
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: bold;
            text-transform: uppercase;
            margin-right: 8px;
            vertical-align: middle;
        }
        .store-label-Barbora { background: #e53e3e; color: white; }
        .store-label-Selver { background: #d69e2e; color: white; }
        .store-label-Rimi { background: #e53e3e; color: white; }
        .store-label-Coop { background: #2b6cb0; color: white; }
        .store-label-Unknown { background: #718096; color: white; }
        .admin-link { margin-top: 40px; display: block; color: #f6ad55; text-decoration: none; font-weight: bold; }
        
        .main { margin-left: 250px; flex: 1; padding: 30px 40px; max-width: 1200px; }
        .header { display: flex; justify-content: space-between; align-items: center; background: white; padding: 15px 25px; border-radius: 12px; margin-bottom: 30px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .btn { padding: 8px 16px; border-radius: 6px; border: 1px solid #e2e8f0; cursor: pointer; text-decoration: none; font-weight: 600; font-size: 14px; background: white; color: #4a5568; }
        .btn-active { background: #2f855a; color: white; border-color: #2f855a; }

        .cat-section { margin-bottom: 50px; scroll-margin-top: 100px; }
        .cat-title { font-size: 22px; font-weight: 700; color: #2d3748; margin-bottom: 15px; border-left: 5px solid #2f855a; padding-left: 15px; }
        .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap: 15px; }
        .card { background:white; border-radius:10px; padding:15px; box-shadow:0 2px 4px rgba(0,0,0,0.04); display:flex; gap:15px; text-decoration:none; color:inherit; height: 120px; border: 1px solid transparent; transition: 0.2s; position: relative; }
        .card:hover { transform: translateY(-2px); border-color: #cbd5e0; }

        .store-badge { 
            position: absolute; top: 10px; right: 10px; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold; text-transform: uppercase; background: #718096; color: white;
        }
        .store-Barbora { background: #e53e3e; }
        .store-Selver { background: #d69e2e; }
        .store-Rimi { background: #e53e3e; }
        .store-Coop { background: #2b6cb0; }

        .card img { width:70px; height:100%; object-fit:contain; }
        .info { flex: 1; display: flex; flex-direction: column; justify-content: center; }
        .name { font-size:12px; font-weight:700; line-height:1.4; max-height: 2.8em; overflow: hidden; margin-bottom: 5px; }
        .price { font-size:18px; font-weight:800; color: #2d3748; }
        .per-l { color:#2f855a; font-weight:600; font-size:13px; }
        
        .expand-bar { grid-column: 1 / -1; background: #fff; border: 1px solid #e2e8f0; color: #4a5568; text-align: center; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; margin-top: 10px; }
        .expand-bar:hover { background: #f7fafc; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>📊 Tracker</h2>
        {% for cat in categories %}
        <a href="#cat_{{ loop.index }}" class="nav-link">
            <span class="store-label store-label-{{ cat.store }}">{{ cat.store }}</span>
            {{ cat.name }}
        </a>
        {% endfor %}
        <a href="/settings" class="admin-link">⚙️ Manage & Scrape</a>
    </div>

    <div class="main">
        <div class="header">
            <div>
                <button class="btn btn-active" id="sort-unit" onclick="setSort('price_per_litre')">Value (€/L)</button>
                <button class="btn" id="sort-total" onclick="setSort('latest_price')">Price</button>
            </div>
            <a href="/download-csv" class="btn">📥 Export CSV</a>
        </div>
        <div id="content"></div>
    </div>

<script>
const products = {{ products_json | safe }};
const categoryOrder = {{ categories | tojson }};
let currentSort = 'price_per_litre';

function setSort(key){
    currentSort = key;
    document.querySelectorAll('.header .btn').forEach(b=>b.classList.remove('btn-active'));
    document.getElementById(key==='latest_price'?'sort-total':'sort-unit').classList.add('btn-active');
    render();
}

function render(){
    const container = document.getElementById("content");
    container.innerHTML = "";
    const byCat = {};
    products.forEach(p => {
        if(!byCat[p.category]) byCat[p.category] = [];
        byCat[p.category].push(p);
    });

    // Render in the order from categoryOrder
    categoryOrder.forEach((cat, index) => {
        if (!byCat[cat.key]) return; // Skip if no products in this category
        
        const sorted = byCat[cat.key].sort((a,b)=> (a[currentSort] || 999) - (b[currentSort] || 999));
        const top5 = sorted.slice(0, 5);
        const rest = sorted.slice(5);
        const sectionId = "cat_" + (index + 1);
        const hiddenId = "hidden_" + sectionId;

        let html = `
            <div class="cat-section" id="${sectionId}">
                <div class="cat-title">${cat.name} <span style="font-size:13px; font-weight:normal; color:#718096">(${sorted.length} items)</span></div>
                <div class="grid">${top5.map(p=>card(p)).join('')}</div>
        `;
        if (rest.length > 0) {
            html += `<div id="${hiddenId}" class="grid hidden" style="margin-top:15px">${rest.map(p=>card(p)).join('')}</div>
                     <div class="expand-bar" onclick="toggle('${hiddenId}', this)">Show ${rest.length} more deals ▾</div>`;
        }
        html += `</div>`;
        container.innerHTML += html;
    });
}

function toggle(id, btn) {
    const el = document.getElementById(id);
    const isHidden = el.classList.toggle('hidden');
    btn.innerHTML = isHidden ? "Show more deals ▾" : "Collapse ▴";
}

function card(p){
    const storeClass = 'store-' + (p.store || 'Unknown');
    return `<a href="${p.url}" target="_blank" class="card">
        <span class="store-badge ${storeClass}">${p.store || 'UNK'}</span>
        <img src="${p.img}" onerror="this.src='https://via.placeholder.com/60x90?text=No+Img'">
        <div class="info">
            <div class="name">${p.name}</div>
            <div class="price">€${p.latest_price.toFixed(2)}</div>
            <div class="per-l">€${(p.price_per_litre||0).toFixed(2)} / L</div>
        </div>
    </a>`;
}
render();
</script>
</body>
</html>
"""

SETTINGS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Settings</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 40px; display: flex; justify-content: center; }
        .box { background: white; width: 100%; max-width: 1000px; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        .row { display: flex; gap: 10px; margin-bottom: 12px; align-items: center; background: #f7fafc; padding: 10px; border-radius: 8px; cursor: move; border: 2px solid transparent; transition: all 0.2s; }
        .row:hover { background: #edf2f7; border-color: #cbd5e0; }
        .row.dragging { opacity: 0.5; border-color: #3182ce; }
        .row.drag-over { border-top: 3px solid #3182ce; }
        
        .drag-handle { cursor: grab; font-size: 18px; color: #a0aec0; padding: 0 8px; user-select: none; }
        .drag-handle:active { cursor: grabbing; }
        
        input { padding: 10px; border: 1px solid #e2e8f0; border-radius: 6px; }
        .cat-name { width: 150px; }
        .cat-url { flex: 1; }
        .cat-unit { width: 80px; padding: 10px; border-radius: 6px; border: 1px solid #e2e8f0; }
        .btn-del { background: #fed7d7; color: #c53030; border: none; padding: 10px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; }
        .btn-scrape-single { background: #38a169; color: white; border: none; padding: 10px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; white-space: nowrap; }
        .btn-scrape-single:hover { background: #2f855a; }
        .btn-scrape-single:disabled { background: #cbd5e0; cursor: not-allowed; }
        
        .btn { padding: 12px 24px; border-radius: 6px; border: none; font-weight: 600; cursor: pointer; }
        .btn-save { background: #3182ce; color: white; }
        .btn-scan { background: #38a169; color: white; width: 100%; margin-top: 25px; font-size: 18px; }
        .hint { color: #718096; font-size: 13px; margin-top: 10px; font-style: italic; }
        .status-msg { text-align: center; font-weight: bold; margin-top: 15px; padding: 10px; border-radius: 6px; display: none; }
        .status-success { background: #c6f6d5; color: #22543d; display: block; }
        .status-loading { background: #bee3f8; color: #2c5282; display: block; }
    </style>
</head>
<body>
    <div class="box">
        <a href="/" style="text-decoration:none; color:#718096; font-weight:600;">← Back to Dashboard</a>
        <h2>⚙️ Scraper Settings</h2>
        <p class="hint">💡 Drag rows using the ☰ handle to reorder categories</p>
        <div id="config-container">
            {% for cat in config %}
            <div class="row" draggable="true">
                <span class="drag-handle">☰</span>
                <input type="text" class="cat-name" value="{{ cat.name }}" data-original-url="{{ cat.url }}">
                <input type="text" class="cat-url" value="{{ cat.url }}">
                <select class="cat-unit">
                    <option value="L" {% if cat.unit == "L" %}selected{% endif %}>€/L</option>
                    <option value="kg" {% if cat.unit == "kg" %}selected{% endif %}>€/kg</option>
                </select>
                <button class="btn-scrape-single" onclick="scrapeSingle(this, '{{ cat.url }}')">🔍 Scrape</button>
                <button class="btn-del" onclick="this.parentElement.remove()">🗑️</button>
            </div>
            {% endfor %}
        </div>
        <div style="margin-top:15px; display:flex; gap:10px;">
            <button class="btn" onclick="addRow()">+ Add New</button>
            <button class="btn btn-save" onclick="save()">💾 Save Changes</button>
            <button class="btn" style="background: #805ad5; color: white;" onclick="rebuildSite()">🔨 Rebuild Site</button>
        </div>
        <p id="singleMsg" class="status-msg"></p>
        <hr style="margin: 30px 0; border:0; border-top:1px solid #e2e8f0;">
        <button id="scanBtn" class="btn btn-scan" onclick="runFull()">🚀 RUN FULL SCRAPE (ALL CATEGORIES)</button>
        <p id="msg" class="status-msg"></p>
    </div>
<script>
    let draggedElement = null;

    function getStoreFromUrl(url) {
        const lower = url.toLowerCase();
        if (lower.includes('barbora')) return 'Barbora';
        if (lower.includes('selver')) return 'Selver';
        if (lower.includes('rimi')) return 'Rimi';
        if (lower.includes('coop')) return 'Coop';
        return 'Unknown';
    }

    function getCategoryKey(name, url) {
        const store = getStoreFromUrl(url);
        return `${store}:${name}`;
    }

    function addRow() {
        const div = document.createElement('div'); 
        div.className = 'row';
        div.draggable = true;
        div.innerHTML = `<span class="drag-handle">☰</span>
                         <input type="text" class="cat-name" placeholder="Name" data-original-url=""> 
                         <input type="text" class="cat-url" placeholder="URL"> 
                         <select class="cat-unit"><option value="L">€/L</option><option value="kg">€/kg</option></select>
                         <button class="btn-scrape-single" onclick="scrapeSingle(this, '')" disabled>🔍 Scrape</button>
                         <button class="btn-del" onclick="this.parentElement.remove()">🗑️</button>`;
        document.getElementById('config-container').appendChild(div);
        setupDragListeners(div);
    }

    function setupDragListeners(row) {
        row.addEventListener('dragstart', function(e) {
            draggedElement = this;
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });

        row.addEventListener('dragend', function() {
            this.classList.remove('dragging');
            document.querySelectorAll('.row').forEach(r => r.classList.remove('drag-over'));
        });

        row.addEventListener('dragover', function(e) {
            e.preventDefault();
            if (draggedElement !== this) {
                const container = document.getElementById('config-container');
                const afterElement = getDragAfterElement(container, e.clientY);
                if (afterElement == null) {
                    container.appendChild(draggedElement);
                } else {
                    container.insertBefore(draggedElement, afterElement);
                }
            }
        });
    }

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.row:not(.dragging)')];
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    // Initialize drag listeners for existing rows
    document.querySelectorAll('.row').forEach(row => setupDragListeners(row));

    async function scrapeSingle(btn, url) {
        const row = btn.closest('.row');
        const name = row.querySelector('.cat-name').value;
        const currentUrl = row.querySelector('.cat-url').value;
        const originalUrl = row.querySelector('.cat-name').dataset.originalUrl;
        
        const urlToUse = originalUrl || currentUrl;
        
        if (!urlToUse || !name) {
            alert('Please save this category before scraping it.');
            return;
        }
        
        const categoryKey = getCategoryKey(name, urlToUse);
        
        const singleMsg = document.getElementById('singleMsg');
        singleMsg.className = 'status-msg status-loading';
        singleMsg.innerText = `⏳ Scraping "${name}"...`;
        
        btn.disabled = true;
        document.querySelectorAll('.btn-scrape-single').forEach(b => b.disabled = true);
        
        try {
            await fetch('/run-single-scan', { 
                method: 'POST', 
                headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({ category: categoryKey })
            });
            
            singleMsg.className = 'status-msg status-success';
            singleMsg.innerText = `✅ Finished scraping "${name}"`;
            
            setTimeout(() => {
                location.reload();
            }, 1500);
        } catch (error) {
            singleMsg.className = 'status-msg';
            singleMsg.style.background = '#fed7d7';
            singleMsg.style.color = '#c53030';
            singleMsg.style.display = 'block';
            singleMsg.innerText = `❌ Error scraping "${name}"`;
            document.querySelectorAll('.btn-scrape-single').forEach(b => b.disabled = false);
        }
    }

    async function save() {
        const rows = document.querySelectorAll('.row');
        let configList = [];
        rows.forEach(row => {
            const name = row.querySelector('.cat-name').value;
            const url = row.querySelector('.cat-url').value;
            const unit = row.querySelector('.cat-unit').value;
            if(name && url) {
                configList.push({
                    "name": name,
                    "url": url,
                    "unit": unit
                });
            }
        });
        await fetch('/update-config', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(configList) });
        alert("Settings Saved!");
        location.reload();
    }

    async function rebuildSite() {
        const singleMsg = document.getElementById('singleMsg');
        singleMsg.className = 'status-msg status-loading';
        singleMsg.innerText = '⏳ Rebuilding static site...';
        
        try {
            const response = await fetch('/rebuild-site', { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                singleMsg.className = 'status-msg status-success';
                singleMsg.innerText = '✅ Site rebuilt successfully!';
                setTimeout(() => {
                    singleMsg.style.display = 'none';
                }, 3000);
            } else {
                singleMsg.className = 'status-msg';
                singleMsg.style.background = '#fed7d7';
                singleMsg.style.color = '#c53030';
                singleMsg.style.display = 'block';
                singleMsg.innerText = `❌ Error: ${data.message}`;
            }
        } catch (error) {
            singleMsg.className = 'status-msg';
            singleMsg.style.background = '#fed7d7';
            singleMsg.style.color = '#c53030';
            singleMsg.style.display = 'block';
            singleMsg.innerText = '❌ Error rebuilding site';
        }
    }

    async function runFull() {
        const msg = document.getElementById('msg');
        const btn = document.getElementById('scanBtn');
        
        btn.disabled = true;
        msg.className = 'status-msg status-loading';
        msg.innerText = "⏳ Running full scrape on all categories...";
        
        await fetch('/run-scan', { method: 'POST' });
        
        msg.className = 'status-msg status-success';
        msg.innerText = "✅ Full scrape complete!";
        
        setTimeout(() => {
            location.href = '/';
        }, 1500);
    }
</script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)