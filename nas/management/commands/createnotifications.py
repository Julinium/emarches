from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
# from datetime import date, timedelta

from nas.models import Notification

class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        
        notifications_data = [
            Notification(
                rank        = 101,
                name        = _("Favourite Tender change"),
                event       = _("Favourite Tender details changed"),
                description = _("Get notified when a Favourite Tender was changed")
            ),

            Notification(
                rank        = 102,
                name        = _("10 Days Favourite Deadline"),
                event       = _("Deadline of a Favourite Tender is in 10 days"),
                description = _("Get notified when the Deadline of a Favourite Tender is 10 days away")
            ),

            Notification(
                rank        = 103,
                name        = _("3 Days Favourite Deadline"),
                event       = _("Deadline of a Favourite Tender is in 3 days"),
                description = _("Get notified when the Deadline of a Favourite Tender is 10 days away")
            ),

            Notification(
                rank        = 111,
                name        = _("10 Days Favourite Meeting"),
                event       = _("Meeting of a Favourite Tender is in 10 days"),
                description = _("Get notified when the Meeting of a Favourite Tender is 10 days away")
            ),

            Notification(
                rank        = 112,
                name        = _("3 Days Favourite Meeting"),
                event       = _("Meeting of a Favourite Tender is in 3 days"),
                description = _("Get notified when the Meeting of a Favourite Tender is 3 days away")
            ),

            Notification(
                rank        = 113,
                name        = _("10 Days Favourite Samples"),
                event       = _("Samples of a Favourite Tender is in 10 days"),
                description = _("Get notified when the Samples of a Favourite Tender is 10 days away")
            ),

            Notification(
                rank        = 114,
                name        = _("3 Days Favourite Samples"),
                event       = _("Samples of a Favourite Tender is in 3 days"),
                description = _("Get notified when the Samples of a Favourite Tender is 3 days away")
            ),

            Notification(
                rank        = 115,
                name        = _("10 Days Favourite Visit"),
                event       = _("In-site Visit of a Favourite Tender is in 10 days"),
                description = _("Get notified when the In-site Visit of a Favourite Tender is 10 days away")
            ),

            Notification(
                rank        = 116,
                name        = _("3 Days Favourite Visit"),
                event       = _("In-site Visit of a Favourite Tender is in 3 days"),
                description = _("Get notified when the In-site Visit of a Favourite Tender is 3 days away")
            ),
            Notification(
                rank        = 201,
                name        = _("New Tender"),
                event       = _("Tender created"),
                description = _("Get notified when a new Tender is found")
            ),

            Notification(
                rank        = 202,
                name        = _("Tender change"),
                event       = _("Tender details changed"),
                description = _("Get notified when an existing Tender was changed")
            ),
            
        ]

        Notification.objects.bulk_create(notifications_data)

        self.stdout.write(self.style.SUCCESS("Data inserted successfully."))
