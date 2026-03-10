import logging
import hashlib

from django.dispatch import receiver
from allauth.account.signals import (
    user_signed_up,
    user_logged_in,
    user_logged_out,
    password_changed,
    password_set,
    email_confirmed,
    email_added,
    email_removed,
)
from allauth.socialaccount.signals import (
    social_account_added,
    social_account_removed,
    social_account_updated,
)

logger_portal = logging.getLogger("portal")


@receiver(user_signed_up)
def log_user_signup(request, user, **kwargs):
    logger_portal.info(
        "User signed up",
        extra={
            "request": request,
        },
    )

@receiver(user_logged_in)
def log_user_login(request, user, **kwargs):
    logger_portal.info(
        "User logged in",
        extra={
            "request": request,
        },
    )

@receiver(user_logged_out)
def log_user_logout(request, user, **kwargs):
    logger_portal.info(
        "User logged out",
        extra={
            "request": request,
        },
    )

@receiver(password_changed)
def log_password_change(request, user, **kwargs):
    logger_portal.warning(
        "Password changed",
        extra={
            "request": request,
        },
    )

@receiver(password_set)
def log_password_set(request, user, **kwargs):
    logger_portal.warning(
        "Password set",
        extra={
            "request": request,
        },
    )

@receiver(email_confirmed)
def log_email_confirmed(request, email_address, **kwargs):
    logger_portal.info(
        "Email confirmed",
        extra={
            "request": request,
            "email": mask_email(email_address.email),
        },
    )

@receiver(email_added)
def log_email_added(request, user, email_address, **kwargs):
    logger_portal.info(
        "Email added",
        extra={
            "request": request,
            "email": mask_email(email_address.email),
        },
    )

@receiver(email_removed)
def log_email_removed(request, user, email_address, **kwargs):
    logger_portal.warning(
        "Email removed",
        extra={
            "request": request,
            "email": mask_email(email_address.email),
        },
    )

@receiver(social_account_added)
def log_social_link(request, sociallogin, **kwargs):
    logger_portal.info(
        "Social account linked",
        extra={
            "request": request,
            "provider": sociallogin.account.provider,
        },
    )

@receiver(social_account_removed)
def log_social_removed(request, socialaccount, **kwargs):
    logger_portal.warning(
        "Social account removed",
        extra={
            "request": request,
            "provider": socialaccount.provider,
            "uid": socialaccount.uid,
        },
    )

@receiver(social_account_updated)
def log_social_updated(request, sociallogin, **kwargs):
    logger_portal.info(
        "Social account updated",
        extra={
            "request": request,
            "provider": sociallogin.account.provider,
            "uid": sociallogin.account.uid,
        },
    )


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email

    local, domain = email.split("@", 1)

    if len(local) > 0:
        masked_local = local[0] + "---" + local[-1]
    else:
        masked_local = "---"

    name, tld = domain.rsplit(".", 1)
    if len(name) > 0:
        masked_name = name[0] + "---" + name[-1]
    else:
        masked_name = "---"

    return f"{masked_local}@{masked_name}.{tld}"