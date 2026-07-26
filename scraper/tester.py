import os
import sys
import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    # from scraper import constants as C
    # from scraper import downer
    # nodce = downer.getEmpties()
    # pass
    from base.models import Change
    change_objects = Change.objects.all()
    chn = len(change_objects)

    i = 0
    for chob in change_objects:
        i += 1
        print(f"Checking item {i}/{chn}...")
        tzc = "<DstTzInfo 'Africa/Casablanca' +01+1:00:00 STD>"
        tzu = "datetime.timezone.utc"
        if tzc in chob.changes:
            print(chob.changes)
            chob.changes = chob.changes.replace(tzc, tzu)
            chob.save()
            print(chob.changes)
    print("++++++++++Done+++++++++")
    # [{
    #     'field': 'estimate', 
    #     'old_value': Decimal('1044000.00'), 
    #     'new_value': Decimal('1530000.00')
    # }, 
    # {
    #     'field': 'deadline', 
    #     'old_value': datetime.datetime(2026, 7, 29, 9, 0, tzinfo=datetime.timezone.utc), 
    #     'new_value': datetime.datetime(2026, 8, 6, 9, 0, tzinfo=<DstTzInfo 'Africa/Casablanca' +01+1:00:00 STD>)
    # }]


if __name__ == '__main__':
    main()
