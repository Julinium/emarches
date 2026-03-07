from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse

from nas import views as nas_views


urlpatterns = i18n_patterns(
    path('',                include('base.urls')),
    path('admin/',          admin.site.urls),
    path('@<str:username>', nas_views.username_view, name='nas_at_username'),
    path('accounts/',       include('allauth.urls')),
    path('user/',           include('nas.urls')),
    path('tenders/',        include('portal.urls')),
    path('bdc/',            include('bdc.urls')),
    path('insights/',       include('insights.urls')),
    path('bidding/',        include('bidding.urls')),
    
    path('__debug__/', include('debug_toolbar.urls')),
)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

def stop_requesting_favicon(request):
    return HttpResponse(status=204)

urlpatterns += [path("favicon.ico", stop_requesting_favicon),]
