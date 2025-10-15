from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.conf import settings
# from django.conf.urls import handler400, handler403, handler404, handler500

# from private_storage import views as pv_views
from private_storage.views import PrivateStorageView

from base import views as base_views

# handler400 = "base_views.custom_400_view" # Bad request
# handler403 = "base_views.custom_403_view" # Forbidden
# handler404 = "base_views.custom_404_view" # Not found
# handler500 = "base_views.custom_500_view" # Internal server error

urlpatterns = []

urlpatterns += i18n_patterns(
    path('', include('base.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('authy.urls')),
    path('accounts/', include('allauth.urls')),
    path('users/', include('nas.urls')),
    path('users/', include('nas.urls')),

    path('private/<path:path>', PrivateStorageView.as_view(), name='serve_private_file'),

)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


