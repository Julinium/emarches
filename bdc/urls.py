
from django.urls import path, include
from . import views


urlpatterns = [
    
    path('',                            views.bdc_list,              name='bdc_bdc_list'),
    # path('chrono/<str:ch>/',            views.bdc_details_chrono,    name='bdc_bdc_detail_chrono'),
    path('details/<uuid:pk>/',          views.bdc_details,           name='bdc_bdc_detail'),
    # path('dce/<uuid:pk>/<str:fn>/',     views.bdc_get_file,          name='bdc_bdc_get_file'),

    # path('locations/',                  views.locations_list,        name='bdc_locations_list'),
    # path('clients/',                    views.clients_list,          name='bdc_clients_list'),
    
    # path('favorites/',                  views.bdc_favorite_list,     name='bdc_bdc_favorite_list'),
    # path('favorites/clean/<str:span>/', views.bdc_favorite_clean,    name='bdc_bdc_favorite_clean'),
    # path('favorite/add/<uuid:pk>/',     views.bdc_favorite,          name='bdc_bdc_favorite_add'),
    # path('favorite/remove/<uuid:pk>/',  views.bdc_unfavorite,        name='bdc_bdc_favorite_remove'),
]
