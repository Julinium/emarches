from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserSettings
from .choices import ItemsPerPage

from django.contrib.auth.models import User
from nas.models import Profile, UserSettings
from nas.subbing import subscribeUserToNotifications, subscribeUserToNewsletters

@receiver(post_save, sender=User)
def createProfile(sender, instance, created, **kwargs):
    if created:
        UserSettings.objects.create(user=instance,)
        Profile.objects.create(user = instance,)
        subscribeUserToNotifications(instance)
        subscribeUserToNewsletters(instance)


# @receiver(post_save, sender=User)
# def save_user_settings(sender, instance, **kwargs):
#     if hasattr(instance, 'settings'):
#         instance.settings.save()