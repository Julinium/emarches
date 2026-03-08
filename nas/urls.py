
from django.urls import include, path

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
    path('settings', views.user_settings, name='nas_user_settings'),
    path('settings/reset', views.user_settings_reset, name='nas_user_settings_reset'),

    # path('onboard', views.onboard, name='nas_onboard'),
    
    path('notifications/all-on', views.enableAllNotifications, name='nas_enable_all_notifications'),
    path('newsletters/all-on', views.enableAllNewsletters, name='nas_enable_all_newsletters'),
    path('notifications/tune', views.tuneNotifications, name='nas_tune_notifications'),
    path('newsletters/tune', views.tuneNewsletters, name='nas_tune_newsletters'),

    path('companies/<uuid:pk>/agrements/', views.manage_company_agrements, name='nas_company_agrements'),
    path('companies/<uuid:pk>/qualifs/', views.manage_company_qualifs, name='nas_company_qualifs'),
    path('companies/<uuid:pk>/icify/', views.accept_iced_company, name='nas_company_icify'),


    path('companies/',                  views.companies_list,              name='nas_company_list'),
    path('companies/<uuid:pk>/files/<str:ft>/', views.company_file,   name='nas_company_file'),
    # path('x_companies/', views.CompanyListView.as_view(), name='x_nas_company_list'),
    path('companies/new/', views.CompanyCreateView.as_view(), name='nas_company_create'),
    path('companies/<uuid:pk>/', views.CompanyDetailView.as_view(), name='nas_company_detail'),
    path('companies/<uuid:pk>/edit/', views.CompanyUpdateView.as_view(), name='nas_company_edit'),
    path('companies/<uuid:pk>/delete/', views.CompanyDeleteView.as_view(), name='nas_company_delete'),


    path('manageriats/<uuid:ck>/create/',   views.manageriat_edit,   name='nas_manageriat_create'),
    path('manageriats/<uuid:pk>/<uuid:ck>/edit/',     views.manageriat_edit,   name='nas_manageriat_edit'),
    path('manageriats/<uuid:pk>/files/<str:ft>/', views.manageriat_file,   name='nas_manageriat_file'),

    path('signatures/<uuid:ck>/create/',   views.signature_key_edit,   name='nas_signature_key_create'),
    path('signatures/<uuid:pk>/<uuid:ck>/edit/',     views.signature_key_edit,   name='nas_signature_key_edit'),
    path('signatures/<uuid:pk>/files/<str:ft>/', views.signature_key_file,   name='nas_signature_key_file'),

    path('expirables/<uuid:ck>/create/',   views.expirable_edit,   name='nas_expirable_create'),
    path('expirables/<uuid:pk>/<uuid:ck>/edit/',     views.expirable_edit,   name='nas_expirable_edit'),
    path('expirables/<uuid:pk>/files/<str:ft>/', views.expirable_file,   name='nas_expirable_file'),




]

