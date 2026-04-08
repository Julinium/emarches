from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

# from base.models import Client, Lot, Tender


class Command(BaseCommand):
    help = "Update Plans data using `features.json` file"

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.NOTICE("eMarchés Plans updater"))
        # TODO: Make sure features.json exists, is readable and not empty.
        # TODO: Make sure Plans found in json exist on DB.
        # 

        # TODO: Update Currencies as well

        # with open("features.json") as f:
        #     data = json.load(f)
        # for cate in data:
        #     for capa in cate:
        #         Feature.objects.update_or_create(

        #             code=feat["code"],
        #             defaults={
        #                 "name": _(feat["name"]),
        #                 "description": _(feat["description"]),
        #             }
        #         )

        self.stdout.write(self.style.SUCCESS("Data updated successfully."))
