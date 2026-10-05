from django.core.management.base import BaseCommand
from base.models import Link, Tender


class Command(BaseCommand):
    help = "Bulk links unlinked Link objects to their matching Tender by chrono."

    def handle(self, *args, **kwargs):
        # 1. Fetch unlinked links
        links = Link.objects.filter(tender__isnull=True).only("id", "chrono", "tender")
        total_links = links.count()

        if total_links == 0:
            self.stdout.write(self.style.SUCCESS("No unlinked links found."))
            return

        self.stdout.write(self.style.SUCCESS(f"Started handling {total_links} links."))

        # 2. Fetch matching Tenders in a single query and build a lookup map {chrono: tender_id}
        chronos = set(links.values_list("chrono", flat=True))
        
        # If chrono can have duplicates in Tender, dict comprehension keeps the last matching Tender
        tender_map = dict(
            Tender.objects.filter(chrono__in=chronos).values_list("chrono", "id")
        )

        # 3. Associate tenders to links in memory
        links_to_update = []
        for link in links:
            tender_id = tender_map.get(link.chrono)
            if tender_id:
                link.tender_id = tender_id  # Assign direct foreign key ID
                links_to_update.append(link)

        # 4. Perform bulk update
        if links_to_update:
            updated_count = Link.objects.bulk_update(
                links_to_update, fields=["tender"], batch_size=1000
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated {updated_count}/{total_links} links."
                )
            )
        else:
            self.stdout.write(self.style.WARNING("No matching Tenders were found."))

        self.stdout.write(self.style.SUCCESS("Finished working."))