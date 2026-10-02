import csv
import json
import os
import random
import traceback
from datetime import timedelta
from django.utils import timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup

from base.models import Tender, Crawler, Link, Parkour, Machine
from scraper import constants as C
from scraper import helper


REFRESH_SAVED = True


def fillForm(driver, back_days=C.PORTAL_DDL_PAST_DAYS):
    """
    # Synopsis:
        Fills in search form.
    # Params:
        driver: Instance of Chrome Webdriver object (web browser window).
        back_days: How many days to look back for deadline.
    # Return:
        Nothing. Raises an exception if something goes wrong.
    """
    # TODO: Set dateMiseEnLigneCalculeStart to the latest successful Crawler -1 day.

    try:
        # assa = date.today()
        assa = timezone.now()
        dt_ddl_start = assa - timedelta(days=back_days)
        date_ddl_start = dt_ddl_start.strftime("%d/%m/%Y")

        helper.printMessage('INFO', 'l.fillForm', 'Submitting search form ...')
        helper.printMessage('INFO', 'l.fillForm', f'Deadline backward days set to {C.PORTAL_DDL_PAST_DAYS} days.', 2)
        # ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneStart
        # ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneEnd
        # ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneCalculeStart
        # ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneCalculeEnd
        el_ddl_start = driver.find_element("id", "ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneStart")
        el_ddl_start.clear()
        el_ddl_start.send_keys(date_ddl_start)
        
    except Exception:
        helper.printMessage('ERROR', 'l.fillForm', 'Could not fill in search form.')
        traceback.print_exc()


def pg2Links(driver, page_number, pages):
    helper.printMessage('INFO', 'l.pg2Links', f'### Getting links from page {page_number:03}/{pages:03}...')
    links = []
    try:
        i = 1
        table_body = driver.find_element(By.XPATH, '/html/body/form/div[3]/div[2]/div/div[5]/div[1]/div[2]/div[2]/table/tbody')
        table_body_html = table_body.get_attribute("innerHTML")
        soup = BeautifulSoup(table_body_html, "html.parser")

        rows = soup.find_all("tr")

        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 6:
                continue
            second_td = tds[1]
            divs = second_td.find_all("div", recursive=False)
            published_text = divs[3].get_text(strip=True) if len(divs) > 3 else ""
            has_enviro = second_td.find("img") is not None

            sixth_td = tds[5]
            anchor = sixth_td.find("a")
            href = anchor.get("href").strip() if anchor and anchor.has_attr("href") else None
            if href:
                HREF_PREFIX = C.LINK_PREFIX.replace(C.SITE_INDEX, '')
                drat = href.replace(HREF_PREFIX, '')
                portal_id_text = drat.split(C.LINK_STITCH)[0]
                organism_text = drat.split(C.LINK_STITCH)[1]

                link = {
                    "chrono": portal_id_text,
                    "acronym": organism_text,
                    "published": helper.getDateTime(published_text),
                    "has_enviro": has_enviro,
                }
                links.append(link)

                helper.printMessage('TRACE', 'l.pg2Links', f'+++ Got the link {page_number:03}.{i:03} = {portal_id_text}')
            else:
                helper.printMessage('ERROR', 'l.pg2Links', f'Could not get link for {page_number:03}.{i:03}', 1, 2)
            i += 1

    except Exception:
        helper.printMessage('ERROR', 'l.pg2Links', f'Exception while getting links from page {page_number:03}', 1, 2)
        traceback.print_exc()

    helper.printMessage('DEBUG', 'l.pg2Links', f'=== Got {len(links)} links from page {page_number:03}')
    
    return links


def exportLinks(links, csv_name="links.csv"):
    """
    # Synopsis:
        Exports links to a csv file. File is placed under {SELENO_DIR/exports} and named {csv_name}.
    # Params:
        links: List of links to export.
        csv_name: Name of the csv file to create.
    # Return:
        full path to the exported csv file.
    """
    helper.printMessage('INFO', 'l.exportLinks', f'Exporting links to {csv_name} ...\n')
    file = ''
    if len(links) > 0 :
        try:
            expo_dir = f'{C.SELENO_DIR}/exports'
            if not os.path.exists(expo_dir) : os.mkdir(expo_dir)
            file = f'{expo_dir}/{csv_name}'
            with open(file, 'w', newline='') as linkscsv:
                linkwriter = csv.writer(linkscsv)
                for l in links:
                    linkwriter.writerow(l)
        except Exception as e :
            helper.printMessage('FATAL', 'l.exportLinks', f'Something went wrong while exporting links')
            traceback.print_exc()
            return None
        helper.printMessage('INFO', 'l.exportLinks', 'Exported links to file. No complains.\n')
    else:
        helper.printMessage('WARN', 'l.exportLinks', 'File was empty and was not exported.\n')

    return file


def mergeLinks(links=[], parkour=None):
    ll = len(links)
    helper.printMessage('DEBUG', 'l.mergeLinks', f'Started merging { ll } link ...')

    raw_instances = [Link(**item) for item in links]
    instances = list({obj.chrono: obj for obj in raw_instances}.values())
    clinked = Link.objects.bulk_create(
            instances,
            update_conflicts=True,
            unique_fields=["chrono"],
            update_fields=["published", "acronym", "has_enviro"]
        )
    helper.printMessage('TRACE', 'l.mergeLinks', f'+++ Created/updated Links: { len(clinked) }.')
    return clinked


def xergeLinks(links=[], parkour=None):
    ll = len(links)
    helper.printMessage('DEBUG', 'l.mergeLinks', f'Started merging { ll } link ...')
    i = 0
    creations = 0
    for l in links:
        i += 1
        helper.printMessage('DEBUG', 'l.mergeLinks', f'>>> Started merging link { i }/{ ll }...')
        published = helper.getDateTime(l.get('published'))
        link, created = Link.objects.update_or_create(
                chrono=l.get('chrono'),
                acronym=l.get('acronym'),
                defaults={
                    "published": published,
                    "has_enviro": l.get('has_enviro'),
                    "parkour": parkour,
                }
            )
        if created == True:
            creations += 1
            helper.printMessage('TRACE', 'l.mergeLinks', f'+++ Creted Link item { link.chrono }')
        else:
            helper.printMessage('TRACE', 'l.mergeLinks', f'~~~ Updated Link item { link.chrono }')
    return creations


def db2Links(back_days=30):
    helper.printMessage('INFO', 'l.db2Links', f'Getting links for saved items, deadline from { back_days } days back ...', 1)
    assa = timezone.now()
    dt_ddl_start = assa - timedelta(days=back_days)
    saved_tenders = Tender.objects.filter(deadline__gte=dt_ddl_start)
    helper.printMessage('DEBUG', 'l.db2Links', f'Found { saved_tenders.count() } eligible saved items', 1)
    links = []
    for tender in saved_tenders:
        links.append({
            "chrono": tender.chrono,
            "acronym": tender.acronym,
            # "published": tender.published.strftime('%d/%m/%Y'),
            "published": tender.published,
            "has_enviro": tender.has_enviro,
        })
    helper.printMessage('DEBUG', 'l.db2Links', f'Constructed { len(links) } link items', 1)

    return links


def getLinks(back_days=30):
    """
    # Synopsis:
        Get a list of available Consultations on Portal.
    # Params:
        None.
    # Return:
        List of extremely abbriged Consultations.
        Each item represents [chrono, acronym, published] for a Consultation.
        The first two values can be used to obtain a working link to the Consultaion on the portal.
    """

    started = timezone.now()
    url = f"{C.SITE_INDEX}?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"
    driver = helper.getDriver(url)
    
    links = []
    pages = 0
    count = 0
    if driver == None: return links
    
    try:
        helper.printMessage('DEBUG', 'l.getLinks', 'Submitting search form with empty terms ...', 1)
        fillForm(driver, back_days)
        org_search_field = driver.find_element("id", "ctl0_CONTENU_PAGE_AdvancedSearch_orgName")
        org_search_field.send_keys(Keys.ENTER)
    except Exception as e :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while submitting search form: {str(e)}', 1, 1)
        if driver: driver.quit()
        traceback.print_exc()
        return links

    try:
        helper.printMessage('DEBUG', 'l.getLinks', 'Finding page size element ...')
        page_size = Select(driver.find_element("id", "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop"))
        helper.printMessage('DEBUG', 'l.getLinks', f'Selecting page size { C.LINES_PER_PAGE }')
        page_size.select_by_visible_text(C.LINES_PER_PAGE)
        helper.printMessage('DEBUG', 'l.getLinks', f'Page size set to{ C.LINES_PER_PAGE }.')
    except Exception as e :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while changing page size: {str(e)}', 1, 1)
        if driver: driver.quit()
        traceback.print_exc()
        return links
    
    try:
        helper.printMessage('DEBUG', 'l.getLinks', 'Reading page count and number of results ...', 0, 1)
        pages_field = driver.find_element("id", "ctl0_CONTENU_PAGE_resultSearch_nombrePageTop")
        pages = int(pages_field.get_attribute("innerText").strip())
        count_field = driver.find_element("id", "ctl0_CONTENU_PAGE_resultSearch_nombreElement")
        count = count_field.get_attribute("innerText").strip()
        helper.printMessage('INFO', 'l.getLinks', f'Number of items: {count:04}. Number of pages: {pages:03}', 0, 1)
    except :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while getting links and pages counts', 1, 1)
        traceback.print_exc()
        if driver: driver.quit()
        return links

    i = 1
    helper.printMessage('DEBUG', 'l.getLinks', f'Reading links from page {i:03}/{pages:03} ...')
    try:
        links = pg2Links(driver, i, pages)
    except:
        helper.printMessage('ERROR', 'l.getLinks', f'Exception raised while getting links from page {i:03}/{pages:03}')
        traceback.print_exc()
        
    try:
        next_page_button = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_resultSearch_PagerTop_ctl2")
    except: 
        next_page_button = None
        traceback.print_exc()
    
    while next_page_button != None:
        next_page_button.click()
        i += 1
        links += pg2Links(driver, i, pages)
        helper.printMessage('TRACE', 'l.getLinks', f'### Looking for next page {i+1:03} ... ')

        try :
            next_page_button = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_resultSearch_PagerTop_ctl2")
            helper.printMessage('TRACE', 'l.getLinks', f'+++ Next page found {i+1:03}')
        except NoSuchElementException: 
            next_page_button = None
            helper.printMessage('TRACE', 'l.getLinks', f'--- Next page {i+1:03} not found', 0, 2)
        except: 
            next_page_button = None
            helper.printMessage('ERROR', 'l.pg2Links', f'Exception while looking for page {i+1:03}', 1, 2)
            traceback.print_exc()

    if driver: driver.quit()
    
    if len(links) != int(count):
        helper.printMessage('ERROR', 'l.getLinks', f'Discrepancy between links count {len(links):04} and items number {count:04}.', 2, 2)
    
    try:
        machine_info = helper.get_system_info()
        machine, created = Machine.objects.get_or_create(
            hostname=machine_info['hostname'],
            os_family=machine_info['os_family'],
            processor=machine_info['processor'],
            defaults={
                "ip_address": machine_info['ip_address'],
                "os_version": machine_info['os_version'],
                "os_release": machine_info['os_release'],
                "architecture": machine_info['architecture'],
                "python_version": machine_info['python_version'],
            }
        )
        if created:
            helper.printMessage('INFO', 'l.getLinks', f'Created Machine info: {machine_info['hostname']}')
        else:
            helper.printMessage('INFO', 'l.getLinks', f'Machine info already exists: {machine_info['hostname']}')

        parkour = Parkour.objects.create(
                started       = started,
                finished      = timezone.now(),
                machine       = machine,
                # deadline_min  = models.DateField()
                # deadline_max  = models.DateField()
                # published_min = models.DateField()
                # published_max = models.DateField()
                page_length   = C.LINES_PER_PAGE,
            )

        if parkour:
            helper.printMessage('DEBUG', 'l.getLinks', 'Created Parkour record.')
        else:
            helper.printMessage('ERROR', 'l.getLinks', 'Errors occurred while creating Parkour record.')

    except Exception as e:
        helper.printMessage('ERROR', 'l.getLinks', f'Error while handling Machine info: {str(e)}', 2,2)


    return links



# def db3Links(back_days=C.PORTAL_DDL_PAST_DAYS):
#     """
#     # Synopsis:
#         Fetch Tenders already on database, with a deadline in the N days back from today (N=back_days).
#     # Params:
#         back_days: Number of days to look back for Tenders.
#     # Return:
#         List of found Tenders, in abbreviated format [chrono, acronym, published].
#     """
#     helper.printMessage('INFO', 'l.db2Links', f'Getting links for saved items, deadline from { back_days } days back ...', 1)
#     # assa = date.today()
#     assa = timezone.now()
#     dt_ddl_start = assa - timedelta(days=back_days)
#     saved_tenders = Tender.objects.filter(deadline__gte=dt_ddl_start)
#     helper.printMessage('DEBUG', 'l.db2Links', f'Found { saved_tenders.count() } eligible saved items', 1)
#     links = []
#     for tender in saved_tenders:
#         try:
#             item = [tender.chrono, tender.acronym, tender.published.strftime("%d/%m/%Y") if tender.published else None]
#             links.append(item)
#         except Exception as xc:
#             helper.printMessage('WARN', 'l.db2Links', f'Error adding item { tender.chrono } to links.', 1)
#             traceback.print_exc()
#     helper.printMessage('DEBUG', 'l.db2Links', f'Constructed { len(links) } link items', 1)

#     return links


# def pg3Links(driver, page_number, pages):
#     """
#     # Synopsis:
#         Get a list of available Consultations from a given page.
#     # Params:
#         driver: Instance of Chrome Webdriver object (web browser window).
#         page_number : Page number to scrape.
#     # Return:
#         List of extremely abbriged Consultations visible on the page.
#         Each element represents [chrono, acronym, published] of a Consultation.
#     """
#     helper.printMessage('INFO', 'l.pg2Links', f'### Getting links from page {page_number:03}/{pages:03}:', 2, 1)
#     links = []
#     try:
#         i = 1
#         body = driver.find_element(By.XPATH, '/html/body/form/div[3]/div[2]/div/div[5]/div[1]/div[2]/div[2]/table/tbody')
        
#         details_btn_xpath = 'tr[1]/td[6]/div/a[1]'
#         details_btn = body.find_element(By.XPATH, details_btn_xpath)
#         while details_btn != None:
#             helper.printMessage('DEBUG', 'l.pg2Links', f'### Getting link {page_number:03}.{i:03} ...')
#             pub_date_xpath = details_btn_xpath.replace('td[6]/div/a[1]', 'td[2]/div[4]')
#             pub_date_element = body.find_element(By.XPATH, pub_date_xpath)
#             env_xpath = details_btn_xpath.replace('td[6]/div/a[1]', 'td[2]/div[5]/a/img')
#             print(f">>>>> Checking for {env_xpath}")
#             has_enviro = len(body.find_elements(By.XPATH, env_xpath)) > 0
            
#             drat = details_btn.get_attribute("href").replace(C.LINK_PREFIX, '')
#             portal_id_text = drat.split(C.LINK_STITCH)[0]
#             organism_text = drat.split(C.LINK_STITCH)[1]
#             links.append([portal_id_text, organism_text, pub_date_element.get_attribute("innerText")])
#             helper.printMessage('DEBUG', 'l.pg2Links', f'+++ Got the link {page_number:03}.{i:03} = {portal_id_text}', 0, 1)
#             i = 1 + i
#             if i > int(C.LINES_PER_PAGE):
#                 details_btn = None
#                 helper.printMessage('TRACE', 'l.pg2Links', f'--- Hit the latest item in page {page_number:03}.')
#             else:
#                 helper.printMessage('TRACE', 'l.pg2Links', f'### Checking for the next elemet: {page_number:03}.{i:03}')
#                 details_btn_xpath = 'tr[' + str(i) + ']/td[6]/div/a[1]'
#                 try:
#                     details_btn = body.find_element(By.XPATH, details_btn_xpath)
#                     helper.printMessage('TRACE', 'l.pg2Links', f'+++ Found next elemet: {page_number:03}.{i:03}')
#                 except NoSuchElementException: 
#                     details_btn = None
#                     helper.printMessage('TRACE', 'l.pg2Links', f'--- Next elemet {page_number:03}.{i:03} not found.', 0, 1)
#                     # traceback.print_exc()
#                 except:
#                     details_btn = None
#                     helper.printMessage('ERROR', 'l.pg2Links', f'Exception while getting links from page {page_number:03}', 1, 2)
#                     traceback.print_exc()

#     except Exception:
#         helper.printMessage('FATAL', 'l.pg2Links', f'Exception while getting links from page {page_number:03}', 1, 2)
#         traceback.print_exc()

#     return links
