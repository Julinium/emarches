
# 01. Make a list of items to handle:
    ## Items with deadline later than a given date (past N days).
    ## Special items (failed previously, requested, ...)

# 02. Loop over the "list" of items:
    ## If refresh is required, delete files if any.
    ## If no files, get the files.
    ## If item in a special list, remove it.


# 03. Periodically, check for and delete:
    ## Orphan files.
    ## Files for items over certain age old.

import os, random, re, requests, traceback
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from scraper import helper
from scraper import constants as C

from base.models import Tender, FileToGet


def getFileables():
    """
    Get a list of Tenders that need DCE to be downloaded.
    That are either Tenders with an open FilesToGet insatnce (recently created or updated), or
    Tenders with empty DCE folders or no DCE folder at all.

    # Return: Tender model QuerySet.
    """

    target_date = datetime.now() - timedelta(days=C.CLEAN_DCE_AFTER_DAYS)
    helper.printMessage("DEBUG", 'd.getFileables', "Getting fresh Tenders (created or recently updated) ...")
    fresh_tenders = Tender.objects.filter(files_to_get__closed=False, deadline__gte=target_date).distinct()
    helper.printMessage("DEBUG", 'd.getFileables', f"Got {fresh_tenders.count()} fresh Tenders.")
    helper.printMessage("DEBUG", 'd.getFileables', "Getting Tenders with no or empty DCE folders ...")
    nodce_tenders = getEmpties().distinct()
    helper.printMessage("DEBUG", 'd.getFileables', f"Got {nodce_tenders.count()} Tenders with no or empty folders.")

    return fresh_tenders | nodce_tenders


def getEmpties(past_days=C.CLEAN_DCE_AFTER_DAYS, batch_size=1000):
    """
    Get Tenders with empty DCE folders or no DCE folder at all.

    # Return: Tender model QuerySet.
    """    

    helper.printMessage("DEBUG", 'd.getEmpties', f"Getting Tenders with deadline older than {past_days} days ...")
    target_date = datetime.now() - timedelta(days=past_days)
    current_tenders = Tender.objects.filter(deadline__gte=target_date)
    helper.printMessage("DEBUG", 'd.getEmpties', f"Got {current_tenders.count()} Tenders deadline older than {past_days} days.")

    tenders_without_files = []
    helper.printMessage("DEBUG", 'd.getEmpties', "Checking against files on disk ...")
    for tender_id, chrono in current_tenders.values_list('id', 'chrono').iterator(chunk_size=batch_size):
        if chrono:
            if is_empty_or_nonexistent(f"{C.MEDIA_ROOT}/dce/{C.DL_PATH_PREFIX}{chrono}"):
                tenders_without_files.append(tender_id)

    helper.printMessage("DEBUG", 'd.getEmpties', f"Found {current_tenders.count()} items ...")
    return current_tenders.filter(id__in=tenders_without_files)


def is_empty_or_nonexistent(folder_path):
    """
    Check if a folder_path is empty or does not exist.
    # Return: Boolean
    """

    if not os.path.exists(folder_path):
        return True
    return not any(os.path.isfile(os.path.join(folder_path, item)) for item in os.listdir(folder_path))


def getDCE(tender):
    """
    The real job of downloading the DCE for a Tender and saving it to the local storage#
    # Arguments:
        ## Tender instance.
    # Return: Integer: 0 if success, 1 else.
    """

    chrono = tender.chrono
    acro   = tender.acronym

    def make_link(type=None):
        if type == 'query': return f'{C.SITE_INDEX}?page=entreprise.EntrepriseDemandeTelechargementDce&refConsultation={chrono}&orgAcronyme={acro}'
        if type == 'file':  return f'{C.SITE_INDEX}?page=entreprise.EntrepriseDownloadCompleteDce&reference={chrono}&orgAcronym={acro}'
                                 # f'{C.SITE_INDEX}?page=entreprise.EntrepriseDownloadReglement&reference=OTQ1Mzcx&orgAcronyme={acro}'
        return None 


    def get_filename(cd):
        if not cd: return None
        fname = re.findall('filename=(.+)', cd)
        if len(fname) == 0: return None
        return fname[0]


    if not os.path.exists(C.MEDIA_ROOT): 
        helper.printMessage('ERROR', 'd.getDCE', f'Could not read media root {C.MEDIA_ROOT}.')
        return 1
    if not chrono or not acro : 
        helper.printMessage('ERROR', 'd.getDCE', f'Incorrect parameter was received.')
        return 1

    con_path = os.path.join(C.MEDIA_ROOT, f'dce/{C.DL_PATH_PREFIX}{chrono}')
    if not os.path.exists(con_path): os.makedirs(con_path)
    if not os.path.exists(con_path):
        helper.printMessage('ERROR', 'd.getDCE', f'Could not find DCE directory {con_path}.')
        return 1


    if len(C.USER_AGENTS) == 0 : 
        DEFAULT_UA = 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
        helper.printMessage('DEBUG', 'd.getDCE', f'UA list was empty. Using default: {DEFAULT_UA}.')
        headino = {"User-Agent": DEFAULT_UA}
    else :
        rua = helper.getUa()
        rua_label = "Random"
        try:
            start_delimiter = "Mozilla/5.0 ("
            end_delimiter = "; "
            start_index = rua.index(start_delimiter) + len(start_delimiter)
            end_index = rua.index(end_delimiter, start_index)
            rua_label = rua[start_index:end_index]
        except ValueError as ve:
            helper.printMessage('ERROR', 'd.getDCE', f'Error trimming UA: {str(ve)}')

        helper.printMessage('DEBUG', 'd.getDCE', f'Using random UA: {rua_label}.')
        headino = {"User-Agent":  rua}

    http_session = requests.Session()

    url_query = make_link('query')
    url_file = make_link('file')
    
    helper.printMessage('DEBUG', 'd.getDCE', 'Building Tender and files links.')
    helper.printMessage('TRACE', 'd.getDCE', f'Cons link : {url_query.replace(C.SITE_INDEX, '')}')
    helper.printMessage('TRACE', 'd.getDCE', f'File link : {url_file.replace(C.SITE_INDEX, '')}')

    try: request_query = http_session.get(url_query, headers=headino, timeout=C.REQ_TIMEOUT)
    except Exception as xc: 
        helper.printMessage('ERROR', 'd.getDCE', str(xc))
        return 1

    soup = BeautifulSoup(request_query.content, 'html.parser')
    
    if request_query.status_code != 200 : 
        helper.printMessage('ERROR', 'd.getDCE', f'Download query: Response Status Code: {request_query.status_code} !')
        helper.printMessage('TRACE', 'd.getDCE', f'\n\n\n===========\n{soup}\n===========\n\n')
        
        helper.sleepRandom(C.SLEEP_4XX_MIN, C.SLEEP_4XX_MAX)
        return request_query.status_code
    else:
        helper.printMessage('DEBUG', 'd.getDCE', f'Download query returned 200.')

    prado_page_state = None
    try: prado_page_state = soup.find(id="PRADO_PAGESTATE")['value']
    except: pass

    prado_pbk_target = None
    try: prado_pbk_target = soup.find(id="PRADO_POSTBACK_TARGET")['value']
    except: pass

    prado_pbk_parame = None
    try: prado_pbk_parame = soup.find(id="PRADO_POSTBACK_PARAMETER")['value']
    except: pass

    datano = {
        'ctl0$menuGaucheEntreprise$quickSearch': 'Recherche rapide',
        'ctl0$CONTENU_PAGE$ctl5$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$modeRecherche': '1',
        'ctl0$CONTENU_PAGE$ctl5$idReferentielZoneText$RepeaterReferentielZoneText$ctl0$typeData': 'montant',
        'ctl0$CONTENU_PAGE$ctl5$idRefRadio$RepeaterReferentielRadio$ctl0$ClientIdsRadio': 'ctl0_CONTENU_PAGE_ctl5_idRefRadio_RepeaterReferentielRadio_ctl0_OptionOui#ctl0_CONTENU_PAGE_ctl5_idRefRadio_RepeaterReferentielRadio_ctl0_OptionNon',
        'ctl0$CONTENU_PAGE$ctl5$idRefRadio$RepeaterReferentielRadio$ctl0$modeRecherche': '1',
        'ctl0$CONTENU_PAGE$ctl5$idAtexoRefDomaineActivites$defineCodePrincipal': '(Code principal)',
        'ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$RadioGroup': 'ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$choixTelechargement',
        'ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$accepterConditions': 'on',
        'ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$clientId': 'ctl0_CONTENU_PAGE_EntrepriseFormulaireDemande', 
        'ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$etablissementEntreprise': 'ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$france',
        'ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$pays': '0',
    }

    creds = {'fname': 'Hamid', 'lname': 'ZAHIRI', 'email': 'h.zahir.pro@menara.ma'}
    if len(C.DCE_CREDS) > 0:
        creds = C.DCE_CREDS[random.randint(0, len(C.DCE_CREDS)-1)]
        helper.printMessage('DEBUG', 'd.getDCE', f'Using Credentials for: {creds.get("fname")} {creds.get("lname")}.')
    else: helper.printMessage('DEBUG', 'd.getDCE', f'Using Credentials for: {creds.get("fname")} {creds.get("lname")}.')

    datano['ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$prenom'] = creds.get('fname', 'Mourad')
    datano['ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$nom'] = creds.get('lname', 'Mountassir')
    datano['ctl0$CONTENU_PAGE$EntrepriseFormulaireDemande$email'] = creds.get('email', 'mmountassirsky@caramail.com')

    if prado_page_state: datano['PRADO_PAGESTATE'] = prado_page_state
    if prado_pbk_target: datano['PRADO_POSTBACK_TARGET'] = prado_pbk_target
    if prado_pbk_parame: datano['PRADO_POSTBACK_PARAMETER'] = prado_pbk_parame
    
    try: request_form = http_session.post(url_query, headers=headino, data=datano, timeout=C.REQ_TIMEOUT)
    except Exception as xc: 
        helper.printMessage('ERROR', 'd.getDCE', 'Exception raised while submitting form.')
        helper.printMessage('ERROR', 'd.getDCE', str(xc)) 
        return 1
    
    if request_form.status_code != 200 :
        helper.printMessage('ERROR', 'd.getDCE', f'Form submission: Response Status Code: {request_form.status_code} !')
        helper.sleepRandom(C.SLEEP_4XX_MIN, C.SLEEP_4XX_MAX)
        return request_form.status_code
    else: helper.printMessage('DEBUG', 'd.getDCE', f'Form submission: Successful')

    try:
        helper.printMessage('DEBUG', 'd.getDCE', f'Requesting file for Tender { tender.chrono }')
        request_file = http_session.get(url_file, headers=headino, timeout=C.DLD_TIMEOUT)
    except requests.exceptions.Timeout:
        helper.printMessage('ERROR', 'd.getDCE', "Request timed out! Exception message: " + str(xc))
    except Exception as xc: 
        helper.printMessage('ERROR', 'd.getDCE', str(xc))
        return 1
    
    if request_file.status_code != 200 :
        helper.printMessage('ERROR', 'd.getDCE', f'Getting file: Response Status Code: {request_file.status_code} !')
        helper.sleepRandom(C.SLEEP_4XX_MIN, C.SLEEP_4XX_MAX)
        return request_file.status_code
    else: helper.printMessage('DEBUG', 'd.getDCE', f'Getting file returned Status Code: {request_file.status_code}')

    try:
        filename_cd = get_filename(request_file.headers.get('content-disposition')).replace('"', '').replace(';', '')
    except Exception as xc:
        helper.printMessage('WARN', 'd.getDCE', 'Could not get file name from portal.')
        helper.printMessage('WARN', 'd.getDCE', str(xc))
        helper.printMessage('ERROR', 'd.getDCE', 'Looks like the server sent back a page, not a file !')
        return 1

    fiel_name_base = os.path.splitext(filename_cd)[0]
    file_extension = os.path.splitext(filename_cd)[1]
    cleaned_name = helper.text2Alphanum(fiel_name_base, allCapps=True, dash='-', minLen=8, firstAlpha='M', fillerChar='0')
    
    filename_base = f'{C.FILE_PREFIX}-{cleaned_name}{file_extension}'
    filename = os.path.join(con_path, filename_base)
    helper.printMessage('DEBUG', 'd.getDCE', f'Writing file content to {filename_base} ... ')

    try:
        with open(filename, 'wb') as file:
            bytes_written = file.write(request_file.content)
            helper.printMessage('DEBUG', 'd.getDCE', f'... Bytes written: {bytes_written}/{len(request_file.content)}.')
        # Verify the file size
        if bytes_written == len(request_file.content):
            try:
                helper.printMessage('DEBUG', 'd.getDCE', f'Trying to remove file request for {chrono}.')
                f2g = tender.files_to_get.all()
                f2g.delete()
                helper.printMessage('DEBUG', 'd.getDCE', f'+++ Removed file request for {chrono}.')
            except Exception as x:
                helper.printMessage('ERROR', 'd.getDCE', "Exception removing file request.")
                traceback.print_exc()
            if tender.size_bytes != bytes_written:
                try:
                    helper.printMessage('DEBUG', 'd.getDCE', f'Updating file size bytes for {chrono}.')
                    tender.size_bytes = bytes_written
                    tender.save()
                except Exception as x:
                    helper.printMessage('ERROR', 'd.getDCE', "Exception updating file size bytes.")
                    traceback.print_exc()                
            else:
                helper.printMessage('DEBUG', 'd.getDCE', f'File size bytes for id {chrono} was the same.')
        else:
            raise IOError("File size mismatch: Not all content was written.")
        if os.path.getsize(filename) == 0: raise IOError("File was created but is empty. Go and know why!")
    except Exception as e:
        helper.printMessage('ERROR', 'd.getDCE', f"Error writing data to file: {e}")
        return 1

    return 0


