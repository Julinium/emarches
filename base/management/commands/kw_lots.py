from django.core.management.base import BaseCommand
# from django.utils.translation import gettext as _


class Command(BaseCommand):
    help = "Updates"

    def handle(self, *args, **kwargs):
        import sys
        from django.db import transaction
        from datetime import datetime
        from base.models import Client, Lot, Tender
        
        lots = Lot.objects.filter(tender__deadline__gte=datetime.now()).order_by("-tender__deadline")
        tt = lots.count()

        self.stdout.write(f"Started processing { tt } items ...")

        with transaction.atomic():
            for index, obj in enumerate(
                lots.iterator(chunk_size=1000), start=1
            ):
                obj.save()
                sys.stdout.write(f"\rHandling item {index}/{tt}")
                sys.stdout.flush()

        self.stdout.write(self.style.SUCCESS("Data updated successfully."))
