# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from django.utils.translation import gettext as _

from django.contrib.auth.models import User

from nas.models import (Newsletter, NewsletterSubscription, Notification,
                        NotificationSubscription, Profile)


def subscribeUserToNotifications(user):
    notifs = Notification.objects.all()
    noti_subs = []
    for notif in notifs:
        if not NotificationSubscription.objects.filter(user=user, notification=notif):
            noti_sub = NotificationSubscription(user=user, notification=notif, active=notif.active, rank=notif.rank)
            noti_subs.append(noti_sub)

    try: NotificationSubscription.objects.bulk_create(noti_subs)
    except Exception as xc : print('xxxxxxxxxxxxxxxxxxx Exception raised when subscribing to Notifications:', str(xc))


def subscribeUserToNewsletters(user):
    newls = Newsletter.objects.all()
    newls_subs = []
    for newl in newls:
        if not NewsletterSubscription.objects.filter(user=user, newsletter=newl):
            noti_sub = NewsletterSubscription(user = user, newsletter = newl, active = newl.active, rank = newl.rank)
            newls_subs.append(noti_sub)

    try: NewsletterSubscription.objects.bulk_create(newls_subs)
    except Exception as xc : print('xxxxxxxxxxxxxxxxxxx Exception raised when subscribing to Newsletters:', str(xc))

