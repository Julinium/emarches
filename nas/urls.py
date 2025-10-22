
from django.urls import path, include
from . import views

# from .views import (
#     CompanyListView,
#     CompanyDetailView,
#     CompanyCreateView,
#     CompanyUpdateView,
#     CompanyDeleteView,
# )

urlpatterns = [
    path('profile', views.profile_view, name='nas_profile_view'),
    path('profile/edit', views.profile_edit, name='nas_profile_edit'),
    path('onboard', views.onboard, name='nas_onboard'),
    path('notifications/all-on', views.enableAllNotifications, name='nas_enable_all_notifications'),
    path('newsletters/all-on', views.enableAllNewsletters, name='nas_enable_all_newsletters'),
    path('notifications/tune', views.tuneNotifications, name='nas_tune_notifications'),
    path('newsletters/tune', views.tuneNewsletters, name='nas_tune_newsletters'),

    path('company/<uuid:pk>/agrements/', views.manage_company_agrements, name='nas_company_agrements'),
    path('company/<uuid:pk>/qualifs/', views.manage_company_qualifs, name='nas_company_qualifs'),
    path('company/<uuid:pk>/icify/', views.accept_iced_company, name='nas_company_icify'),
    
    
    path('company/', views.CompanyListView.as_view(), name='nas_company_list'),
    path('company/new/', views.CompanyCreateView.as_view(), name='nas_company_create'),
    path('company/<uuid:pk>/', views.CompanyDetailView.as_view(), name='nas_company_detail'),
    path('company/<uuid:pk>/edit/', views.CompanyUpdateView.as_view(), name='nas_company_edit'),
    path('company/<uuid:pk>/delete/', views.CompanyDeleteView.as_view(), name='nas_company_delete'),
]
