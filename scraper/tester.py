import os
import sys
# import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    from base.models import Tender
    t = Tender.objects.filter(chrono=1033775).first()
    if t:
        print(f"Found Tender. Value: {t.has_samples}")
        t.save()
        print(f"Saved Tender. Value: {t.has_samples}")
    # from downer import getFileables
    # ft = getFileables(past_days=90)
    # print(f"Found {len(ft)} Tenders with no DCE and deadline older than 90 days.")
    pass


if __name__ == '__main__':
    main()

