from django.core.management.base import BaseCommand
from base.models import Tender

class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        # tenders = Tender.objects.all()
        # tl = tenders.count()
        # self.stdout.write(self.style.WARNING(f"Started updating { tl } tenders ..."))
        # i = 0
        # for t in tenders:
        #     i += 1
        #     print(f"\tUpdating item { i } from { tl } ...")
        #     t.save()
        # tenders = Tender.objects.filter(id='890ede0f-8141-49cb-bc99-9e5ffe53ea3c')
        from base.models import Lot
        from django.db.models import Count
        lots = Lot.objects.annotate(
            qualifs__count=Count('qualifs')).filter(
            tender__has_qualifs=False,
            qualifs__count__gt=0
            )
        lc = lots.count()
        i = 0
        for l in lots:
            i += 1
            print(f"\tUpdating {i} / {lc} ...")
            l.save()
    
        self.stdout.write(self.style.SUCCESS("Data updated successfully."))