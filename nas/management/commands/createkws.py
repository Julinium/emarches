from django.core.management.base import BaseCommand
# from base.models import Tender, Lot, Category


class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING(f"Started doing the work ..."))
        
        ############################################
        from bdc.models import PurchaseOrder
        from datetime import datetime, timedelta

        assa = datetime.now() - timedelta(days=5)
        pos = PurchaseOrder.objects.all().order_by('-deadline')

        pc = pos.count()

        print(f"Found items: { pc }")
        i = 0
        for po in pos:
            i += 1
            p = 100 * i / pc
            print(f"{ round(p, 2) }% \tWorink on item { i } / { pc } ...")
            po.save()

        ############################################


        self.stdout.write(self.style.SUCCESS("Processing finished successfully."))
