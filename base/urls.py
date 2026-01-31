from django.urls import include, path

from base import views

urlpatterns = [
    path('', views.home, name='base_home'),
]