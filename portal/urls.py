
from django.urls import path, include
from . import views


urlpatterns = [
    path('tenders', views.TenderListView.as_view(), name='portal_tender_list'),
    path('tender/<uuid:pk>/', views.TenderDetailView.as_view(), name='portal_tender_detail'),
]
