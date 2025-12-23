import os, sys, traceback
import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    from scraper import helper, getter, merger
    from base.models import Tender
    from datetime import datetime
    
    def get_results():
        print('\n\n\n\n======================================================')
        helper.printMessage('===', 'tester', f"▶▶▶▶▶ Now, let's get some Results ◀◀◀◀◀", 1, 1)
        
        assa = datetime.now().date()

        tenders = Tender.objects.filter(
            deadline__date__lte=assa,
            minutes__isnull=True,
            ).order_by('published')
        # tenders = Tender.objects.filter(lots_count__gte=5).order_by('deadline')
        count = tenders.count()

        i = 0
        for tender in tenders:
            i += 1
            if i % 25 == 0:
                print("\n\n")
                helper.sleepRandom(30, 35)
                print("\n\n")
            # print(f"\tWorking on item { i }/{ count } = {tender.chrono}&{tender.acronym}\n")
            result = getter.getMinutes(tender.chrono, tender.acronym)
            # print(f"Result = {result}\n\n")
            if result and result != {}:
                print(f"\tItem { i }/{ count } is positive \n")
                try: 
                    if merger.mergeResults(result) == 0:
                        print(f"\tItem { i }/{ count } succeeded \n")
                except Exception as xc : 
                    print(f"Result = {result}\n\n")
                    traceback.print_exc()
            else:
                print(f"\tItem { i }/{ count } is negative \n")

            


        print('\n\n======================================================\n\n')
    
    get_results()


if __name__ == '__main__':
    main()
