
import requests
from bs4 import BeautifulSoup
import traceback
import random
import time
import json
import pytz

from datetime import datetime
from decimal import Decimal

from . import helper
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
        "User-Agent": helper.getUa(),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
    }
    

def safe_text(elem):
    return elem.get_text(strip=True) if elem else ""


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


def get_bdc(card):
    """
    Extracts data from a single item card
    """
    
    ref_text = card.select_one(".entreprise__middleSubCard a.table__links")
    try: reference = ref_text.get_text(strip=True).replace("Référence :", "").strip()
    except Exception as xc: 
        print('ref_text :::::::::', ref_text)
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

    date_limite_text = None
    heure_limite_text = None
    lieu = None

    right = card.select_one(".entreprise__rightSubCard--top")
    if right:
        date_text = right.select("span")[1].get_text(strip=True)
        try: date_limite_text = date_text.replace("", "").strip()
        except Exception as xc: 
            print('date_limite_text exception: \n', xc)
            pass

        heure_text = right.select("span")[2].get_text(strip=True)
        try: heure_limite_text = heure_text.replace("", "").strip()
        except Exception as xc: 
            print('heure_limite_text exception: \n', xc)
            pass

        lieu_text = right.select("span")[4]
        try: lieu = lieu_text.get_text(strip=True)
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
    # print('details_url', details_url)
    html = fetch_page(details_url)
    if html:

        soup = BeautifulSoup(html, "lxml")
        # box = soup.find("div", class_="py-3 content__subBox  devisAccordionStyle")
        box = soup.select_one("div.py-3.content__subBox.devisAccordionStyle")
        # print('soup =[', soup, ']')

        published = None
        try:
            published_str = safe_text(box.select_one("#dateMiseEnLigne ~ div span.truncate-one-line"))
            naive_dt = datetime.strptime(published_str, "%d/%m/%Y %H:%M")
            published = rabat_tz.localize(naive_dt)
        except: pass

        category_name = None
        try: category_name = safe_text(box.select_one("#category ~ div span:nth-of-type(2)"))
        except: pass

        nature = None
        try: nature = safe_text(box.select_one("#screwdriver ~ div span:nth-of-type(2)"))
        except: pass

        # Articles
        articles = []
        for acc in box.select(".accordion-item"):
            title_btn = acc.select_one("button")
            title_text = safe_text(title_btn).replace("\n", " ")

            number = safe_text(acc.select_one("span.font-bold")).replace("#", "")
            title_article = " ".join(title_text.split()[1:])
            uom = safe_text(acc.select_one(".content__article--subMiniCard:nth-of-type(1)"))
            quantity = safe_text(acc.select_one(".content__article--subMiniCard:nth-of-type(2)"))
            vat_percent = safe_text(acc.select_one(".content__article--subMiniCard:nth-of-type(3)"))
            warranties = safe_text(acc.select_one(".content__article--subMiniCard:nth-of-type(4)"))
            specifications = safe_text(acc.select_one(".gap-3 .text-black"))

            # Le veau laid violet volait le volet et volait avec le vieux lait.

            try: number = int(number)
            except: number = None

            try: vat_percent = int(vat_percent)
            except: vat_percent = None


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
                "link": a["href"] if a and a.has_attr("href") else None
            }
            for a in box.select("a.nounderlinelink")
        ]


        bdc = {
            'reference'     : reference,
            'title'         : title,
            'published'     : published,
            'deadline'      : deadline,
            'nature'        : nature,
            'location'      : lieu,
            'link'          : link,
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
                if created_bdc: bdc_created += 1
            except Exception as xc:
                print("[XXXXX] Exception raised while getting data: ", str(xc))
                traceback.print_exc()
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


def get_and_save_bdcs():

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
                item = get_bdc(card)
                if item != {} :
                    client_name = item['client']
                    if client_name and client_name != '':
                        client, created = Client.objects.update_or_create(name=client_name)
                        if created: clients_created += 1

                    category_label = item['category']
                    if category_label and category_label != '':
                        category, created = Category.objects.update_or_create(label=category_label)
                        if created: categorys_created += 1

                    bdc, created = PurchaseOrder.objects.update_or_create(
                        reference = item['reference'],
                        client = client,
                        title = item['title'],
                        defaults = {
                            'category' : category,
                            # 'unsuccessful': None,
                            # 'bids_count': item['bids_count'],
                            # 'winner_entity': item['winner_entity'],
                            # "winner_amount" : item['winner_amount'],
                            # "deliberated" : item['deliberated'],
                        }
                    )
                    if created : bdc_created += 1

                    articles_items = item['articles']
                    if articles_items and articles_items != {}:
                        for articles_item in articles_items:
                            article_number = articles_item['number']
                            if article_number and article_number != '':
                                number = int(article_number)
                                try:
                                    qts = articles_item['quantity'].strip().replace(' ', '').replace(',', '.')
                                    quantity = Decimal(qts)
                                except: quantity = 0

                                article, created = Article.objects.update_or_create(
                                    purchase_order=bdc, number=number,
                                    defaults = {
                                        'title' : articles_item['title'],
                                        'specifications' : articles_item['specifications'],
                                        'warranties' : articles_item['warranties'],
                                        'uom' : articles_item['uom'],
                                        'quantity' : quantity,
                                        'vat_percent' : articles_item['vat_percent'],
                                    }
                                )
                                if created : articles_created += 1

                    attachements_items = item['attachements']
                    if attachements_items and attachements_items != {}:
                        for attachements_item in attachements_items:
                            link = attachements_item['link']
                            if link and link != '': 
                                attachement, created = Attachement.objects.update_or_create(
                                    purchase_order=bdc, link=link,
                                    defaults = {'name': attachements_item['name']}
                                )
                                if created : attachements_created += 1
                    
                else:
                    print("[XXXXX] Got an empty item !")
            except Exception as xc:
                print("[XXX----XXX] Exception raised while getting data: ", str(xc))
                traceback.print_exc()
                errors_happened = True

            handled_items += 1

        if not has_next_page(soup):
            print("\n[✔✔✔✔✔] Reached last page.")
            print('\tHandled items: ', handled_items)
            print('\tP. Orders created: ', bdc_created)
            print('\tClients created: ', clients_created)
            print('\tCategories created: ', categorys_created)
            print('\tArticles created: ', articles_created)
            break

        page += 1

    return 0 if errors_happened == False else 1


get_and_save_bdcs()