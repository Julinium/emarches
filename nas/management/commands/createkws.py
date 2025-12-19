from django.core.management.base import BaseCommand
# from base.models import Tender, Lot, Category


class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING(f"Started doing the work ..."))
        
        ############################################
        from bdc.models import PurchaseOrder
        from datetime import datetime, timedelta
        from django.db.models import Count 

        assa = datetime.now() - timedelta(days=5)
        pos = PurchaseOrder.objects.annotate(item_count=Count('articles')).filter(item_count__gt=0).order_by('-deadline')

        pc = pos.count()

        print(f"Found POs: { pc }")
        i = 0
        for po in pos:
            i += 1
            p = 100 * i / pc
            if po.articles.count() > 0:                
                print(f"{ round(p, 2) }% \tWorink on PO { i } / { pc }: { po.articles.count() } items ...")
                po.save()
            else:
                print(f"{ round(p, 2) }% \tSkipping PO { i } / { pc }: No items ...")

        ############################################


        self.stdout.write(self.style.SUCCESS("Processing finished successfully."))
