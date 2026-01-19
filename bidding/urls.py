
from django.urls import path, include
from . import views


urlpatterns = [

    path('dashboard',                       views.dashboard,    name='bidding_dashboard'),

    path('bids/',                           views.bids_list,    name='bidding_bids_list'),
    path('bids//details/<uuid:pk>/',        views.bid_details,  name='bidding_bid_details'),
    path('bids/create/<uuid:tk>/',          views.bid_edit,     name='bidding_bid_create'),
    path('bids/edit/<uuid:pk>/',            views.bid_edit,     name='bidding_bid_edit'),
    path('bids/delete/<uuid:pk>/',          views.bid_delete,   name='bidding_bid_delete'),
    path('bids/files/<uuid:pk>/<str:path>', views.bid_get_file, name='bidding_bid_get_file'),

    # path('contracts/',              views.contracts_list,   name='bidding_contracts_list'),
    # path('contracts/<uuid:pk>/',    views.contract_details, name='bidding_contract_details'),

    # path('contacts/',               views.contacts_list,    name='bidding_contacts_list'),
    # path('contacts/<uuid:pk>/',     views.contact_details,  name='bidding_contact_details'),

    # path('expenses/',               views.expenses_list,    name='bidding_expenses_list'),
    # path('expenses/<uuid:pk>/',     views.expense_details,  name='bidding_expense_details'),

    # path('incomes/',                views.incomes_list,     name='bidding_incomes_list'),
    # path('incomes/<uuid:pk>/',      views.income_details,   name='bidding_income_details'),

]

