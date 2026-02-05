from django.core.management.base import BaseCommand

# from base.models import Tender, Lot, Category


class Command(BaseCommand):
    help = "Insert basic Notification instances to database"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING(f"Started doing the work ..."))
        
        ############################################
        from bidding.models import Team
        # from datetime import datetime
        
        # mbs = TeamMember.objects.all()
        # for mb in mbs:
        #     mb.created = mb.joined
        #     mb.save()
        teams = Team.objects.all()
        for t in teams:
            if t.members.count() == 0:
                t.delete()

        ############################################


        self.stdout.write(self.style.SUCCESS("Processing finished successfully."))
