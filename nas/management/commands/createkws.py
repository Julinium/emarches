# from django.core.management.base import BaseCommand
# from base.models import Tender

# class Command(BaseCommand):
#     help = "Insert basic Notification instances to database"

#     def handle(self, *args, **kwargs):
#         tenders = Tender.objects.all()
#         tl = tenders.count()
#         self.stdout.write(self.style.WARNING(f"Started updating { tl } tenders ..."))
#         i = 0
#         for t in tenders:
#             i += 1
#             print(f"\tUpdating item { i } from { tl } ...")
#             t.save()
        
#         self.stdout.write(self.style.SUCCESS("Data inserted successfully."))