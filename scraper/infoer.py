import requests
from bs4 import BeautifulSoup
import time
import random
# import pandas as pd
import urllib.parse

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.directinfo.ma/recherche",
    "Origin": "https://www.directinfo.ma",
    "Content-Type": "application/x-www-form-urlencoded",  # For form POST
})

def search_company_form(company_name: str, max_retries=1):
    # Warmup: Get search page for cookies/form state
    init_url = "https://www.directinfo.ma/recherche"
    init_resp = s.get(init_url, timeout=15)
    if init_resp.status_code != 200:
        print(f"[!] Init failed: {init_resp.status_code}")
        return []
    
    # Build form data (from your debug/inspect)
    encoded_name = urllib.parse.quote_plus(company_name.strip())
    payload = {
        "denomination": company_name,  # Or encoded_name if needed
        "type_recherche": "societe",  # Company search
        "recherche_avancee": "0",     # Basic search flag
        "page": "1",
        # Add more fields if debug shows (e.g., _token if CSRF present)
    }
    
    for attempt in range(max_retries):
        time.sleep(random.uniform(4, 7))  # Longer delay for gov site
        resp = s.post("https://www.directinfo.ma/recherche/resultats",  # Adjust if debug shows different action
                      data=payload, timeout=20)
        
        if resp.status_code == 403:
            print(f"[!] 403 on POST attempt {attempt+1}. Trying proxy or VPN.")
            # Optional: Add proxies here
            continue
        elif resp.status_code != 200:
            print(f"[!] HTTP {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        
        # Parse table (adapt from actual HTML; inspect for classes/IDs)
        rows = soup.select("table.resultats tr")[1:]  # Skip header
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 5:
                link = cols[0].find("a")
                results.append({
                    "Name": cols[0].get_text(strip=True),
                    "City": cols[1].get_text(strip=True),
                    "RC": cols[2].get_text(strip=True),
                    "Legal Form": cols[3].get_text(strip=True),
                    "Creation Date": cols[4].get_text(strip=True),
                    "Status": cols[5].get_text(strip=True) if len(cols) > 5 else "",
                    "Detail URL": "https://www.directinfo.ma" + (link["href"] if link else ""),
                })
        if results:
            return results
        print(f"[!] No results parsed—check HTML\n\n\n\n====\n\n\n: {resp.text}")
    
    return []

# # Usage
# companies = ["Maroc Telecom", "Attijariwafa Bank"]
# all_data = []
# for name in companies:
#     print(f"Searching: {name}")
#     data = search_company_form(name)
#     all_data.extend(data)
#     print(f"→ {len(data)} results")

def get_business_details(companies_to_search=['mode 777']):

    # all_results = []
    # for name in companies_to_search:
    #     data = search_company_api(name)
    #     all_results.extend(data)

    all_results = []
    for name in companies_to_search:
        print(f"Searching API for: {name}")
        data = search_company_form(name)
        all_results.extend(data)
        print(f"→ {len(data)} results:\n\n")
        print(data)

    # # Save to CSV
    # if all_results:
    #     df = pd.DataFrame(all_results)
    #     df.to_csv("directinfo_api_results.csv", index=False, encoding="utf-8-sig")
    #     print(f"\nDone! {len(all_results)} records saved to directinfo_api_results.csv")
    # else:
    #     print("No results—check errors above.")