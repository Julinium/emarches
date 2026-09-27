from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse

from django.views.decorators.cache import cache_page
from django.contrib.sitemaps.views import index, sitemap

from base.views import clean_sitemap_index, clean_sitemap
from .sitemaps import ConcurrentSitemap, TenderSitemap

from nas import views as nas_views
from base.views import robots_txt


urlpatterns = i18n_patterns(
    path('',                include('base.urls')),
    path('admin/',          admin.site.urls),
    path('@<str:username>', nas_views.username_view, name='nas_at_username'),
    path('accounts/',       include('allauth.urls')),
    path('user/',           include('nas.urls')),
    path('tenders/',        include('portal.urls')),
    path('porders/',            include('bdc.urls')),
    path('bidders/',        include('insights.urls')),
    path('bidding/',        include('bidding.urls')),
    
    path('__debug__/', include('debug_toolbar.urls')),
)

urlpatterns += [
    path("robots.txt", robots_txt, name="robots_txt"),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

def stop_requesting_favicon(request):
    return HttpResponse(status=204)

urlpatterns += [path("favicon.ico", stop_requesting_favicon),]

sitemaps = {
    'concurrents': ConcurrentSitemap,
    'tenders': TenderSitemap,
}

# urlpatterns += [
#     # path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
#     # 1. Main index file listing all sub-sitemaps
#     path(
#         'sitemap.xml', 
#         # cache_page(86400)(index), 
#         index,
#         {'sitemaps': sitemaps}, 
#         name='django.contrib.sitemaps.views.index'
#     ),
    
#     # 2. Individual paginated sitemaps (e.g. sitemap-items.xml?p=1)
#     path(
#         'sitemap-<section>.xml', 
#         # cache_page(86400)(sitemap),
#         sitemap,
#         {'sitemaps': sitemaps}, 
#         name='django.contrib.sitemaps.views.sitemap'
#     ),
# ]

urlpatterns += [
    path(
        'sitemap.xml', 
        # clean_sitemap_index, 
        cache_page(86400)(clean_sitemap_index),
        {'sitemaps': sitemaps}, 
        name='django.contrib.sitemaps.views.index'
    ),

    path(
        'sitemap-<section>.xml', 
        # clean_sitemap, 
        cache_page(86400)(clean_sitemap),
        {'sitemaps': sitemaps}, 
        name='django.contrib.sitemaps.views.sitemap'
    ),
]