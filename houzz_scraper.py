import sys
import asyncio
import json
import os
from playwright.async_api import async_playwright
import pandas as pd
from datetime import datetime

# --- GİRDİLER (ABD Formatı) ---
# Örn: category="roofing-contractors", location="New-York--NY"
CATEGORY = sys.argv[1] if len(sys.argv) > 1 else "roofing-contractors"
LOCATION = sys.argv[2] if len(sys.argv) > 2 else "New-York--NY"
DB_FILE = "houzz_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

async def scrape_houzz():
    old_data = load_db()
    existing_names = {item["Business Name"] for item in old_data if "Business Name" in item}
    
    async with async_playwright() as p:
        # ABD siteleri için gizlilik (stealth) önemli
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        # Houzz URL yapısı
        base_url = f"https://www.houzz.com/professionals/{CATEGORY}/c/{LOCATION}"
        print(f"🚀 Houzz Tarama Başladı: {CATEGORY} in {LOCATION}")
        
        results = []
        page_num = 1
        
        while page_num <= 5: # İlk 5 sayfayı tara (Limit artırılabilir)
            print(f"📄 Sayfa {page_num} taranıyor...")
            current_url = f"{base_url}/p/{(page_num-1)*15}" if page_num > 1 else base_url
            await page.goto(current_url, wait_until="domcontentloaded")
            await asyncio.sleep(3)

            # Müteahhit kartlarını bul
            cards = await page.query_selector_all(".hz-pro-search-result")
            
            for card in cards:
                try:
                    name_el = await card.query_selector(".pro-title")
                    name = await name_el.inner_text() if name_el else "Unknown"

                    if name in existing_names: continue

                    # Telefon numarasını açmak için butona bas (Houzz klasiği)
                    try:
                        phone_btn = await card.query_selector("button[data-item-id='phone']")
                        if phone_btn:
                            await phone_btn.click()
                            await asyncio.sleep(1)
                    except: pass

                    # Verileri topla
                    results.append({
                        "Business Name": name,
                        "Category": CATEGORY,
                        "Location": LOCATION,
                        "Date Scraped": datetime.now().strftime('%Y-%m-%d')
                    })
                    existing_names.add(name)
                    print(f"✅ Found: {name}")
                except: continue

            # "Next" butonu kontrolü
            next_btn = await page.query_selector("a.hz-pagination-link--next")
            if not next_btn: break
            page_num += 1

        await browser.close()
        
        # Kayıt İşlemleri
        final_data = old_data + results
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        
        pd.DataFrame(final_data).to_excel("houzz_leads.xlsx", index=False)
        print(f"🏁 Bitti! Toplam {len(final_data)} lead veritabanında.")

if __name__ == "__main__":
    asyncio.run(scrape_houzz())
