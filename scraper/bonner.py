
import requests
from bs4 import BeautifulSoup
import pandas as pd
import random
import time
import json

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from scraper import helper
from scraper import constants as C

LISTING_BASE_URL = C.BDC_LISTING_BASE_URL
LISTING_PAGE_PARAM = "page"

RESULTS_BASE_URL = C.BDC_RESULTS_BASE_URL
RESULTS_PAGE_PARAM = "page"

# USER_AGENTS = [
#     # Windows — Chrome
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",

#     # Windows — Firefox
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",

#     # Windows — Edge
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",

#     # macOS — Safari
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",

#     # macOS — Chrome
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",

#     # Linux — Firefox
#     "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
#     "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",

#     # Linux — Chrome
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
# ]


def get_headers():
    return {
        "User-Agent": helper.getUa(),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        # "User-Agent": random.choice(USER_AGENTS),
    }


def fetch_results_page(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=get_headers(), timeout=15)
            s = r.status_code
            if s == 200:
                return r.text
            else:
                print("[!!!!!] Error : status code was not 200:", s)
        except Exception as e:
            print("[!!!!!] Exception:", e)

        print(f"[-----] Retrying ({ attempt + 1 }/{ retries }) …")
        time.sleep(random.random())

    return None


def get_results_bdc(card):
    """
    Extracts data from a single item card
    """
    
    ref = card.select_one(".entreprise__middleSubCard div.font-bold.table__links")
    reference = ref.get_text(strip=True).replace("Référence :", "").strip() if ref else None

    title_div = card.select_one('.entreprise__middleSubCard div[data-bs-toggle="tooltip"]')
    title = title_div.get_text(strip=True).replace("Objet :", "").strip() if title_div else None

    client_div = card.find("span", string=lambda x: x and "Acheteur" in x)
    client = client_div.parent.get_text(strip=True).replace("Acheteur :", "") if client_div else None

    date_div = card.find("span", string=lambda x: x and "Date de publication" in x)
    date_pub = date_div.parent.get_text(strip=True).replace("Date de publication du résultat :", "") if date_div else None

    right_top = card.select_one(".entreprise__rightSubCard--top")
    if right_top:
        is_infructueux = "infructueux" in right_top.get_text().lower()

        n_devis_el = right_top.select_one("span:-soup-contains('Nombre de devis')")
        if n_devis_el:
            n_devis_span = n_devis_el.find("span", class_="font-bold")
            n_devis = n_devis_span.get_text(strip=True) if n_devis_span else None
        else:
            n_devis = None
        
        if not is_infructueux:

            entreprise_el = right_top.select_one("span:-soup-contains('Entreprise attributaire')")
            if entreprise_el:
                entreprise_span = entreprise_el.find("span", class_="font-bold")
                entreprise_attr = entreprise_span.get_text(strip=True) if entreprise_span else None
            else:
                entreprise_attr = None

            montant_el = right_top.select_one("span:-soup-contains('Montant')")
            if montant_el:
                montant_span = montant_el.find("span", class_="font-bold")
                montant_ttc = montant_span.get_text(strip=True) if montant_span else None
            else:
                montant_ttc = None

        else:
            n_devis = entreprise_attr = montant_ttc = None

    rabat_tz = pytz.timezone("Africa/Casablanca")
    naive_dt = datetime.strptime(date_pub, "%d/%m/%Y %H:%M")
    published_dt = rabat_tz.localize(naive_dt)

    cleaned = montant_ttc.replace(" ", "").replace(",", ".").replace("MAD", "")
    montant_decimal_ttc = Decimal(cleaned)

    bdc_result = {
        'reference': reference,
        'title': title,
        'client': client,
        'unsuccessful': is_infructueux,
        'bids_count': n_devis,
        'winner_entity': entreprise_attr,
        "deliberated" : published_dt,
        "winner_amount" : montant_decimal_ttc
    }

    return bdc_result


def has_next_page(soup):
    next_link = soup.find("a", string=lambda x: x and ("Suivant" in x))
    return next_link is not None


def get_and_save_results():

    errors_happened = False
    handled_items = 0
    clients_created = 0
    bdc_created = 0

    page = 1
    while True:
        url = f"{RESULTS_BASE_URL}&{RESULTS_PAGE_PARAM}={page}"
        print("[=====] Fetching page :", page)
        
        html = fetch_results_page(url)
        if not html:
            errors_happened = True
            break

        soup = BeautifulSoup(html, "lxml")
        container = soup.select_one("div.mt-4.py-3.content__subBox")

        if not container:
            errors_happened = True
            break
        
        cards = container.select(".entreprise__card")
        for card in cards:
            try:
                item = get_results_bdc(card)

                client, created_clt = Client.objects.update_or_create(name=item['client'])
                if created_clt: clients_created += 1

                itex, created_bdc = PurchaseOrder.objects.update_or_create(
                    reference = item['reference'],
                    client = client,
                    title = title,
                    defaults = {
                        'unsuccessful': is_infructueux,
                        'bids_count': n_devis,
                        'winner_entity': entreprise_attr,
                        "winner_amount" : montant_decimal_ttc,
                        "deliberated" : published_dt,
                    }
                )
                if created_bdc: bdc_created += 1
            except Exception as xc:
                print("[XXXXX] Exception raised while getting data: ", str(xc))
                errors_happened = True

            handled_items += 1

        if not has_next_page(soup):
            print("\n[✔✔✔✔✔] Reached last page.")
            print('\tHandled items: ', handled_items)
            print('\tP. Orders created: ', bdc_created)
            print('\tClients created: ', clients_created)
            break

        page += 1

    return 0 if errors_happened == False else 1

get_and_save_results()