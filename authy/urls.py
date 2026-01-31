from django.contrib import admin
from django.urls import include, path

from authy import views

urlpatterns = [
    path('user-profile/', views.user_profile, name='authy_profile'),
]