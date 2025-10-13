import os, csv, random, time, pytz, zipfile, re, unicodedata, traceback
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from selenium import webdriver

from scraper import constants as C

def printMessage(level='---', raiser='---', message='!!! Empty Message !!!', before=0, after=0):
    """
    # Synopsis:
    Prints a message to the stdout, tagged with a level and current datetime.

    # Params:
        # level:    Level of the message.
        # raiser:   Module or Function raising the message.
        # message:  Text to print.
        # before: Empty lines to print before the message.
        # after: Empty lines to print after the message.

    # Return: nothing
    """

    prefix = f'{before * "\n"}' if before > 0 else ""
    suffix = f'{after * "\n"}' if after > 0 else ""
    printout = False
    if level in C.LOGS_LEVELS: 
        if C.LOGS_LEVELS[level] >= C.VERBOSITY:
            printout = True
    else:
        printout = True

    if printout:
        print(f'{prefix}[{datetime.now(timezone.utc).strftime(C.LOG_TIME_FORMAT)}][{level}][{raiser}] {message}{suffix}')


def getAmount(texte: str) -> Decimal:
    """
    Converts a string containing a monetary amount to a Decimal.

    Args:
        texte: The text containing the amount (e.g., "1,234.56 DH", "123,123,45").

    Returns:
        Decimal: The parsed monetary value.
        Decimal('0'): For empty strings, "-", or "--".
        Decimal('-1'): If conversion fails.
    """
    if not texte or texte.strip() == "" or texte == "-":
        return Decimal('0')
    if "--" in texte:
        return Decimal('0')

    try:
        f = texte.strip().replace("\u202f", "").replace("\u00a0", "").replace(" ", "")
        f = f.replace("DH", "").replace("MAD", "").replace("TTC", "")

        if "/" in f:
            f = f.split("/")[0]
        if "par" in f:
            f = f.split("par")[0]

        if "," in f and "." in f:
            parts = f.rsplit(",", 1) if f.rfind(",") > f.rfind(".") else f.rsplit(".", 1)
            f = "".join(parts[0].replace(",", "").replace(".", "") + "." + parts[1])
        elif "," in f:
            parts = f.rsplit(",", 1)
            f = parts[0].replace(",", "") + "." + parts[1] if len(parts) == 2 else f.replace(",", ".")
        elif "." in f:
            parts = f.rsplit(".", 1)
            f = parts[0].replace(".", "") + "." + parts[1] if len(parts) == 2 else f

        return Decimal(f.strip())
    except (InvalidOperation, ValueError):
        printMessage('ERROR', 'h.getAmount', f'Could not get Amount from "{texte}". Set to 0')
        traceback.print_exc()
        return Decimal('0')


def text2Alphanum(text, allCapps=True, dash='-', minLen=8, firstAlpha='M', fillerChar='0'):
    normalized = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode()
    cleaned = re.sub(r'[^A-Za-z0-9]', '-', normalized)
    cleaned = re.sub(r'-+', '-', cleaned)
    cleaned = cleaned.strip('-')
    cleaned = cleaned.upper()
    if len(cleaned) < minLen:
        cleaned = cleaned.ljust(minLen, fillerChar)
    if not cleaned[0].isalpha():
        cleaned = firstAlpha + cleaned[1:]

    return cleaned


def getDateTime(datetime_str):
    """
    # Synopsis:
    Extracts a datetime object from a string.

    # Params:
        # datetime_str: The string containing the datetime.
        Accepted formats: '19/09/2031 13:55' or '19/09/2031'

    # Return: None or a datetime object. Time may be set to 00:00 if not present.

    """


    rabat_tz = pytz.timezone("Africa/Casablanca")

    if len(datetime_str) == 16:
        naive_dt = datetime.strptime(datetime_str, '%d/%m/%Y %H:%M')
        rabat_dt = rabat_tz.localize(naive_dt)
        return rabat_dt
    if len(datetime_str) == 10:
        naive_dt = datetime.strptime(datetime_str, '%d/%m/%Y').date()
        return naive_dt
    return None


def getDriver(url=''):
    """
    # Synopsis:
        Opens a web browser page, goes to the portal website and submits search form.
    # Params:
        url: The address to retrieve before returning. 
    # Return:
        None or the opened browser page. That is an instance of webdriver.
    """

    printMessage('DEBUG', 'h.getDriver', 'Setting up options for Chromium browser ...\n')
    options = webdriver.ChromeOptions()
    printMessage('DEBUG', 'h.getDriver', f'\tSetting headless mode to {C.HEADLESS_MODE}')
    if C.HEADLESS_MODE:
        options.add_argument('--headless')
    options.timeouts = {'pageLoad': C.LOADING_TIMEOUT, 'implicit': 60000}
    options.add_argument("--window-size=1920,1080")
    printMessage('DEBUG', 'h.getDriver', 'Launching instance of Chromium browser ...\n')
    driver = webdriver.Chrome(options=options)
    if url == '' or url == None:
        printMessage('DEBUG', 'h.getDriver', 'Returning a driver with an empty url.\n')
        return driver
    printMessage('DEBUG', 'h.getDriver', f'Loading web address to driver: {url.replace(C.SITE_INDEX, "[held]")}')
    try:
        driver.get(url)
        printMessage('DEBUG', 'h.getDriver', 'Chromium driver instance is setup and ready.')
    except:
        printMessage('ERROR', 'h.getDriver', 'Could not load address to Chromium driver.')
        traceback.print_exc()
    return driver


def importLinks(file=f'{C.SELENO_DIR}/exports/links.csv'):
    """
    # Synopsis:
        Imports a list of links from csv file.
    # Params:
        file: The file containing the links. 
    # Return:
        Links: List of the links contained in the file.
    """
    printMessage('INFO', 'h.importLinks', f'Importing links from file {file.replace(C.SELENO_DIR, "")}\n')
    links = []
    try:
        with open(file, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                links.append(row)
    except:
        printMessage('ERROR', 'h.importLinks', f'Exception while importing links from file:\n')
        traceback.print_exc()
    printMessage('INFO', 'h.importLinks', f'Imported {len(links)} links from file.\n')
    
    return links


def printBanner():
    aski = """
 ##############################
 ##                          ##
 ##   777777  77777  77777   ##
 ##      77     77     77    ##
 ##     77     77     77     ##
 ##     77     77     77     ##
 ##                          ##
 ##############################
 ###  ©2025 - MODE-777.COM  ###
 ##############################
    """
    print(aski)


def getUa():
    rua = 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
    if len(C.USER_AGENTS) > 0 : rua = C.USER_AGENTS[random.randint(0, len(C.USER_AGENTS)-1)]
    return rua


def sleepRandom(Fm=35, To=65):
    rint = random.randint(Fm, To)
    printMessage('DEBUG', 'h.sleepRandom', f'zzzzzzzzzzzz Sleeping for a ({rint}s) while zzzzzzzzzzzz')
    time.sleep(1)
    time.sleep(rint)
    return 0


