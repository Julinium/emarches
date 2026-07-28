import os
import sys
import traceback

import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():

    import ast
    import datetime
    from decimal import Decimal
    from zoneinfo import ZoneInfo
    # from datetime import date, timezone

    def convert_datetimes_to_iso(obj):
        """
        Recursively walks through dicts, lists, or tuples and converts 
        any datetime or date instance to an ISO 8601 string in UTC.
        """
        # 1. Check for datetime/date instances first
        if isinstance(obj, datetime.datetime):
            # Convert to UTC to ensure the 'Z' suffix is accurate
            utc_dt = obj.astimezone(datetime.timezone.utc) if obj.tzinfo else obj
            return utc_dt.strftime('%Y-%m-%dT%H:%MZ')
        
        elif isinstance(obj, datetime.date): # handles date objects without time component
            return obj.isoformat()

        # 2. Recursively handle collections
        elif isinstance(obj, dict):
            return {k: convert_datetimes_to_iso(v) for k, v in obj.items()}
        
        elif isinstance(obj, list):
            return [convert_datetimes_to_iso(item) for item in obj]
        
        elif isinstance(obj, tuple):
            return tuple(convert_datetimes_to_iso(item) for item in obj)

        # 3. Leave all other data types (strings, ints, None) unchanged
        return obj


    from base.models import Change
    records = Change.objects.all()


    i = 0
    for rec in records:
        tzc = 'tzinfo=ZoneInfo("Africa/Casablanca")'
        i += 1
        bs = '["level", "field", "old_value", "new_value"]'
        if tzc in rec.changes:
            print(f"{i} = {rec.changes}", '\n------\n')
            data = eval(rec.changes, {"datetime": datetime, "ZoneInfo": ZoneInfo, "Decimal": Decimal})

            # Now run the conversion function on the parsed object
            rec.changes = convert_datetimes_to_iso(data)
            # rec.changes = convert_datetimes_to_iso(rec.changes)
            rec.save()
            print(f"==== {rec.changes}", '------\n')

    # tsc = 'tzinfo=<DstTzInfo "Africa/Casablanca" +01+1:00:00 STD>'
    # tzc = 'tzinfo=ZoneInfo("Africa/Casablanca")'
    # i = 0 
    # for rec in records:
    #     i += 1
    #     if tsc in rec.changes:
    #         rec.changes = rec.changes.replace(tsc, tzc)
    #         rec.save()
    #         print(f"{i} = {rec.changes}")

    
        


if __name__ == '__main__':
    main()
