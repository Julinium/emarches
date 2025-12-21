import os, sys
import django

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emarches.settings')
django.setup()

def main():
    from scraper import helper, getter
    from base.models import Tender
    
    def get_results():
        print('\n\n\n\n======================================================')
        helper.printMessage('===', 'tester', f"▶▶▶▶▶ Now, let's get some Results ◀◀◀◀◀", 1, 1)
        
        tenders = Tender.objects.all().order_by('deadline')
        # tenders = Tender.objects.filter(chrono='929722').order_by('deadline')
        count = tenders.count()

        i = 0
        for tender in tenders:
            i += 1
            print(f"\tWorking on item { i }/{ count } = {tender.chrono}&{tender.acronym}\n")
            result = getter.getMinutes(tender.chrono, tender.acronym)
            print(f"Result = {result}\n\n")
            if i % 10 == 0:
                print("\n\n")
                helper.sleepRandom()
                print("\n\n")


        print('\n\n======================================================\n\n')
    
    get_results()


if __name__ == '__main__':
    main()
