
from django.urls import path, include
from . import views

from .views import (
    CompanyListView,
    CompanyDetailView,
    CompanyCreateView,
    CompanyUpdateView,
    CompanyDeleteView,
)

urlpatterns = [
    path('profile', views.profile_view, name='nas_profile_view'),
    path('profile/edit', views.profile_edit, name='nas_profile_edit'),
    path('onboard', views.onboard, name='nas_onboard'),

    path('company/', CompanyListView.as_view(), name='nas_company_list'),
    path('company/new/', CompanyCreateView.as_view(), name='nas_company_create'),
    path('company/<uuid:pk>/', CompanyDetailView.as_view(), name='nas_company_detail'),
    path('company/<uuid:pk>/edit/', CompanyUpdateView.as_view(), name='nas_company_edit'),
    path('company/<uuid:pk>/delete/', CompanyDeleteView.as_view(), name='nas_company_delete'),
]
