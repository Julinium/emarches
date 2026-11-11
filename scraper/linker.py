import csv
import json
import os
import re
import random
import traceback
from datetime import timedelta
from django.utils import timezone
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from base.models import Tender, Link, Parkour, Machine
from scraper import constants as C
from scraper import helper



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

    try:
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
    helper.printMessage('DEBUG', 'l.pg2Links', f'### Looking at page {page_number:02}/{pages}...')
    links = []
    try:
        i = 0
        list_body_xpath = "/html/body/form/div[3]/div[1]/div[1]/div[6]/div[1]"
        list_body = driver.find_element(By.XPATH, list_body_xpath)

        list_body_html = list_body.get_attribute("innerHTML")
        soup = BeautifulSoup(list_body_html, "html.parser")

        rows = [
            div for div in soup.find_all('div', class_='contentColumn') 
            if len(div.get('class', [])) == 1
        ]
        rows_count = len(rows)
        helper.printMessage('DEBUG', 'l.pg2Links', f'Found {rows_count} items on page {page_number:02}.')

        for row in rows:
            i += 1
            helper.printMessage('TRACE', 'l.pg2Links', f'\tLooking at row #{i:03}/{rows_count:03} in page {page_number:02}...')
            try:
                chrono = None
                acronym = None
                published = None
                has_enviro = None
                onclick_value = row.get('onclick', '')
                match = re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', onclick_value)
                if match:
                    url = match.group(1)
                    parsed_url = urlparse(url)
                    params = parse_qs(parsed_url.query)
                    chrono = params.get('refConsultation', [None])[0]
                    acronym = params.get('orgAcronyme', [None])[0]
                    
                has_enviro = bool(row.find('img', src='ressources/eco.png'))

                link = {
                    "chrono": chrono,
                    "acronym": acronym,
                    "published": published,
                    "has_enviro": has_enviro,
                }
                links.append(link)
                helper.printMessage('DEBUG', 'l.pg2Links', f'\tGot link {i:02}@{page_number:02}/{pages} = {chrono}.')
                helper.printMessage('TRACE', 'l.pg2Links', f'\tLink data: {link}.')

            except Exception as xc:
                helper.printMessage('ERROR', 'l.pg2Links', f'Could not get link for {page_number:02}.{i:02}', 1, 2)
                traceback.print_exc()

    except Exception:
        helper.printMessage('ERROR', 'l.pg2Links', f'Exception while getting links from page {page_number:02}/{pages}', 1, 2)
        traceback.print_exc()

    helper.printMessage('INFO', 'l.pg2Links', f'=== Got {len(links)} links from page {page_number:02}/{pages}')
    
    return links


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

    started = timezone.now()
    url = f"{C.SITE_INDEX}?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"
    driver = helper.getDriver(url)
    
    links = []
    pages = 0
    count = 0
    if driver == None: return links

    try:
        helper.printMessage('TRACE', 'l.getLinks', 'Filling in search form ...', 1)
        fillForm(driver, back_days)
    except Exception as e :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while filling in search form.', 1, 1)
        traceback.print_exc()
    
    try:
        helper.printMessage('TRACE', 'l.getLinks', 'Submitting search form ...', 1)
        org_search_field = driver.find_element("id", "ctl0_CONTENU_PAGE_AdvancedSearch_orgName")
        org_search_field.send_keys(Keys.ENTER)
    except Exception as e :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while submitting search form.', 1, 1)
        traceback.print_exc()

    try:
        helper.printMessage('DEBUG', 'l.getLinks', 'Finding page size element ...')
        page_size = Select(driver.find_element("id", "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop"))
        helper.printMessage('DEBUG', 'l.getLinks', f'Selecting page size { C.LINES_PER_PAGE }')
        page_size.select_by_visible_text(C.LINES_PER_PAGE)
        helper.printMessage('DEBUG', 'l.getLinks', f'Page size set to { C.LINES_PER_PAGE }.')
    except Exception as e :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while changing page size: {str(e)}', 1, 1)
        # if driver: driver.quit()
        traceback.print_exc()
        # return links
    
    try:
        helper.printMessage('DEBUG', 'l.getLinks', 'Reading page count and number of results ...', 0, 1)
        pages_field = driver.find_element("id", "ctl0_CONTENU_PAGE_resultSearch_nombrePageTop")
        pages = int(pages_field.get_attribute("innerText").strip())
        count_field = driver.find_element("id", "ctl0_CONTENU_PAGE_resultSearch_nombreElement")
        count = count_field.get_attribute("innerText").strip()
        helper.printMessage('INFO', 'l.getLinks', f'Number of items: {count:04}. Number of pages: {pages}', 0, 1)
    except :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while getting links and pages counts', 1, 1)
        traceback.print_exc()
        if driver: driver.quit()
        return links

    i = 1
    try:
        links = pg2Links(driver, i, pages)
    except:
        helper.printMessage('ERROR', 'l.getLinks', f'Exception raised while getting links from page {i:02}/{pages}')
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
        helper.printMessage('TRACE', 'l.getLinks', f'### Looking for next page {i+1:02}/{pages} ... ')

        try :
            next_page_button = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_resultSearch_PagerTop_ctl2")
            helper.printMessage('TRACE', 'l.getLinks', f'+++ Next page found {i+1:02}/{pages}')
        except NoSuchElementException: 
            next_page_button = None
            helper.printMessage('TRACE', 'l.getLinks', f'--- Next page {i+1:02}/{pages} not found', 0, 2)
        except TimeoutError: 
            traceback.print_exc()
            helper.sleepRandom(60, 90)
        except: 
            next_page_button = None
            helper.printMessage('ERROR', 'l.pg2Links', f'Exception while looking for page {i+1:02}/{pages}', 1, 2)
            traceback.print_exc()

        # if i % 8 == 0:
        #     helper.sleepRandom(10, 15)

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
                page_length   = C.LINES_PER_PAGE,
            )

        if parkour:
            helper.printMessage('DEBUG', 'l.getLinks', 'Created Parkour record.')
        else:
            helper.printMessage('ERROR', 'l.getLinks', 'Errors occurred while creating Parkour record.')

    except Exception as e:
        helper.printMessage('ERROR', 'l.getLinks', f'Error while handling Machine info: {str(e)}', 2,2)


    return links


