from django.db.models.signals import post_save
from django.dispatch import receiver

# from django.utils.translation import gettext as _

from django.contrib.auth.models import User
from nas.models import Profile, Notification, NotificationSubscription



@receiver(post_save, sender=User)
def createProfile(sender, instance, created, **kwargs):
    if created:
        profile = Profile(
            user = instance,
        )
        try : profile.save()
        except Exception as xc : print('xxxxxxxxxxxxxxxxxxx Exception raised when creating Profile instance:', str(xc))



@receiver(post_save, sender=User)
def subscribeToNotifications(sender, instance, created, **kwargs):
    if created:
        notifs = Notification.objects.all()
        noti_subs = []
        for notif in notifs:
            noti_sub = NotificationSubscription(
                user = instance,
                notification = notif,
                active = notif.active,
                rank = notif.rank
            )
            noti_subs.append(noti_sub)

        try: NotificationSubscription.objects.bulk_create(noti_subs)
        except Exception as xc : print('xxxxxxxxxxxxxxxxxxx Exception raised when subscribing to Notifications:', str(xc))

