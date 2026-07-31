import os
import sys
import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():

    # import ast
    # import datetime
    # from decimal import Decimal
    # from zoneinfo import ZoneInfo

    # from base.models import Change
    # records = Change.objects.all()

    # i = 0
    # for rec in records:
    #     tzc = 'tzinfo=ZoneInfo("Africa/Casablanca")'
    #     i += 1
    #     bs = '["level", "field", "old_value", "new_value"]'
    #     if tzc in rec.changes:
    #         print(f"{i} = {rec.changes}", '\n------\n')
    #         data = eval(rec.changes, {"datetime": datetime, "ZoneInfo": ZoneInfo, "Decimal": Decimal})

    #         rec.changes = convert_datetimes_to_iso(data)
    #         rec.save()
    #         print(f"==== {rec.changes}", '------\n')
    pass

    
        


if __name__ == '__main__':
    main()

