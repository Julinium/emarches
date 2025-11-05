from django.core.management.base import BaseCommand
from base.models import Tender

class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        tenders = Tender.objects.all()
        tl = tenders.count()
        self.stdout.write(self.style.WARNING(f"Started updating { tl } tenders ..."))
        i = 0
        for t in tenders:
            i += 1
            print(f"\tUpdating item { i } from { tl } ...")
            t.save()
        # from base.models import Lot
        # lots = Lot.objects.filter(category=None)
        # lc = lots.count()
        # i = 0
        # for l in lots:
        #     i += 1
        #     print(f"\tUpdating {i} / {lc} ...")
        #     l.category = l.tender.category
        #     l.save()
        
        self.stdout.write(self.style.SUCCESS("Data inserted successfully."))