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

        # from base.models import Lot
        # from django.db.models import Count
        # lots = Lot.objects.annotate(
        #     qualifs__count=Count('qualifs')).filter(
        #     tender__has_qualifs=False,
        #     qualifs__count__gt=0
        #     )
        # lc = lots.count()
        # i = 0
        # for l in lots:
        #     i += 1
        #     print(f"\tUpdating {i} / {lc} ...")
        #     l.tender.save()

        #################################
        mt = 0
        tenders = Tender.objects.prefetch_related('lots').filter(lots_count__gt=1)
        for tender in tenders:
            if tender.lots.count() != tender.lots_count:
                try: 
                    tender.delete()
                    mt += 1
                    self.stdout.write(self.style.WARNING(f"\t Deleted {tender.chrono}: Declared={tender.lots_count}, \tfound={tender.lots.count()}"))
                except Exception as xc: print(str(xc))

        self.stdout.write(self.style.ERROR(f"Total Deleted mismatches: {mt}"))
        ###################################


        self.stdout.write(self.style.SUCCESS("Processing finished successfully."))
