from django.core.management.base import BaseCommand
# from base.models import Tender, Lot, Category


class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING(f"Started doing the work ..."))


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
        # mt = 0
        # tenders = Tender.objects.prefetch_related('lots').filter(lots_count__gt=1)
        # for tender in tenders:
        #     if tender.lots.count() != tender.lots_count:
        #         try: 
        #             tender.delete()
        #             mt += 1
        #             self.stdout.write(self.style.WARNING(f"\t Deleted {tender.chrono}: Declared={tender.lots_count}, \tfound={tender.lots.count()}"))
        #         except Exception as xc: print(str(xc))

        # self.stdout.write(self.style.ERROR(f"Total Deleted mismatches: {mt}"))
        ###################################


        ###################################
        from base.models import FileToGet

        from django.db import transaction
        from django.db.models import Min

        @transaction.atomic
        def remove_duplicates_keep_any_one():
            Model = FileToGet  # Replace with your actual model
            fk_field = 'tender'  # e.g. 'user', 'product', 'category', etc.

            seen = set()  # Tracks FK values we've already kept a record for
            to_delete = []  # Collects IDs of duplicates to delete

            # Order by FK for efficient grouping (then by ID for consistency)
            queryset = Model.objects.order_by(fk_field, 'id').iterator(chunk_size=1000)

            i = 0
            for obj in queryset:
                i += 1
                print('\t Working on instance ', i)
                # Get the FK value (use _id suffix if it's an FK to avoid loading related object)
                key = getattr(obj, f'{fk_field}_id', getattr(obj, fk_field, None))
                if key is None:
                    continue  # Skip null FKs if they shouldn't be duplicated anyway

                key_str = str(key)  # Ensure it's hashable (UUIDs are, but safe)
                if key_str in seen:
                    to_delete.append(obj.id)
                    print('\t\t To delete ', i)
                else:
                    seen.add(key_str)
                    print('\t\t Newly seen ', i)

            # Bulk delete in one go
            if to_delete:
                deleted_count = Model.objects.filter(id__in=to_delete).delete()[0]
                print(f"Deleted {deleted_count} duplicate records")
            else:
                print("No duplicates found")
        remove_duplicates_keep_any_one()
        ###################################

        


        self.stdout.write(self.style.SUCCESS("Processing finished successfully."))
