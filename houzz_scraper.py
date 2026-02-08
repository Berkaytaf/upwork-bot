import sys
import asyncio
import json
import os
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime

# --- AYARLAR ---
CATEGORY = sys.argv[1] if len(sys.argv) > 1 else "roofing-contractors"
LOCATION = sys.argv[2] if len(sys.argv) > 2 else "New-York--NY"
DB_FILE = "houzz_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def generate_houzz_dashboard(data):
    """USA Lead Gen için şık bir HTML Dashboard oluşturur."""
    if not data: return
    df = pd.DataFrame(data)
    
    # En yeni veriyi en üstte göster (ABD formatında tarih sıralaması)
    if 'Date Scraped' in df.columns:
        df = df.sort_values(by='Date Scraped', ascending=False)
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Houzz Hunter USA Dashboard</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ background-color: #f0f2f5; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            .container {{ margin-top: 50px; }}
            .stats-card {{ background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white; border-radius: 15px; padding: 20px; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }}
            .table-container {{ background: white; border-radius: 15px; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            .badge-usa {{ background-color: #ff4d4d; color: white; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="stats-card text-center">
                <h1 class="display-5">🏠 Houzz Hunter Dashboard</h1>
                <p class="lead">USA Contractor Leads Database</p>
                <div class="d-flex justify-content-center gap-4 mt-3">
                    <div><h5>Total Leads</h5><h3>{len(data)}</h3></div>
                    <div><h5>Region</h5><h3>USA</h3></div>
                    <div><h5>Last Sync</h5><h3>{datetime.now().strftime('%Y-%m-%d %H:%M')}</h3></div>
                </div>
            </div>

            <div class="table-container">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Business Name</th>
                            <th>Category</th>
                            <th>Location</th>
                            <th>Date Found</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([f"<tr><td><strong>{row.get('Business Name','-')}</strong></td><td>{row.get('Category','-')}</td><td><span class='badge bg-info text-dark'>{row.get('Location','-')}</span></td><td>{row.get('Date Scraped','-')}</td></tr>" for _, row in df.iterrows()])}
                    </tbody>
                </table>
            </div>
            <p class="text-center mt-4 text-muted">Lead Gen Automation Engine v2.0 - Developed for USA Market</p>
        </div>
    </body>
    </html>
    """
    # Eczane botuyla karışmaması için ismini index_houzz.html yapıyoruz
    with open("index_houzz.html", "w", encoding="utf-8") as f:
        f.write(html_content)

async def scrape_houzz():
    old_data = load_db()
    existing_names = {item["Business Name"] for item in old_data if "Business Name" in item}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0...", viewport={{'width': 1280, 'height': 800}})
        page = await context.new_page()

        base_url = f"https://www.houzz.com/professionals/{{CATEGORY}}/c/{{LOCATION}}"
        print(f"🚀 USA Hunting: {{CATEGORY}} in {{LOCATION}}")
        
        results = []
        await page.goto(base_url, wait_until="domcontentloaded")
        await asyncio.sleep(5)

        # Kartları bul
        cards = await page.query_selector_all(".hz-pro-search-result")
        for card in cards[:20]: # Test için 20
            try:
                name_el = await card.query_selector(".pro-title")
                name = await name_el.inner_text() if name_el else "Unknown"

                if name in existing_names: continue

                results.append({{
                    "Business Name": name,
                    "Category": CATEGORY,
                    "Location": LOCATION,
                    "Date Scraped": datetime.now().strftime('%Y-%m-%d')
                }})
                existing_names.add(name)
                print(f"✅ Found: {{name}}")
            except: continue

        await browser.close()
        
        # Kaydet ve Dashboard oluştur
        final_data = old_data + results
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        
        generate_houzz_dashboard(final_data)
        pd.DataFrame(final_data).to_excel("houzz_leads.xlsx", index=False)
        print(f"🏁 Dashboard updated: index_houzz.html")

if __name__ == "__main__":
    asyncio.run(scrape_houzz())
