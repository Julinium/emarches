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
    
    # def get_results():
    #     print('\n\n\n\n======================================================')
    #     helper.printMessage('===', 'tester', f"▶▶▶▶▶ Now, let's get some Results ◀◀◀◀◀", 1, 1)
        
    #     assa = datetime.now().date()

    #     tenders = Tender.objects.filter(
    #         deadline__date__lte=assa, 
    #         # minutes__isnull=True, 
    #         ).order_by('-deadline')
    #     count = tenders.count()

    #     i = 0
    #     for tender in tenders:
    #         i += 1
    #         if i % 50 == 0:
    #             helper.sleepRandom(30, 35)
    #         print(f"\tWorking on item { i }/{ count } = {tender.chrono}&{tender.acronym}\n")
    #         result = getter.getMinutes(tender.chrono, tender.acronym)
    #         # print(f"Result = {result}\n\n")
    #         if result and result != {}:
    #             print(f"\tItem { i }/{ count } is positive \n")
    #             try: 
    #                 if merger.mergeResults(result) == 0:
    #                     print(f"\tItem { i }/{ count } succeeded \n")
    #             except Exception as xc : 
    #                 print(f"Result = {result}\n\n")
    #                 traceback.print_exc()
    #         else:
    #             print(f"\tItem { i }/{ count } is negative \n")
            
    #     print('\n\n======================================================\n\n')




    def handle_results_for_all():

        results_saved = 0
        helper.printMessage('INFO', 'worker', f"▶▶▶▶▶ Started handling Tenders Results ◀◀◀◀◀", 2, 1)
        assa = datetime.now().date()


        tenders = Tender.objects.filter(
            deadline__date__lte=assa,
            # minutes__isnull=True, 
            ).order_by('-deadline')
        count = tenders.count()

        i = 0
        for tender in tenders:
            i += 1
            if i % C.BURST_LENGTH == 0: helper.sleepRandom(30, 35)

            helper.printMessage('INFO', 'worker', f"Working on item { i }/{ count } = {tender.chrono}&{tender.acronym}")
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
        
        helper.printMessage('INFO', 'worker', f"Finished handling Results Minutes. Failures: { i - results_saved }")
        helper.printMessage('INFO', 'worker', f"\t Saved { results_saved } items over { i } handled.")
        return results_saved, i


    handle_results_for_all()


if __name__ == '__main__':
    main()
