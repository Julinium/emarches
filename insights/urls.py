
from django.urls import include, path

from . import views

urlpatterns = [

    path('',               views.dashboard,        name='insights_dashboard'),
    path('list/',          views.bidders_list,     name='insights_bidders_list'),
    path('<uuid:pk>/',     views.bidder_details,   name='insights_bidder_details'),

    path('pdf/<uuid:pk>/', views.bidder_pdf,       name='insights_bidder_pdf'),
    path('csv/<uuid:pk>/', views.bidder_csv,       name='insights_bidder_csv'),


    # path('loc/',                views.locations_list,           name='bdc_locations_list'),
    # path('cli/',                views.client_list,              name='bdc_client_list'),

    # path('fav/',                views.bdc_favorite_list,        name='bdc_bdc_favorite_list'),
    # path('<uuid:pk>/fav/add/',  views.bdc_stickies_add,         name='bdc_bdc_stickies_add'),
    # path('<uuid:pk>/fav/del/',  views.bdc_stickies_remove,      name='bdc_bdc_stickies_remove'),
    # path('fav/del/',            views.bdc_stickies_remove_all,  name='bdc_bdc_stickies_remove_all'),
]

