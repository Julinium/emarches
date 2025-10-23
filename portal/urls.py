
from django.urls import path, include
from . import views


urlpatterns = [
    path('tenders', views.tender_list, name='portal_tender_list'),
]
