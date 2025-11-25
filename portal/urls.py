
from django.urls import path, include
from . import views


urlpatterns = [
    
    path('',                            views.tender_list,              name='portal_tender_list'),
    path('chrono/<str:ch>/',            views.tender_details_chrono,    name='portal_tender_detail_chrono'),
    path('details/<uuid:pk>/',          views.tender_details,           name='portal_tender_detail'),
    path('dce/<uuid:pk>/<str:fn>/',     views.tender_get_file,          name='portal_tender_get_file'),

    path('clients/',                    views.client_list,              name='portal_client_list'),
    path('locations/',                  views.locations_list,           name='portal_locations_list'),
    
    path('favorites/',                  views.tender_favorite_list,     name='portal_tender_favorite_list'),
    path('favorites/clean/<str:span>/', views.tender_favorite_clean,    name='portal_tender_favorite_clean'),
    path('favorite/add/<uuid:pk>/',     views.tender_favorite,          name='portal_tender_favorite_add'),
    path('favorite/remove/<uuid:pk>/',  views.tender_unfavorite,        name='portal_tender_favorite_remove'),
]
