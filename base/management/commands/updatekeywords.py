from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from base.models import Client, Lot, Tender


class Command(BaseCommand):
    help = "Updates"

    def handle(self, *args, **kwargs):

        from base.models import Change

        modifs = Change.objects.all()
        for modif in modifs:
            if ":00+00:00" in  modif.changes:
                xdc = modif.changes
                modif.changes = xdc.replace(":00+00:00", "")
                modif.save()

        # clients = Client.objects.filter(keywords=None)
        # cc = clients.count()
        # i = 0
        # for c in clients:
        #     i += 1
        #     print(f"\t===== Updating client { i } form { cc }")
        #     c.save()

        # tenders = Tender.objects.filter(keywords=None)
        # tt = tenders.count()
        # i = 0
        # for t in tenders:
        #     i += 1
        #     print(f"\t===== Updating tender { i } form { tt }")
        #     t.save()

        # lots = Lot.objects.all()
        # ll = lots.count()
        # i = 0
        # for l in lots:
        #     i += 1
        #     print(f"\t===== Updating lot { i } form { ll }")
        #     l.save()


        self.stdout.write(self.style.SUCCESS("Data updated successfully."))
