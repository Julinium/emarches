import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

SELENO_DIR = str(Path(__file__).resolve().parent)
env_path = f'{ SELENO_DIR }/.env'
load_dotenv(dotenv_path=env_path)

# Tell whether script is running on local server or in a remote machine.
MACHINE = os.getenv("MACHINE", 'local')
REMOTE_USER = os.getenv("REMOTE_USER", 'emarches')
SSH_PORT = os.getenv("SSH_PORT", 22)

MEDIA_ROOT = os.getenv("MEDIA_ROOT")
DL_PATH_PREFIX = os.getenv("DL_PATH_PREFIX")

VERBOSITY = 1
BURST_LENGTH = 25

LOGS_LEVELS = {"TRACE" : 1, "DEBUG" : 2, "INFO"  : 3, "WARN"  : 4, "ERROR" : 5, "FATAL" : 6,}

IMPORT_LINKS = False
REFRESH_EXISTING = True
SKIP_DCE = False

parser = argparse.ArgumentParser()
parser.add_argument('--level', type=str, required=False, help='debug for more verbose output.')
parser.add_argument('--links', type=str, required=False, help='import to use already saved links.')
parser.add_argument('--found', type=str, required=False, help='refresh to refresh existing items.')
parser.add_argument('--dce', type=str, required=False, help='DCE files download.')

args = parser.parse_args()
if args.level: 
    level = args.level.upper()
    if level in LOGS_LEVELS:
        VERBOSITY = LOGS_LEVELS[level]

if args.links: IMPORT_LINKS = args.links.lower() == "import"
if args.found: REFRESH_EXISTING = args.found.lower() == "refresh"
if args.dce: SKIP_DCE = args.dce.lower() != "download"

HEADLESS_MODE = True

SITE_ROOT = os.getenv("SITE_ROOT")
SITE_INDEX = os.getenv("SITE_INDEX")
LINK_PREFIX = os.getenv("LINK_PREFIX")
LINK_STITCH = os.getenv("LINK_STITCH")

BDC_RESULTS_BASE_URL = os.getenv("BDC_RESULTS_BASE_URL")
BDC_LISTING_BASE_URL = os.getenv("BDC_LISTING_BASE_URL")
BDC_DETAILS_HOST = os.getenv("BDC_DETAILS_HOST")


DB_SERVER = os.getenv("DB_SERVER")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

MEDIA_ROOT = os.getenv("MEDIA_ROOT")
FILE_PREFIX   = 'eMarches.com' # Prefix before DCE files names
# When a 4XX error is returned sleep a random time between SLEEP_4XX_MIN and SLEEP_4XX_MAX seconds
SLEEP_4XX_MIN = 377
SLEEP_4XX_MAX = 777

# Read User Agents list from file
ua_json = f'{ SELENO_DIR }/.env.ua.json'
with open(ua_json) as f:
    USER_AGENTS = json.load(f)

# Read credentials list from file
creds_json = f'{ SELENO_DIR }/.env.creds.json'
with open(creds_json) as g:
    DCE_CREDS = json.load(g)

# Items per page on browser. Higher means less pages to handle by Chromium, and then less time
LINES_PER_PAGE = "500" 
# Look for Tenders with Deadline up to PORTAL_DDL_PAST_DAYS days in the past.
PORTAL_DDL_PAST_DAYS = 365 * 1 
# Download Tenders DCE with Deadline up to PORTAL_DCE_PAST_DAYS days in the past.
PORTAL_DCE_PAST_DAYS = 365 * 1 
# Look for Tenders with Deadline up to PORTAL_DDL_FUTURE_DAYS days in the future.
PORTAL_DDL_FUTURE_DAYS = 365 * 1 
# Look for Tenders published up to PORTAL_PUB_PAST_DAYS days in the past.
PORTAL_PUB_PAST_DAYS = 365 * 1 
# Do not come from the future
PORTAL_PUB_FUTURE_DAYS = 0
# If a page does not load in LOADING_TIMEOUT, look at something else
LOADING_TIMEOUT = 1000 * 91
REQ_TIMEOUT = 60
DLD_TIMEOUT = 60

LOG_TIME_FORMAT = '%d/%m-%H:%M:%S'

NA_PLH = ''
TRUNCA = 32

DCE_CLEANING_DAY = 7        # 1 to 28 (just to be sure)
CLEAN_DCE_AFTER_DAYS = 365 * 1
CLEAN_CONS_AFTER_DAYS = 365 * 25
