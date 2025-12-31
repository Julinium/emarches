import os, sys, traceback
import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    from scraper import helper, getter, merger
    from base.models import Tender
    from scraper import constants as C
    from datetime import datetime
    

    def handle_results():

        results_saved, results_searched = 0, 0
        helper.printMessage('INFO', 'worker', f"▶▶▶▶▶ Started handling Tenders Results ◀◀◀◀◀", 2, 1)
        assa = datetime.now().date()

        tenders = Tender.objects.filter(
            deadline__date__lte=assa,
            openings__isnull=True, 
            ).order_by('published')
        count = tenders.count()

        helper.printMessage('INFO', 'worker', f"###Getting Results for { count } items ...", 3)
        i = 0
        for tender in tenders:
            i += 1
            if i % C.BURST_LENGTH == 0: helper.sleepRandom(30, 35)

            helper.printMessage('INFO', 'worker', f"Working on item { i }/{ count } = {tender.chrono}&{tender.acronym}",2)
            result = getter.getMinutes(tender.chrono, tender.acronym)
            if result and result != {}:
                helper.printMessage('INFO', 'worker', f"\tMinutes found for item { i }/{ count }")
                try:
                    if merger.mergeResults(result) == 0:
                        results_saved += 1
                        helper.printMessage('DEBUG', 'worker', f"\tSaved Minutes for item { i }/{ count }")
                except Exception as xc : 
                    helper.printMessage('ERROR', 'worker', f"\tError saving Minutes for item { i }/{ count }")
                    helper.printMessage('DEBUG', 'worker', f"Received object: \n{ result }\n")
                    helper.printMessage('DEBUG', 'worker', f"Raised Exception: \n{ xc }\n")
                    traceback.print_exc()
            else:
                helper.printMessage('INFO', 'worker', f"\tMinutes empty or not found for item { i }/{ count }")
        
        return results_saved, i


    handle_results()

    # from base.models import Concurrent
    # ghosts = Concurrent.objects.filter(deposits__isnull=True)
    # n = ghosts.count()
    # ghosts.delete()
    # print(f'================ Deleted {n} ghosts')

if __name__ == '__main__':
    main()
