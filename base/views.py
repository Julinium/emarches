import logging
import os

from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control
from django.http import HttpResponse

from django.contrib.sitemaps.views import index as sitemap_index_view
from django.contrib.sitemaps.views import sitemap as sitemap_view


logger_portal = logging.getLogger("portal")


def home(request):
    logger_portal.info(f"Home page view", extra={"request": request})
    return render(request, 'base/home.html')


def about(request):
    logger_portal.info(f"About page view", extra={"request": request})
    return render(request, 'base/about.html')


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
    

def robots_txt(request):
    lines = [
        "User-Agent: *",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /user/",
        # "Disallow: /tenders/",
        # "Disallow: /porders/",
        # "Disallow: /bidders/",
        "Disallow: /bidding/",
        "Sitemap: https://new.emarches.com/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def clean_sitemap_index(request, sitemaps):
    response = sitemap_index_view(request, sitemaps=sitemaps)
    # Strip the header if Django or an app attached it
    response.headers.pop('X-Robots-Tag', None)
    response.headers.pop('x-robots-tag', None)
    return response


def clean_sitemap(request, sitemaps, section=None):
    response = sitemap_view(request, sitemaps=sitemaps, section=section)
    # Strip the header if Django or an app attached it
    response.headers.pop('X-Robots-Tag', None)
    response.headers.pop('x-robots-tag', None)
    return response