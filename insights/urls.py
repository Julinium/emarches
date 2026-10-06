
from django.urls import include, path

from . import views

urlpatterns = [

    path('',                   views.dashboard,         name='insights_dashboard'),
    path('list/',              views.bidders_list,      name='insights_bidders_list'),
    path('details/<uuid:pk>/', views.bidder_details,    name='insights_bidder_details'),
    path('pdf/<uuid:pk>/',     views.bidder_pdf,        name='insights_bidder_pdf'),
    path('print/<uuid:pk>/',   views.bidder_printable,  name='insights_bidder_printable'),
    path('csv/<uuid:pk>/',     views.bidder_csv,        name='insights_bidder_csv'),

]

