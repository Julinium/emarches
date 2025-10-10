from django.contrib import admin
from django.urls import path, include

from authy import views

urlpatterns = [
    path('user-profile/', views.user_profile, name='authy_profile'),
]