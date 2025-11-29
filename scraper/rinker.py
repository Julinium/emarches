import os, csv, random, json, traceback
import requests, pytz
from datetime import datetime, date, timedelta
from django.utils import timezone
from bs4 import BeautifulSoup

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from scraper import constants as C
from scraper import helper

from base.models import Tender


REFRESH_SAVED = True
rabat_tz = pytz.timezone("Africa/Casablanca")


def fillSearchForm(driver, back_days=C.PORTAL_DDL_PAST_DAYS):
    assa = date.today()
    dt_ddl_start = assa - timedelta(days=back_days)
    date_ddl_start = dt_ddl_start.strftime("%d/%m/%Y")

    helper.printMessage('INFO', 'l.fillSearchForm', 'Submitting search form ...')
    try:
        helper.printMessage('INFO', 'l.page2Links', f'Deadline backward days set to {C.PORTAL_DDL_PAST_DAYS} days.', 2)
        el_ddl_start = driver.find_element("id", "ctl0_CONTENU_PAGE_AdvancedSearch_dateMiseEnLigneStart")
        el_ddl_start.clear()
        el_ddl_start.send_keys(date_ddl_start)
        
    except Exception:
        helper.printMessage('FATAL', 'l.fillSearchForm', 'Could not find date field:')
        traceback.print_exc()
        

def page2Links(driver, page_number, pages):
    """
    # Synopsis:
        Get a list of available Consultations from a given page.
    # Params:
        driver: An instance of Chrome Webdriver object. That is a web browser window.
        page_number : Page number to scrape.
    # Return:
        List of extremely abbriged Consultations visible on the page.
        Each element represents [portal id, organism acronym, published date] of a Consultation.
        The first two values can be used to obtain a working link to the Consultaion on the portal.
    """
    helper.printMessage('INFO', 'l.page2Links', f'### Getting links from page {page_number:03}/{pages:03}:', 2, 1)
    links = []
    try:
        i = 1
        body = driver.find_element(By.XPATH, '/html/body/form/div[3]/div[2]/div/div[5]/div[1]/div[2]/div[2]/table/tbody')
        details_btn_xpath = 'tr[1]/td[6]/div/a[1]'
        details_btn = body.find_element(By.XPATH, details_btn_xpath)
        while details_btn != None:
            pub_date_xpath = details_btn_xpath.replace('td[6]/div/a[1]', 'td[2]/div[4]')
            pub_date_element = body.find_element(By.XPATH, pub_date_xpath)
            drat = details_btn.get_attribute("href").replace(C.LINK_PREFIX, '')
            portal_id_text = drat.split(C.LINK_STITCH)[0]
            organism_text = drat.split(C.LINK_STITCH)[1]
            helper.printMessage('DEBUG', 'l.page2Links', f'### Getting link {page_number:03}.{i:03} = {portal_id_text} ...')
            links.append([portal_id_text, organism_text, pub_date_element.get_attribute("innerText")])
            helper.printMessage('DEBUG', 'l.page2Links', f'+++ Got the link {page_number:03}.{i:03} = {portal_id_text}', 0, 1)
            i = 1 + i
            if i > int(C.LINES_PER_PAGE):
                helper.printMessage('TRACE', 'l.page2Links', f'--- Hit the latest item in page.')
                details_btn = None
            else:
                helper.printMessage('TRACE', 'l.page2Links', f'### Checking for the next elemet: {page_number:03}.{i:03}')
                details_btn_xpath = 'tr[' + str(i) + ']/td[6]/div/a[1]'
                try: 
                    details_btn = body.find_element(By.XPATH, details_btn_xpath)
                    helper.printMessage('TRACE', 'l.page2Links', f'+++ Found next elemet: {page_number:03}.{i:03}')
                except: 
                    helper.printMessage('TRACE', 'l.page2Links', f'--- Next elemet {page_number:03}.{i:03} not found.', 0, 1)
                    details_btn = None
    except Exception:
        helper.printMessage('FATAL', 'l.page2Links', f'Exception while getting links from page {page_number:03}', 1, 2)
        traceback.print_exc()

    return links


def exportLinks(links):
    """
    # Synopsis:
        Exports links to a csv file. File is placed under {SELENO_DIR/exports} and named links.csv.
    # Params:
        links: List of links to export.
    # Return:
        full path to the exported csv file.
    """
    helper.printMessage('INFO', 'l.exportLinks', 'Exporting links to a file ...\n')
    file = ''
    if len(links) > 0 :
        try:
            expo_dir = f'{C.SELENO_DIR}/exports'
            if not os.path.exists(expo_dir) : os.mkdir(expo_dir)
            file = f'{expo_dir}/links.csv'
            with open(file, 'w', newline='') as linkscsv:
                linkwriter = csv.writer(linkscsv)
                for l in links:
                    linkwriter.writerow(l)
        except Exception as e :
            helper.printMessage('FATAL', 'l.exportLinks', f'Something went wrong while exporting links')
            traceback.print_exc()
            return ''
        helper.printMessage('INFO', 'l.exportLinks', 'Exported links to file. No complains.\n')
    else:
        helper.printMessage('WARN', 'l.exportLinks', 'File was empty and was not exported.\n')
    return file


def getSavedLinks(back_days=C.PORTAL_DDL_PAST_DAYS):
    helper.printMessage('INFO', 'l.getSavedLinks', f'Getting links for saved items, deadline from { back_days } days back ...', 1)
    assa = date.today()
    dt_ddl_start = assa - timedelta(days=back_days)
    saved_tenders = Tender.objects.filter(deadline__gte=dt_ddl_start)
    helper.printMessage('DEBUG', 'l.getSavedLinks', f'Found { saved_tenders.count() } eligible saved items', 1)
    links = []
    for tender in saved_tenders:
        item = [tender.chrono, tender.acronym, tender.published.strftime("%d/%m/%Y")]
        links.append(item)
    helper.printMessage('DEBUG', 'l.getSavedLinks', f'Constructed { len(links) } link items', 1)
    
    return links


def get_headers():
    return {
        "User-Agent": helper.getUa(),
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"
    }


def getLinks(back_days=C.PORTAL_DDL_PAST_DAYS):
    """
    # Synopsis:
        Get a list of available Consultations on Portal.
    # Params:
        None.
    # Return:
        List of extremely abbriged Consultations.
        Each element represents [portal id, organism acronym, published date] of a Consultation.
        The first two values can be used to obtain a working link to the Consultaion on the portal.
    """

    links = []
    page = 1
    items_per_page = 10 #500

    # https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons#
    # https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons

    rua = helper.getUa()
    rua_label = "Random"    
    url = f"{C.SITE_INDEX}?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"

    helper.printMessage('DEBUG', 'l.getLinks', f'Using UA: {rua_label}.')
    headino = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7,ar;q=0.6",
        "cache-control": "no-cache",
        "connection": "keep-alive",
        "content-type": "application/x-www-form-urlencoded",
        "Referer": url,
        "User-Agent": rua, 
        }
    sessiono = requests.Session()
    sessiono.headers=headino

    
    res_form = sessiono.get(url, headers=headino)
    res_form.raise_for_status()

    # res_form = requests.get(url, headers=get_headers(), params=params, timeout=15)
    # s = r.status_code

    print("\n=======================")
    print("res_form.status_code:", res_form.status_code)
    print("=======================\n")
    soup = BeautifulSoup(res_form.text, 'html.parser')
    
    
    PRADO_PAGESTATE = soup.find('input', {'id': 'PRADO_PAGESTATE'})['value']
    PRADO_POSTBACK_TARGET = soup.find('input', {'id': 'PRADO_POSTBACK_TARGET'})['value']
    PRADO_POSTBACK_PARAMETER = soup.find('input', {'id': 'PRADO_POSTBACK_PARAMETER'})['value']

    print(f'PRADO_PAGESTATE (/{ len(PRADO_PAGESTATE) })======== ', PRADO_PAGESTATE[:64], '...')
    print('PRADO_POSTBACK_TARGET ======== ', PRADO_POSTBACK_TARGET[:64])
    print('PRADO_POSTBACK_PARAMETER ======== ', PRADO_POSTBACK_PARAMETER[:64])

    wassa = timezone.now().astimezone(rabat_tz)
    wassa_str = wassa.strftime('%Y-%m-%d')
# 
    payload = {
        "PRADO_PAGESTATE": PRADO_PAGESTATE,
        "PRADO_POSTBACK_TARGET": "ctl0$CONTENU_PAGE$AdvancedSearch$lancerRecherche",
        "PRADO_POSTBACK_PARAMETER": "undefined",
        # "PRADO_POSTBACK_TARGET": PRADO_POSTBACK_TARGET,
        # "PRADO_POSTBACK_PARAMETER": PRADO_POSTBACK_PARAMETER,
        # "ctl0$CONTENU_PAGE$resultSearch$numPageTop": page,
        # "ctl0$CONTENU_PAGE$resultSearch$listePageSizeTop": items_per_page,
        "ctl0$menuGaucheEntreprise$quickSearch": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$type_rechercheEntite": "floue",
        "ctl0$CONTENU_PAGE$AdvancedSearch$classification" : 0,
        "ctl0$CONTENU_PAGE$AdvancedSearch$organismesNames" : 0,
        "ctl0$CONTENU_PAGE$AdvancedSearch$choixInclusionDescendancesServices": "ctl0$CONTENU_PAGE$AdvancedSearch$inclureDescendances",
        "ctl0$CONTENU_PAGE$AdvancedSearch$orgName": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$reference": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$procedureType": 0,
        "ctl0$CONTENU_PAGE$AdvancedSearch$categorie": 0,
        "ctl0$CONTENU_PAGE$AdvancedSearch$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$idReferentielZoneTextFrom": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$idReferentielZoneTextTo": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$modeRecherche": 1,
        "ctl0$CONTENU_PAGE$AdvancedSearch$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$typeData": "montant",
        "ctl0$CONTENU_PAGE$AdvancedSearch$idAtexoLtRefRadio$RepeaterReferentielRadio$ctl0$ClientIdsRadio": "ctl0_CONTENU_PAGE_AdvancedSearch_idAtexoLtRefRadio_RepeaterReferentielRadio_ctl0_OptionOui#ctl0_CONTENU_PAGE_AdvancedSearch_idAtexoLtRefRadio_RepeaterReferentielRadio_ctl0_OptionNon",
        "ctl0$CONTENU_PAGE$AdvancedSearch$idAtexoLtRefRadio$RepeaterReferentielRadio$ctl0$modeRecherche": 1,
        "ctl0$CONTENU_PAGE$AdvancedSearch$idsSelectedGeoN2": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$numSelectedGeoN2": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$domaineActivite$idsDomaines": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$qualification$idsQualification": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$qualification$libelleQualif": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$agrements$idsSelectedAgrements": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneStart": wassa_str,
        "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneEnd": "31/12/2030",
        "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeStart": "01/01/2001",
        "ctl0$CONTENU_PAGE$AdvancedSearch$dateMiseEnLigneCalculeEnd": wassa_str,
        "ctl0$CONTENU_PAGE$AdvancedSearch$keywordSearch": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$rechercheFloue": "ctl0$CONTENU_PAGE$AdvancedSearch$floue",
        "ctl0$CONTENU_PAGE$AdvancedSearch$orgNameAM": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$refRestreinteSearch": "",
        "ctl0$CONTENU_PAGE$AdvancedSearch$accesRestreinteSearch": "",
    }

    ###################

    # cons_uri = f"{link_item[0]}{C.LINK_STITCH}{link_item[1]}"
    # cons_link = f'{C.LINK_PREFIX}{cons_uri}'
    # dce_link = f'{C.SITE_INDEX}?page=entreprise.EntrepriseDownloadCompleteDce&reference={link_item[0]}&orgAcronym={link_item[1]}'
    # /index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons
    url = "https://www.marchespublics.gov.ma/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnCons"
    try:
        print("trying .......................")
        # print(sessiono.headers)
        response = sessiono.post(url, headers=headino, params=payload, timeout=C.REQ_TIMEOUT)  # driver.get(lots_link)
        print("response.status_code:", response.status_code)
        bowl = BeautifulSoup(response.text, 'html.parser')
        print("bowwwwwwwwwl:\n", bowl)
    except Exception as x:
        helper.printMessage('ERROR', 'l.getLinks', f'Exception raised while getting Tenders list {str(url.replace(C.SITE_INDEX, '[...]'))}: {x}')
        return None

    helper.printMessage('DEBUG', 'l.getLinks', f'Getting  Tenders list from page: { page }')
    if response.status_code != 200 :
        helper.printMessage('ERROR', 'l.getLinks', f'Request to server page returned a {response.status_code} status code.')
        if response.status_code == 429:
            helper.printMessage('ERROR', 'l.getLinks', f'Too many Requests, said the server: {response.status_code} !')
            helper.sleepRandom(300, 600)
        return None

    bowl = BeautifulSoup(response.text, 'html.parser')
    # soup = bowl.find(class_='ongletLayer')

    print("bowl:\n", bowl)

    pages_field = soup.find("span", {"id": "ctl0_CONTENU_PAGE_resultSearch_nombrePageTop"})
    pages = int(pages_field.text.strip())

    print("\n\t\t===========")
    print("\t\tpages:", pages)
    print("\t\t===========\n")

    helper.sleepRandom(3000, 6000)

    ###################


    results_request = request.post(url, params=payload)

    driver = helper.getDriver(url)
    
    links = []
    pages = 0
    count = 0
    if driver == None: return links
    
    fillSearchForm(driver, back_days)
    
    try:
        helper.printMessage('DEBUG', 'l.getLinks', 'Submitting search form with default dates and empty terms ...', 1)
        org_search_field = driver.find_element("id", "ctl0_CONTENU_PAGE_AdvancedSearch_orgName")
        org_search_field.send_keys(Keys.ENTER)
    except Exception as e :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while submitting search form: {str(e)}', 1, 1)
        if driver: driver.quit()
        return links

    try:
        helper.printMessage('DEBUG', 'l.getLinks', 'Finding page size element ...')
        page_size = Select(driver.find_element("id", "ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop"))
        helper.printMessage('DEBUG', 'l.getLinks', f'Selecting page size { C.LINES_PER_PAGE }')
        page_size.select_by_visible_text(C.LINES_PER_PAGE)
    except Exception as e :
        helper.printMessage('ERROR', 'l.getLinks', f'Something went wrong while changing page size: {str(e)}', 1, 1)
        if driver: driver.quit()
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
    # helper.printMessage('DEBUG', 'l.getLinks', f'Reading links from page {i:03}/{pages:03} ... \n')

    links = page2Links(driver, i, pages)
    try: next_page_button = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_resultSearch_PagerTop_ctl2")
    except: next_page_button = None
    
    while next_page_button != None:
        next_page_button.click()
        i += 1
        links += page2Links(driver, i, pages)
        helper.printMessage('TRACE', 'l.getLinks', f'### Looking for next page {i+1:03} ... ')
            
        try :
            next_page_button = driver.find_element(By.ID, "ctl0_CONTENU_PAGE_resultSearch_PagerTop_ctl2")
            helper.printMessage('TRACE', 'l.getLinks', f'+++ Next page found {i+1:03}')
        except: 
            helper.printMessage('TRACE', 'l.getLinks', f'--- Next page {i+1:03} not found', 0, 2)
            next_page_button = None

    if driver: driver.quit()
    
    if len(links) != int(count):
        helper.printMessage('ERROR', 'l.getLinks', f'Discrepancy between links count {len(links):04} and items number {count:04}.', 2, 2)

    return links
