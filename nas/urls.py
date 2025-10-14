
from django.urls import path, include

from . import views

urlpatterns = [
    path('profile', views.profile, name='nas_profile'),
    path('onboard', views.onboard, name='nas_onboard'),
]
