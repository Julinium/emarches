
from django.urls import include, path

from . import views

urlpatterns = [

    path('',                    views.bdc_list,                 name='bdc_bdc_list'),
    path('<uuid:pk>/',          views.bdc_details,              name='bdc_bdc_detail'),

    path('<uuid:pk>/pdf/<str:fn>/', views.bdc_items_pdf,            name='bdc_articles_pdf'),
    path('<uuid:pk>/csv/<str:fn>/', views.bdc_items_csv,            name='bdc_articles_csv'),

    path('loc/',                views.locations_list,           name='bdc_locations_list'),
    path('cli/',                views.client_list,              name='bdc_client_list'),

    path('fav/',                views.bdc_favorite_list,        name='bdc_bdc_favorite_list'),
    path('<uuid:pk>/fav/add/',  views.bdc_stickies_add,         name='bdc_bdc_stickies_add'),
    path('<uuid:pk>/fav/del/',  views.bdc_stickies_remove,      name='bdc_bdc_stickies_remove'),
    path('fav/del/',            views.bdc_stickies_remove_all,  name='bdc_bdc_stickies_remove_all'),
]

