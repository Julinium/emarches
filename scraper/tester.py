import os
import sys
# import traceback

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

    from base.models import Tender
    st = Tender.objects.filter(chrono='1028243').first()
    if st:
        print(f"Tender found: {st.chrono} - {st.title}")
        st.delete()
    else:
        print("Tender not found.")

    pass

    
        


if __name__ == '__main__':
    main()

