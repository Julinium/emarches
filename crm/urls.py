
from django.urls import include, path

from . import views

urlpatterns = [
    path('users/', views.customer_list_view,   name='crm_customer_list'),
]

