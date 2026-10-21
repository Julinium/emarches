import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db.models import Count, F, Sum

from base.models import Tender


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        self.stdout.write("Started working.")

        def _amount(value):
            """Preserve monetary precision in JSON."""
            return str(value if value is not None else Decimal("0"))

        def _top_related(queryset, relation, name_field="name", limit=3):
            return list(
                queryset.values(
                    related_id=F(f"{relation}__id"),
                    related_name=F(f"{relation}__{name_field}"),
                ).annotate(
                    tender_count=Count("pk", distinct=True),
                    amount_sum=Sum("estimate"),
                ).order_by("-tender_count", "-amount_sum")[:limit]
            )


        def generate_procurement_digest():
            """
            Return a JSON-serializable procurement digest for running tenders.
            """
            print
            today = timezone.localdate()

            # Assumes deadline is a DateField and a tender remains running
            # through its deadline date. See the note below for DateTimeField.
            running = Tender.objects.filter(deadline__gte=today)

            totals = running.aggregate(
                tender_count=Count("pk"),
                amount_sum=Sum("estimate"),
            )

            categories = _top_related(running, "category", "label")
            clients = _top_related(running, "client")

            # A tender can belong to multiple domains. Aggregate separately by
            # domain so each domain receives the amounts of its associated tenders.
            domains = _top_related(running, "domains")

            # Split the text field into individual cities and aggregate in Python.
            city_stats = defaultdict(lambda: {
                "tender_count": 0,
                "amount_sum": Decimal("0"),
            })

            for location, estimate in running.values_list(
                "location", "estimate"
            ).iterator():
                cities = {
                    city.strip()
                    for city in (location or "").split(",")
                    if city.strip()
                }

                for city in cities:
                    city_stats[city]["tender_count"] += 1
                    city_stats[city]["amount_sum"] += estimate or Decimal("0")

            locations = [
                {
                    "name": city,
                    "tender_count": stats["tender_count"],
                    "amount_sum": _amount(stats["amount_sum"]),
                }
                for city, stats in sorted(
                    city_stats.items(),
                    key=lambda item: (
                        -item[1]["tender_count"],
                        -item[1]["amount_sum"],
                        item[0].casefold(),
                    ),
                )[:3]
            ]

            # Top three individual tenders by estimated amount.
            top_amounts = [
                {
                    "id": str(tender.pk),
                    "amount": _amount(tender.estimate),
                }
                for tender in running.order_by(
                    "-estimate", "pk"
                )[:3]
            ]

            def normalize_groups(groups):
                return [
                    {
                        "id": str(group["related_id"]),
                        "name": group["related_name"],
                        "tender_count": group["tender_count"],
                        "amount_sum": _amount(group["amount_sum"]),
                    }
                    for group in groups
                ]

            return {
                "generated_at": timezone.now().isoformat(),
                "running_tenders": {
                    "count": totals["tender_count"],
                    "amount_sum": _amount(totals["amount_sum"]),
                },
                "top_categories": normalize_groups(categories),
                "top_clients": normalize_groups(clients),
                "top_locations": locations,
                "top_domains": normalize_groups(domains),
                "top_amounts": top_amounts,
            }


        def write_procurement_digest(path="summaries"):
            """Generate the digest and write it to a JSON file."""
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)

            digest = generate_procurement_digest()
            temporary_path = path.with_suffix(path.suffix + ".tmp")

            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(digest, file, ensure_ascii=False, indent=2)
                file.write("\n")

            # Atomic replacement prevents readers from seeing a partially
            # written digest.
            temporary_path.replace(path)

            return digest

        write_procurement_digest()

        self.stdout.write(self.style.SUCCESS("Finished working."))