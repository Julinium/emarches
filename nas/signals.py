from django.db.models.signals import post_save
from django.dispatch import receiver

# from django.utils.translation import gettext as _

from django.contrib.auth.models import User
from nas.models import Profile, Notification, Newsletter, NotificationSubscription, NewsletterSubscription
from nas.subbing import subscribeUserToNotifications, subscribeUserToNewsletters


@receiver(post_save, sender=User)
def createProfile(sender, instance, created, **kwargs):
    if created:
        profile = Profile(
            user = instance,
        )
        try : profile.save()
        except Exception as xc : print('xxxxxxxxxxxxxxxxxxx Exception raised when creating Profile instance:', str(xc))


