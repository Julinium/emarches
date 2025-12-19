
import requests
from bs4 import BeautifulSoup
import traceback
import random
import time
import json
import pytz

from datetime import datetime, timedelta
from decimal import Decimal

# from . import helper
from .helper import getUa, printMessage
from . import constants as C

from bdc.models import Article, Attachement, PurchaseOrder
from base.models import Category, Client


LISTING_BASE_URL = C.BDC_LISTING_BASE_URL
LISTING_PAGE_PARAM = "page"
BDC_DETAILS_HOST = C.BDC_DETAILS_HOST

RESULTS_BASE_URL = C.BDC_RESULTS_BASE_URL
RESULTS_PAGE_PARAM = "page"

rabat_tz = pytz.timezone("Africa/Casablanca")


def get_headers():
    return {
        "User-Agent": getUa(),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
    }


def safe_text(elem):
    return elem.get_text().strip(" ") if elem else ""


def fetch_page(url, params={}, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=get_headers(), params=params, timeout=15)
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


def get_bdc(card):
    """
    Extracts data from a single item card
    """
        
    ref_text = card.select_one(".entreprise__middleSubCard a.table__links")
    try: reference = ref_text.get_text(strip=True).replace("Référence :", "").strip()
    except Exception as xc: 
        print('Reference exception: \n', xc)
        reference = None

    title_elem = card.select_one(".entreprise__middleSubCard a.truncate_fullWidth")
    try: title = title_elem.get_text(strip=True).replace("Objet :", "").strip()
    except Exception as xc: 
        print('Title exception: \n', xc)
        title = None

    acheteur_elem = card.select(".entreprise__middleSubCard a.table__links")[2]
    try: acheteur = acheteur_elem.get_text(strip=True).replace("Acheteur :", "").strip()
    except Exception as xc: 
        print('Acheteur exception: \n', xc)
        acheteur = None

    anchor_elem = card.select_one("a")
    try: link = anchor_elem["href"]
    except Exception as xc: 
        print('Link exception: \n', xc)
        link = None

    try: chrono = link.rsplit('/', 1)[-1]
    except Exception as xc: 
        print('Chrono exception: \n', xc)
        chrono = None

    date_limite_text = None
    heure_limite_text = None
    lieu = None

    right = card.select_one(".entreprise__rightSubCard--top")
    if right:
        date_text = right.select("span")[1].get_text(strip=True)
        try: 
            date_limite_text = date_text.replace("", "").strip()
        except Exception as xc: 
            print('date_limite_text exception: \n', xc)
            pass

        heure_text = right.select("span")[2].get_text(strip=True)
        try: 
            heure_limite_text = heure_text.replace("", "").strip()
        except Exception as xc: 
            print('heure_limite_text exception: \n', xc)
            pass

        lieu_text = right.select("span")[4]
        try: 
            lieu = lieu_text.get_text(strip=True)
        except Exception as xc:
            print('lieu exception: \n', xc)
            pass

    deadline = None
    try:
        deadline_str = f"{date_limite_text} {heure_limite_text}"
        naive_dt = datetime.strptime(deadline_str, "%d/%m/%Y %H:%M")
        deadline = rabat_tz.localize(naive_dt)
    except Exception as xc:
        print('deadline exception: \n', xc)
        pass

    # Get details
    details_url = f"{BDC_DETAILS_HOST}{link}"
    html = fetch_page(details_url)
    if html:

        soup = BeautifulSoup(html, "lxml")
        for br in soup.find_all("br"): br.replace_with("\n")
            
        box = soup.select_one("div.py-3.content__subBox.devisAccordionStyle")

        published = None
        try:
            published_str = safe_text(box.select_one("#dateMiseEnLigne ~ div span.truncate-one-line"))
            naive_dt = datetime.strptime(published_str, "%d/%m/%Y %H:%M")
            published = rabat_tz.localize(naive_dt)
        except Exception as xc:
            print('Published Exception: \n', xc)
            pass

        category_name = None
        try: 
            category_name = safe_text(box.select_one("#category ~ div span:nth-of-type(2)"))
        except Exception as xc:
            print('Category name Exception: \n', xc)
            pass

        nature = '--' # None
        try: nature = safe_text(box.select_one("#screwdriver ~ div span:nth-of-type(2)"))
        except Exception as xc:
            print('Nature Exception: \n', xc)
            pass

        # Articles
        articles = []
        for acc in box.select(".accordion-item"):
            title_btn = acc.select_one("button")
            title_text = safe_text(title_btn)

            number = safe_text(acc.select_one("span.font-bold")).replace("#", "")
            # if number == '': number = '0'
            title_article = title_text.replace('#' + number, '')
            mini_elements = acc.select(".content__article--subMiniCard")
            uom = safe_text(mini_elements[0])
            quantity = safe_text(mini_elements[1])
            vat_percent = safe_text(mini_elements[2])
            if vat_percent == '': vat_percent = '0'
            warranties = safe_text(mini_elements[3])
            specifications = safe_text(acc.select_one(".gap-3 .text-black"))

            # Le veau laid violet volait le volet et volait avec le vieux lait.

            articles.append({
                'number'            : number,
                'title'             : title_article,
                'uom'               : uom,
                'quantity'          : quantity,
                'vat_percent'       : vat_percent,
                'specifications'    : specifications,
                'warranties'        : warranties,
            })

        attachements = [
            {
                "name": safe_text(a),
                "link": f"{ BDC_DETAILS_HOST }" + a["href"] if a and a.has_attr("href") else None
            }
            for a in box.select("a.nounderlinelink")
        ]


        bdc = {
            'chrono'        : chrono,
            'reference'     : reference,
            'title'         : title,
            'published'     : published,
            'deadline'      : deadline,
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
    
    is_infructueux = None
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
            entreprise_attr, montant_ttc = None, None

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


def save_results(published_since_days=1):
    print('\n\n')
    printMessage('INFO', 'b.save_results', "Started Results browsing ...")

    errors_happened = False
    handled_items = 0
    clients_created = 0
    bdc_created = 0

    page = 1
    while True:
        url = f"{RESULTS_BASE_URL}&{RESULTS_PAGE_PARAM}={page}"
        assnna = datetime.now().date() - timedelta(days=published_since_days)
        assnna_str = assnna.strftime('%Y-%m-%d')
        params = {
            "search_consultation_resultats[keyword]" : '',
            "search_consultation_resultats[reference]" : '',
            "search_consultation_resultats[objet]" : '',
            "search_consultation_resultats[dateLimitePublicationStart]" : assnna_str,
            "search_consultation_resultats[dateLimitePublicationEnd]" : '',
            "search_consultation_resultats[dateMiseEnLigneStart]" : '',
            "search_consultation_resultats[dateMiseEnLigneEnd]" : '',
            "search_consultation_resultats[categorie]" : '',
            "search_consultation_resultats[naturePrestation]" : '',
            "search_consultation_resultats[acheteur]" : '',
            "search_consultation_resultats[service]" : '',
            "search_consultation_resultats[lieuExecution]" : '',
            "search_consultation_resultats[pageSize]" : '50'
        }

        # print('\n\n====================')
        # print('Searching Results with [dateLimitePublicationStart] = ', assnna_str)
        # print('====================\n\n')
        
        printMessage('INFO', 'b.save_results', f"Fetching Results page: { page }")

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
            items_count = 0

        printMessage('INFO', 'b.save_results', f"Found Results items count: { items_count }")

        cards = container.select(".entreprise__card")
        i = 0
        for card in cards:
            i += 1
            printMessage('INFO', 'b.save_results', f"Fetching item { i } from page { page }")
            try:
                item = get_results_bdc(card)

                client, created_client = Client.objects.update_or_create(name=item['client'])
                if created_client: clients_created += 1

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

        if not has_next_page(soup):
            printMessage('INFO', 'b.save_results', "[✔✔✔✔✔] Reached last Results page.")
            printMessage('INFO', 'b.save_results', f"Handled items: { handled_items }. +P.Orders: { bdc_created }. +Clients: { clients_created }")
            break

        page += 1

    return 0 if errors_happened == False else 1


def save_bdcs(published_since_days=1):
    print('\n\n')
    printMessage('INFO', 'b.save_bdcs', "Started browsing Ongoing POs ...")

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
        url = f"{LISTING_BASE_URL}&{LISTING_PAGE_PARAM}={page}"
        assnna = datetime.now().date() - timedelta(days=published_since_days)
        assnna_str = assnna.strftime('%Y-%m-%d')

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

        # print('\n\n====================')
        # print('Searching POs with [dateMiseEnLigneStart] = ', assnna_str)
        # print('====================\n\n')

        printMessage('INFO', 'b.save_bdcs', f"Fetching POs page { page } ...")

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
            items_count = 0

        printMessage('INFO', 'b.save_results', f"Found POs count: { items_count }")

        cards = container.select(".entreprise__card")
        i = 0
        for card in cards:
            i += 1
            printMessage('INFO', 'b.save_bdcs', f"Fetching item: { i } from { page } ...")
            try:
                item = get_bdc(card)
                if item != {} :
                    chrono = item['chrono']

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
                        reference = item['reference'],
                        title = item['title'],
                        client = client,
                        defaults = {
                            'category'  : category,
                            'chrono'    : item['chrono'],
                            'published' : item['published'],
                            'deadline'  : item['deadline'],
                            'location'  : item['location'],
                            'link'      : item['link'],
                            'nature'    : item['nature'],
                        }
                    )
                    if created : 
                        printMessage('DEBUG', 'b.save_bdcs', f"Created Purchase Order: { chrono }: { item['title'][:truncater] }")
                        bdc_created += 1
                    else:
                        printMessage('DEBUG', 'b.save_bdcs', f"Updated Purchase Order: { chrono }: { item['title'][:truncater] }")

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

        if not has_next_page(soup):
            printMessage('INFO', 'b.save_bdcs', "[✔✔✔✔✔] Reached last POs page.")
            printMessage('INFO', 'b.save_bdcs', f"Handled items: { handled_items } +P.Orders: { bdc_created } +Clients: { clients_created } +Categories: { categorys_created } +Articles: { articles_created }")

            break

        page += 1

    return 0 if errors_happened == False else 1
