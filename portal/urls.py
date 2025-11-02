
from django.urls import path, include
from . import views


urlpatterns = [
    path('', views.TenderListView.as_view(), name='portal_tender_list'),
    path('details/<uuid:pk>/', views.tender_details, name='portal_tender_detail'),
    path('dce/<uuid:pk>/<str:fn>', views.tender_get_file, name='portal_tender_get_file'),
]
