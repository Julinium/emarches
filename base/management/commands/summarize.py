from django.core.management.base import BaseCommand
from django.db.models import Count, Min
from base.models import Tender


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        

        self.stdout.write(self.style.SUCCESS("Finished working."))