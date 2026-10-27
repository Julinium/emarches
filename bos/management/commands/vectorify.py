from django.core.management.base import BaseCommand
from bos.helper import reindex

class Command(BaseCommand):
    help = "Reindex search vectors"

    def handle(self, *args, **options):
        reindex()

