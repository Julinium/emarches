
from django.urls import path, include
from . import views


urlpatterns = [

    path('',           views.dashboard,   name='bidding_dashboard'),
    path('bidding/',   views.bids_list,   name='bidding_bids_list'),
    path('<uuid:pk>/', views.bid_details, name='bidding_bid_details'),

]

