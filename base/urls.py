from django.urls import include, path

from base import views

urlpatterns = [
    path('', views.home, name='base_home'),
    path('logs/<str:logger>', views.view_log_file, name='base_view_log_file')
]