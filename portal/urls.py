
from django.urls import path, include
from . import views


urlpatterns = [
    path('list', views.TenderListView.as_view(), name='portal_tender_list'),
    # path('details/<uuid:pk>/', views.TenderDetailView.as_view(), name='portal_tender_detail'),
    path('details/<uuid:pk>/', views.tender_details, name='portal_tender_detail'),
]
