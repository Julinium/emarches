from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserSettings
from .choices import ItemsPerPage

from django.contrib.auth.models import User
from nas.models import Folder, Profile, UserSettings
from nas.subbing import subscribeUserToNotifications, subscribeUserToNewsletters

@receiver(post_save, sender=User)
def createProfile(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance,)
        Profile.objects.create(user = instance,)
        subscribeUserToNotifications(instance)
        subscribeUserToNewsletters(instance)
        Folder.objects.create(user=u, name='eMarchés', color='#aa0088', comment='Default Tenders Folder')
        Folder.objects.create(user=u, name='MODE-777', comment='Tenders Folder')


# @receiver(post_save, sender=User)
# def save_user_settings(sender, instance, **kwargs):
#     if hasattr(instance, 'settings'):
#         instance.settings.save()