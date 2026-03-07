from django.core.management.base import BaseCommand

# from base.models import Tender, Lot, Category


class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING(f"Started doing the work ..."))
        
        ############################################
        # from base.models import Client, make_acronym
        # clients = Client.objects.filter(
        #         # tenders__isnull=False,
        #         short__isnull=True,
        #     )

        # cc = clients.count()
        # print(f"Found {cc} clients to save.\n")
        # i = 0
        # for c in clients:
        #     # i += 1
        #     ns = make_acronym(c.name)
        #     if c.short != ns:
        #         i += 1
        #         print(f"Saving client {i:04} / {cc:04}:")
        #         print(f"\tOld Short: {c.short}")
        #         c.short = ns
        #         print(f"\tNew Short: {ns}")
        #         print(f"\tFull name: {c.name}\n")
        #         c.save()

        ############################################


        self.stdout.write(self.style.SUCCESS("Processing finished successfully."))
