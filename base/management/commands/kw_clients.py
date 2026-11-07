from django.core.management.base import BaseCommand
# from django.utils.translation import gettext as _


class Command(BaseCommand):
    help = "Updates"

    def handle(self, *args, **kwargs):
        import sys
        from django.db import transaction
        from datetime import datetime
        from base.models import Client, Lot, Tender
        
        clients = Client.objects.all()
        tt = clients.count()

        self.stdout.write(f"Started processing { tt } items ...")

        with transaction.atomic():
            for index, obj in enumerate(
                clients.iterator(chunk_size=1000), start=1
            ):
                obj.save()
                sys.stdout.write(f"\rHandling item {index}/{tt}")
                sys.stdout.flush()

        self.stdout.write(self.style.SUCCESS("Data updated successfully."))
