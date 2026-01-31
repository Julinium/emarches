from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from nas.models import Newsletter

# from datetime import date, timedelta


class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        
        newsleters_data = [
            Newsletter(
                rank        = 101,
                name        = _("Weekly Digest"),
                monthly     = 4,
                description = _("Get a digest of the week.")
            ),

            Newsletter(
                rank        = 102,
                name        = _("Monthly Digest"),
                monthly     = 1,
                description = _("Get a digest of the month.")
            ),

            Newsletter(
                rank        = 103,
                name        = _("Monthly Updates"),
                monthly     = 1,
                description = _("Get the greatest updates of the month.")
            ),

            Newsletter(
                rank        = 201,
                name        = _("Commercial Offers"),
                monthly     = 1,
                description = _("Get notified about our commercial offers and new products.")
            ),

            Newsletter(
                rank        = 202,
                name        = _("Partners' Offers"),
                monthly     = 1,
                description = _("Get commercial offers from our partners.")
            ),

            Newsletter(
                rank        = 301,
                name        = _("Polls and reviews"),
                monthly     = 1,
                description = _("Get invitations to participate in our polls and reviews.")
            ),
            
        ]

        Newsletter.objects.bulk_create(newsleters_data)

        self.stdout.write(self.style.SUCCESS("Data inserted successfully."))
