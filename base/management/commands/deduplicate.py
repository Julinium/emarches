from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from base.models import Tender


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        duplicates = (
            Tender.objects.values('chrono')
            .annotate(
                chrono_count=Count('id'),
            )
            .filter(chrono_count__gt=1)
        )

        self.stdout.write(self.style.SUCCESS(f"Found {len(duplicates)} duplicates."))

        for entry in duplicates:
            chrono_val = entry['chrono']
            oldest_tender = (
                Tender.objects.filter(chrono=chrono_val)
                .order_by('created', 'id')
                .first()
            )

            if oldest_tender:
                self.stdout.write(f"\t{ chrono_val } oldest tender: {oldest_tender.id}")
                too_much_tenders = Tender.objects.filter(chrono=chrono_val).exclude(pk=oldest_tender.pk)
                self.stdout.write(f"\t{ chrono_val } trop plein to delete: { len(too_much_tenders) }")
                dr = too_much_tenders.delete()
                self.stdout.write(self.style.WARNING(f"Deleted: {dr}."))

        self.stdout.write(self.style.SUCCESS("Finished working."))