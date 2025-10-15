
from django.urls import path, include

from . import views

urlpatterns = [
    path('profile', views.profile_view, name='nas_profile_view'),
    path('profile/edit', views.profile_edit, name='nas_profile_edit'),
    path('onboard', views.onboard, name='nas_onboard'),
]
