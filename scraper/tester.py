import os
import sys
import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    # from datetime import datetime

    # from base.models import Tender
    # from scraper import constants as C
    # from scraper import downer
    # print("------------", "")
    # nodce = downer.getEmpties()
    # print(nodce.count)
    pass


if __name__ == '__main__':
    main()
