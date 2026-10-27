
from django.urls import include, path

from . import views

urlpatterns = [
    path('', views.search,   name='bos_search'),
    path('pdf/<str:pk>', views.log_pdf_download,   name='bos_log_pdf_download'),
]

