
from django.urls import path, include
from . import views


urlpatterns = [
    # path('', views.TenderListView.as_view(), name='portal_tender_list'),
    path('', views.tender_list, name='portal_tender_list'),
    path('details/<uuid:pk>/', views.tender_details, name='portal_tender_detail'),
    path('dce/<uuid:pk>/<str:fn>', views.tender_get_file, name='portal_tender_get_file'),
    
    path('favorite/<uuid:pk>/', views.tender_favorite, name='tender_favorite'),
    path('unfavorite/<uuid:pk>/', views.tender_unfavorite, name='tender_unfavorite'),
    path('choices/', views.company_folder_choices, name='company_folder_choices'),
]
