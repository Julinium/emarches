
from django.urls import path, include
from . import views


urlpatterns = [
    
    path('',                            views.bdc_list,                 name='bdc_bdc_list'),
    path('details/<uuid:pk>/',          views.bdc_details,              name='bdc_bdc_detail'),
    path('print/<uuid:pk>/<str:fn>/',   views.bdc_items_pdf,            name='bdc_articles_pdf'),
    path('export/<uuid:pk>/<str:fn>/',  views.bdc_items_csv,            name='bdc_articles_csv'),

    path('locations/',                  views.locations_list,           name='bdc_locations_list'),
    path('clients/',                    views.client_list,              name='bdc_client_list'),
    
    path('favorites/',                  views.bdc_favorite_list,        name='bdc_bdc_favorite_list'),
    path('favorites/add/<uuid:pk>/',    views.bdc_stickies_add,         name='bdc_bdc_stickies_add'),
    path('favorites/remove/<uuid:pk>/', views.bdc_stickies_remove,      name='bdc_bdc_stickies_remove'),
    path('favorites/clean/',            views.bdc_stickies_remove_all,  name='bdc_bdc_stickies_remove_all'),
]
