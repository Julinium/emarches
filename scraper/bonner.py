
import requests
from bs4 import BeautifulSoup
# import pandas as pd
import random
import time
import json
import pytz

from datetime import datetime
from decimal import Decimal

from . import helper
from . import constants as C

from bdc.models import Client, PurchaseOrder

LISTING_BASE_URL = C.BDC_LISTING_BASE_URL
LISTING_PAGE_PARAM = "page"

RESULTS_BASE_URL = C.BDC_RESULTS_BASE_URL
RESULTS_PAGE_PARAM = "page"

rabat_tz = pytz.timezone("Africa/Casablanca")


def get_headers():
    return {
        "User-Agent": helper.getUa(),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        # "User-Agent": random.choice(USER_AGENTS),
    }


def fetch_page(url, retries=3):
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


def get_bdc(card, details=None):
    """
    Extracts data from a single item card
    """
    
    ref_text = card.select_one(".entreprise__middleSubCard a.table__links")
    try: reference = ref_text.replace("Référence :", "").strip()
    except: reference = None

    title_elem = card.select_one(".entreprise__middleSubCard a.truncate_fullWidth")
    try: title = title_elem.get_text(strip=True).replace("Objet :", "").strip()
    except: title = None

    acheteur_elem = card.select(".entreprise__middleSubCard a.table__links")[2]
    try: acheteur = acheteur_elem.get_text(strip=True).replace("Acheteur :", "").strip()
    except: acheteur = None

    anchor_elem = card.select_one("a")
    try: link = anchor_elem["href"]
    except: link = None

    date_limite_text = None
    heure_limite_text = None
    lieu = None

    right = card.select_one(".entreprise__rightSubCard--top")
    if right:
        date_text = right.select("span")[1].get_text(strip=True)
        try: date_limite_text = date_text.replace("", "").strip()
        except: pass

        heure_text = right.select("span")[2].get_text(strip=True)
        try: heure_limite_text = heure_text.replace("", "").strip()
        except: pass

        lieu_text = right.select("span")[4]
        try: lieu = lieu_text.get_text(strip=True)
        except: pass

    deadline = None
    try:
        deadline_str = f"{date_limite_text} {heure_limite_text}"
        naive_dt = datetime.strptime(deadline_str, "%d/%m/%Y %H:%M")
        deadline = rabat_tz.localize(naive_dt)
    except: pass

    # TODO: Fetch link and get details ...
    
    bdc = {
        'reference' : reference,
        'title'     : title,
        'acheteur'  : acheteur,
        'dealine'   : deadline,
        'location'  : lieu,
        'link'      : link,
    }
    
    return bdc
    


def get_results_bdc(card):
    """
    Extracts data from a single item card
    """
    
    ref = card.select_one(".entreprise__middleSubCard div.font-bold.table__links")
    reference = None
    if ref: reference = ref.get_text(strip=True).replace("Référence :", "").strip()


    title_div = card.select_one('.entreprise__middleSubCard div[data-bs-toggle="tooltip"]')
    title = None
    if title_div: title = title_div.get_text(strip=True).replace("Objet :", "").strip()

    client_div = card.find("span", string=lambda x: x and "Acheteur" in x)
    client = None
    if client_div: client = client_div.parent.get_text(strip=True).replace("Acheteur :", "")

    date_div = card.find("span", string=lambda x: x and "Date de publication" in x)
    date_pub = None
    if date_div: date_pub = date_div.parent.get_text(strip=True).replace("Date de publication du résultat :", "")

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

    published_dt = None
    if date_pub:
        naive_dt = datetime.strptime(date_pub, "%d/%m/%Y %H:%M")
        published_dt = rabat_tz.localize(naive_dt)

    montant_decimal_ttc = None
    if montant_ttc:
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
        
        html = fetch_page(url)
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
                    title = item['title'],
                    defaults = {
                        'unsuccessful': item['unsuccessful'],
                        'bids_count': item['bids_count'],
                        'winner_entity': item['winner_entity'],
                        "winner_amount" : item['winner_amount'],
                        "deliberated" : item['deliberated'],
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