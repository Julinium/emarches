
import json
import random
import time
import traceback
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urljoin
from django.db import transaction

import pytz
import requests
from bs4 import BeautifulSoup

from base.models import Category, Client
from bdc.models import Article, Attachement, PurchaseOrder

from scraper import constants as C
from scraper.helper import getUa, printMessage, getDateTime, getAmount

BDC_DETAILS_HOST = C.BDC_DETAILS_HOST
LISTING_BASE_URL = C.BDC_LISTING_BASE_URL
LISTING_PAGE_PARAM = "?page"
RESULTS_BASE_URL = C.BDC_RESULTS_BASE_URL

BDC_UPDATE_MODE = True

rabat_tz = pytz.timezone("Africa/Casablanca")


def get_headers():
    rua = getUa()
    printMessage('TRACE', 'b.get_headers', f"Using UA: {rua}", 2)
    return {
        "User-Agent": rua,
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
    }


def safe_text(element=None, fallback=None):
    return element.get_text(strip=True) if element else fallback


def fetch_page(url, params={}, retries=3, timeout=60):
    for attempt in range(retries):
        try:
            printMessage('TRACE', 'b.fetch_page', f"Getting page at: {url}", 2)
            printMessage('TRACE', 'b.fetch_page', f"... Using params: \n{params} ...", 2)
            r = requests.get(url, headers=get_headers(), params=params, timeout=timeout)
            s = r.status_code
            printMessage('TRACE', 'b.fetch_page', f"Request header: {r.headers}", 2)
            if s == 200:
                return r.text
            else:
                print("[!!!!!] Error : status code was not 200:", s)
        except Exception as e:
            print("[!!!!!] Exception:", e)

        print(f"[-----] Retrying ({ attempt + 1 }/{ retries }) …")
        time.sleep(random.random())

    return None


def get_bdc(card):
    """
    Extracts data from a single item card
    """
    
    printMessage("DEBUG", "b.get_bdc", "Getting BDC digest ...")

    reference = safe_text(card.select_one(".bdc-card__ref"))
        
    date_limite_elem = card.select_one(".bdc-card__v")
    date_limite_text = date_limite_elem.get_text(strip=True) if date_limite_elem else None
    heure_limite_elem = card.select_one(".bdc-card__s")
    heure_limite_text = heure_limite_elem.get_text(strip=True).replace('à ', '') if heure_limite_elem else None
    
    deadline = None
    if date_limite_text and heure_limite_text:
        day_str, month_str, year_str = date_limite_text.split()
        month_str = month_str.lower().rstrip('.')
        month_str = month_str[:4] if month_str.startswith(('juin', 'juil')) else month_str[:3]
        month_str = month_str.replace('é', 'e').capitalize()
        date_time_str = f'{day_str} {month_str} {year_str} {heure_limite_text}'
        deadline = getDateTime('----' + date_time_str)

        
    cancelled_text = card.select_one(".badge.bg-danger")
    cancelled = cancelled_text is not None

    title_elem = card.select_one(".bdc-card__title")
    if title_elem: 
        title  = title_elem.get_text(strip=True)
        link   = title_elem["href"]
        chrono = link.rsplit('/', 1)[-1]
    else: 
        title, link, chrono = None, None, None

    acheteur_elem = card.select_one('.bdc-card__meta')
    if acheteur_elem:
        spans = acheteur_elem.select('span')
        acheteur = spans[0].get_text(strip=True) if len(spans) > 0 else None
        lieu = spans[1].get_text(strip=True) if len(spans) > 1 else None


    # Get details
    details_url = f"{BDC_DETAILS_HOST}{link}"
    html = fetch_page(details_url)
    if html:

        soup = BeautifulSoup(html, "lxml")
        for br in soup.find_all("br"): br.replace_with("\n")
            
        box = soup.select_one("div.py-3.content__subBox.devisAccordionStyle")


        published_str = safe_text(box.select_one("#dateMiseEnLigne ~ div span.truncate-one-line"))
        naive_dt = datetime.strptime(published_str, "%d/%m/%Y %H:%M") if published_str else None
        published = rabat_tz.localize(naive_dt) if naive_dt else None

        category_name = safe_text(box.select_one("#category ~ div span:nth-of-type(2)"))

        nature = safe_text(box.select_one("#screwdriver ~ div span:nth-of-type(2)"), '--')
        

        # Articles
        articles = []
        articles_accordions = box.select(".accordion-item")
        printMessage("TRACE", "b.get_bdc", f"Getting {len(articles_accordions)} BDC articles ...")

        for acc in articles_accordions:
            title_btn = acc.select_one("button")
            title_text = safe_text(title_btn, '--')

            number = safe_text(acc.select_one("span.font-bold"), '--').replace("#", "")
            title_article = title_text.replace('#' + number, '')
            mini_elements = acc.select(".content__article--subMiniCard")
            uom = safe_text(mini_elements[0], '--')
            quantity = safe_text(mini_elements[1], '--')
            vat_percent = safe_text(mini_elements[2], '')
            if vat_percent == '': vat_percent = '0'
            warranties = safe_text(mini_elements[3], '--')
            specifications = safe_text(acc.select_one(".gap-3 .text-black"), '--')

            articles.append({
                'number'            : number,
                'title'             : title_article,
                'uom'               : uom,
                'quantity'          : quantity,
                'vat_percent'       : vat_percent,
                'specifications'    : specifications,
                'warranties'        : warranties,
            })

        attachements_links = box.select("a.nounderlinelink")
        printMessage("TRACE", "b.get_bdc", f"Getting {len(attachements_links)} BDC attachements ...")
        attachements = [
            {
                "name": safe_text(a, '--'),
                "link": f"{ BDC_DETAILS_HOST }" + a["href"] if a and a.has_attr("href") else None
            }
            for a in attachements_links
        ]


        bdc = {
            'chrono'        : chrono,
            'reference'     : reference,
            'title'         : title,
            'published'     : published,
            'deadline'      : deadline,
            'cancelled'     : cancelled,
            'nature'        : nature,
            'location'      : lieu,
            'link'          : details_url,
            'client'        : acheteur,
            'category'      : category_name,
            'articles'      : articles,
            'attachements'  : attachements,
        }

    else:
        return {}
    
    printMessage("DEBUG", "b.get_bdc", f"Finished getting BDC digest for {reference}.")
    printMessage("TRACE", "b.get_bdc", f"BDC digest: { bdc }")
    return bdc
    

def get_results_bdc(card):
    """
    Extracts data from a single item card
    """
    
    printMessage("DEBUG", "b.get_rsults_bdc", "Getting BDC result digest ...")
    reference = safe_text(card.select_one(".bdc-card__ref"))    
    title = safe_text(card.select_one('.bdc-card__title'))
    client = safe_text(card.select_one('.bdc-card__meta'))

    infructueux_elem = card.select_one('span.bdc-card__v')
    infructueux = infructueux_elem.get_text(strip=True) == "Infructueux" if infructueux_elem else None

    date_pub_elem = card.select_one('span.bdc-card__s')
    date_pub_str = date_pub_elem.get_text(strip=True).replace('Publié le ', '').replace('à ', '') if date_pub_elem else None
    date_pub = getDateTime(date_pub_str) if date_pub_str else None
    
    bids_count_str = safe_text(card.select_one('.bdc-card__facts').select_one('dd'))
    bids_count = int(bids_count_str) if bids_count_str else 0
    
    winner = safe_text(card.select_one('.bdc-card__winner'))
    amount_ttc_str = safe_text(card.select_one('.bdc-card__money'))
    amount_ttc = getAmount(amount_ttc_str) if amount_ttc_str and amount_ttc_str != '—' else None

    bdc_result = {
        'reference': reference,
        'title': title,
        'client': client,
        'unsuccessful': infructueux,
        'bids_count': bids_count,
        'winner_entity': winner if winner != '—' else None,
        "deliberated" : date_pub,
        "winner_amount" : amount_ttc
    }

    printMessage("DEBUG", "b.get_rsults_bdc", f"Finished getting BDC result digest for {reference}.")
    printMessage("TRACE", "b.get_rsults_bdc", f"BDC result digest: { bdc_result }")

    return bdc_result


def next_page_link(soup):
    return soup.find("a", string=lambda x: x and ("Suivant" in x))


def save_bdcs(since_days=1, update_mode=BDC_UPDATE_MODE):
    
    printMessage('INFO', 'b.save_bdcs', "Started browsing running POs ...", 2)
    printMessage('INFO', 'b.save_bdcs', f"Since days: {since_days}. Update mode: {update_mode}.")

    truncater = 32
    errors_happened = False
    handled_items = 0
    clients_created = 0
    categorys_created = 0
    bdc_created = 0
    articles_created = 0
    attachements_created = 0

    page = 1
    while True:
        url = f"{LISTING_BASE_URL}{LISTING_PAGE_PARAM}={page}"
        assnna = datetime.now().date() - timedelta(days=since_days)
        assnna_str = assnna.strftime('%Y-%m-%d')
        
        printMessage('TRACE', 'b.save_bdcs', f"Fetching URL {url} ...", 2)

        params = {
            "search_consultation_entreprise[keyword]": "",
            "search_consultation_entreprise[reference]": "",
            "search_consultation_entreprise[objet]": "",
            "search_consultation_entreprise[dateLimiteStart] ": "",
            "search_consultation_entreprise[dateLimiteEnd] ": "",
            "search_consultation_entreprise[dateMiseEnLigneStart]": assnna_str,
            "search_consultation_entreprise[dateMiseEnLigneEnd]": "",
            "search_consultation_entreprise[categorie]": "",
            "search_consultation_entreprise[naturePrestation]": "",
            "search_consultation_entreprise[acheteur]": "",
            "search_consultation_entreprise[service]": "",
            "search_consultation_entreprise[lieuExecution]": "",
            "search_consultation_entreprise[pageSize]": "50"
        }

        printMessage('INFO', 'b.save_bdcs', f"Fetching POs page { page } ...", 2)

        html = fetch_page(url, params=params)
        if not html:
            errors_happened = True
            break

        soup = BeautifulSoup(html, "lxml")
        for br in soup.find_all("br"): br.replace_with("\n")
            
        container = soup.select_one("div.mt-4.py-3.content__subBox")

        if not container:
            errors_happened = True
            break

        count_text = container.select_one(".content__resultat")
        try:
            items_count_str = count_text.get_text(strip=True).replace(":", "").replace("Nombre de résultats", "").strip()
            items_count = int(items_count_str)
        except Exception as xc:
            print('Items count exception: \n', xc)
            items_count = None

        printMessage('INFO', 'b.save_bdcs', f"Fetching items from page { page } ...", 1)
        printMessage('INFO', 'b.save_bdcs', f"Found POs count: { items_count }")

        cards = container.select(".bdc-card.bdc-card--lien")
        i = 0
        for card in cards:
            i += 1
            printMessage('DEBUG', 'b.save_bdcs', f"Fetching item: { i } from page { page } ...", 1)
            try:
                item = get_bdc(card)
                if item != {} :
                    chrono = item['chrono']

                    if update_mode == False and PurchaseOrder.objects.filter(chrono=chrono).exists():
                        printMessage('DEBUG', 'b.save_bdcs', f"Item exists. Skipping { chrono }.")
                        continue

                    with transaction.atomic():
                        client_name = item['client']
                        if client_name and client_name != '':
                            client, created = Client.objects.get_or_create(name=client_name)
                            if created :
                                printMessage('DEBUG', 'b.save_bdcs', f"Created Client: { client_name[:truncater] }")
                                clients_created += 1
                            else:
                                printMessage('DEBUG', 'b.save_bdcs', f"Found Client: { client_name[:truncater] }")

                        category_label = item['category']
                        if category_label and category_label != '':
                            category, created = Category.objects.get_or_create(label=category_label)
                            if created :
                                printMessage('DEBUG', 'b.save_bdcs', f"Created Category: { category_label[:truncater] }")
                                categorys_created += 1
                            else:
                                printMessage('DEBUG', 'b.save_bdcs', f"Found Category: { category_label[:truncater] }")

                        bdc, created = PurchaseOrder.objects.update_or_create(
                            chrono = item['chrono'],
                            # title = item['title'],
                            # client = client,
                            defaults = {
                                'category'  : category,
                                'client'    : client,
                                'title'     : item['title'],
                                'reference' : item['reference'],
                                # 'chrono'    : item['chrono'],
                                'published' : item['published'],
                                'cancelled' : item['cancelled'],
                                'deadline'  : item['deadline'],
                                'location'  : item['location'],
                                'link'      : item['link'],
                                'nature'    : item['nature'],
                            }
                        )

                        if created : 
                            printMessage('DEBUG', 'b.save_bdcs', f"Created P. Order: { chrono }: { item['title'][:truncater] }")
                            bdc_created += 1
                        else:
                            printMessage('DEBUG', 'b.save_bdcs', f"Updated P. Order: { chrono }: { item['title'][:truncater] }")

                        articles_items = item['articles']
                        if articles_items and articles_items != {}:
                            rank = 0
                            for articles_item in articles_items:
                                rank += 1
                                
                                try: 
                                    number = articles_item['number']
                                except Exception as xc:
                                    printMessage('ERROR', 'b.save_bdcs', f"[xxxxx] Exception raised while getting article number: { xc }")
                                    traceback.print_exc()

                                try:
                                    qts = articles_item['quantity'].strip().replace(' ', '').replace(',', '.')
                                    quantity = Decimal(qts)
                                except Exception as xc:
                                    printMessage('ERROR', 'b.save_bdcs', f"[xxxxx] Exception raised while getting article quantity: { xc }")
                                    traceback.print_exc()
                                    quantity = 0
                                try:
                                    vat = articles_item['vat_percent'].strip().replace(' ', '').replace(',', '.')
                                    vat_percent = Decimal(vat)
                                except Exception as xc:
                                    printMessage('ERROR', 'b.save_bdcs', f"[xxxxx] Exception raised while getting VAT: { xc }")
                                    traceback.print_exc()
                                    vat_percent = 0

                                article, created = Article.objects.update_or_create(
                                    purchase_order=bdc, 
                                    number=number, 
                                    defaults = {
                                        'rank'           : rank,
                                        'title'          : articles_item['title'],
                                        'specifications' : articles_item['specifications'],
                                        'warranties'     : articles_item['warranties'],
                                        'uom'            : articles_item['uom'],
                                        'quantity'       : quantity,
                                        'vat_percent'    : vat_percent,
                                    }
                                )
                                if created:
                                    printMessage('DEBUG', 'b.save_bdcs', f"Created Article: { number }: { articles_item['title'][:truncater] }")
                                    articles_created += 1
                                else:
                                    printMessage('DEBUG', 'b.save_bdcs', f"Updated Article: { number }: { articles_item['title'][:truncater] }")

                        attachements_items = item['attachements']
                        if attachements_items and attachements_items != {}:
                            for attachements_item in attachements_items:
                                link = attachements_item['link']
                                if link and link != '': 
                                    attachement, created = Attachement.objects.update_or_create(
                                        purchase_order=bdc, link=link,
                                        defaults = {'name': attachements_item['name']}
                                    )
                                    if created :
                                        printMessage('DEBUG', 'b.save_bdcs', f"Created Attachement: { attachements_item['name'][:truncater] }")
                                        attachements_created += 1
                                    else:
                                        printMessage('DEBUG', 'b.save_bdcs', f"Updated Attachement: { attachements_item['name'][:truncater] }")

                else:
                    printMessage('ERROR', 'b.save_bdcs', f"[xxxxx] Got an empty PO !")
            except Exception as xc:
                printMessage('ERROR', 'b.save_bdcs', f"[xxxxx] Exception raised while getting PO data: { xc }")
                traceback.print_exc()
                errors_happened = True

            handled_items += 1

        if not next_page_link(soup):
            printMessage('INFO', 'b.save_bdcs', "[✔✔✔✔✔] Reached last POs page.")
            printMessage('INFO', 'b.save_bdcs', f"Handled items: { handled_items }: \n\t+ P. Orders: { bdc_created } \n\t+ Clients: { clients_created } \n\t+ Categories: { categorys_created } \n\t+ Articles: { articles_created }")

            break

        page += 1

    return 0 if errors_happened == False else 1


def save_results(since_days=1):
    printMessage('INFO', 'b.save_results', "Started browsing POs results ...", 4)    
    assnna = datetime.now().date() - timedelta(days=since_days)
    assnna_str = assnna.strftime('%Y-%m-%d')
    printMessage('INFO', 'b.save_results', f"Browsing items published since: { since_days } days on ...")
    
    errors_happened = False
    handled_items = 0
    clients_created = 0
    bdc_created = 0

    page = 1
    url_res = f"{RESULTS_BASE_URL}"
    while True:
        printMessage('DEBUG', 'b.save_results', f"Fetching URL for page {page} ...", 2)
        params_res = {
            "search_consultation_resultats[keyword]": "",
            "search_consultation_resultats[reference]": "",
            "search_consultation_resultats[objet]": "",
            "search_consultation_resultats[dateLimitePublicationStart]": assnna_str,
            "search_consultation_resultats[dateLimitePublicationEnd]": "",
            "search_consultation_resultats[dateMiseEnLigneStart]": "",
            "search_consultation_resultats[dateMiseEnLigneEnd]": "",
            "search_consultation_resultats[categorie]": "",
            "search_consultation_resultats[naturePrestation]": "",
            "search_consultation_resultats[acheteur]": "",
            "search_consultation_resultats[service]": "",
            "search_consultation_resultats[lieuExecution]": "",
            "search_consultation_resultats[pageSize]": "50",
            "page": str(page)
        }
        
        printMessage('INFO', 'b.save_results', f"Fetching Results page: { page }")

        html = fetch_page(url_res, params=params_res)
        if not html:
            errors_happened = True
            break

        soup = BeautifulSoup(html, "lxml")
        for br in soup.find_all("br"): br.replace_with("\n")

        container = soup.select_one("div.mt-4.py-3.content__subBox")

        if not container:
            errors_happened = True
            break

        count_text = container.select_one(".content__resultat")
        try:
            items_count_str = count_text.get_text(strip=True).replace(":", "").replace("Nombre de résultats", "").strip()
            items_count = int(items_count_str)
        except Exception as xc:
            print('Items count exception: \n', xc)
            items_count = 0

        printMessage('INFO', 'b.save_results', f"Found Results items count: { items_count }")

        cards = container.select("article.bdc-card")

        cl = len(cards)
        if cl < 1: 
            printMessage('WARN', 'b.save_results', f"No items were found in page { page }")
        i = 0
        for card in cards:
            i += 1
            printMessage('INFO', 'b.save_results', f"Fetching item { i }/{cl} from page { page }")
            try:
                item = get_results_bdc(card)

                client, created_client = Client.objects.update_or_create(name=item['client'])
                if created_client: clients_created += 1

                itex, created_bdc = PurchaseOrder.objects.update_or_create(
                    reference = item['reference'],
                    client = client,
                    # title = item['title'],
                    defaults = {
                        'title'         : item['title'],
                        'unsuccessful'  : item['unsuccessful'],
                        'bids_count'    : item['bids_count'],
                        'winner_entity' : item['winner_entity'],
                        "winner_amount" : item['winner_amount'],
                        "deliberated"   : item['deliberated'],
                    }
                )
                if created_bdc:
                    bdc_created += 1
                    printMessage('DEBUG', 'b.save_results', f"Created result for: { item['reference'] }")
                else:
                    printMessage('DEBUG', 'b.save_results', f"Updated result for: { item['reference'] }")

            except Exception as xc:
                printMessage('ERROR', 'b.save_results', f"[xxxxx] Exception raised while getting data: { xc }")
                traceback.print_exc()
                errors_happened = True

            handled_items += 1
        if not next_page_link(soup):
            printMessage('INFO', 'b.save_results', "[✔✔✔✔✔] Reached last Results page.")
            printMessage('INFO', 'b.save_results', f"Handled items: { handled_items }. +P.Orders: { bdc_created }. +Clients: { clients_created }")
            break

        page += 1

    return 0 if errors_happened == False else 1

