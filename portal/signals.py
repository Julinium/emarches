from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

# from .models import UserSettings
# from .choices import ItemsPerPage

# from django.contrib.auth.models import User
# from nas.models import Folder, Profile, UserSettings
# from nas.subbing import subscribeUserToNotifications, subscribeUserToNewsletters
from base.models import Meeting, Sample, Visit, RelAgrementLot, RelQualifLot


@receiver(post_save, sender=RelAgrementLot)
def updateTender_saveRelAgrementLot(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_delete, sender=RelAgrementLot)
def updateTender_deleteRelAgrementLot(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_save, sender=RelQualifLot)
def updateTender_saveRelQualifLot(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_delete, sender=RelQualifLot)
def updateTender_deleteRelQualifLot(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_save, sender=Meeting)
def updateTender_saveMeeting(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_save, sender=Sample)
def updateTender_saveSample(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_save, sender=Visit)
def updateTender_saveVisit(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_delete, sender=Meeting)
def updateTender_deleteMeeting(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_delete, sender=Sample)
def updateTender_deleteSample(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

@receiver(post_delete, sender=Visit)
def updateTender_deleteVisit(sender, instance, created, **kwargs):
    lot = instance.lot
    lot.save()

