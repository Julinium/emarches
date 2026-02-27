import logging
import os

from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.http import HttpResponse

logger_portal = logging.getLogger("portal")


def home(request):
    logger_portal.info(f"Home page view", extra={"request": request})
    return render(request, 'base/home.html')


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def view_log_file(request, logger='portal'):

    if not logger:
        logger_portal.warning("E404: Null log type parameter", extra={"request": request})
        return HttpResponse(_("Not found"), status=404)

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenicated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    if not user.is_superuser:
        logger_portal.warning("E403: User not a superuser", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    log_file = os.path.join(settings.BASE_DIR, f"logs/{ logger }.log")
    if not os.path.exists(log_file):
        logger_portal.warning("E404: Logger not found", extra={"request": request})
        return HttpResponse(_("File not found"), status=404)
    
    with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    logger_portal.info(f"Log file view: { logger }.log", extra={"request": request})

    context = {
        "logger": logger, 
        "content": content,
        }
    
    return render(request, "base/log.html", context)

