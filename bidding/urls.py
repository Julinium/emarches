
from django.urls import include, path

from . import views

urlpatterns = [

    path('dashboard',                views.dashboard,    name='bidding_dashboard'),

    path('tenders/',                 views.tenders_list, name='bidding_tenders_list'),
    path('bids/',                    views.bids_list,    name='bidding_bids_list'),
    path('bonds/',                   views.bonds_list,   name='bidding_bonds_list'),
    path('bids/<uuid:pk>/details/',  views.bid_details,  name='bidding_bid_details'),
    path('bids/<uuid:lk>/create/',   views.bid_edit,     name='bidding_bid_create'),
    path('bids/<uuid:pk>/edit/',     views.bid_edit,     name='bidding_bid_edit'),
    path('bids/<uuid:pk>/delete/',   views.bid_delete,   name='bidding_bid_delete'),
    path('bids/<uuid:pk>/<str:ft>/', views.bid_file,     name='bidding_bid_file'),

    path('tasks/<uuid:bk>/create/', views.task_edit,    name='bidding_task_create'),
    path('tasks/<uuid:pk>/edit/',   views.task_edit,    name='bidding_task_edit'),
    path('tasks/<uuid:pk>/delete/', views.task_delete,  name='bidding_task_delete'),

    path('expenses/<uuid:bk>/create/', views.expense_edit, name='bidding_expense_create'),
    path('expenses/<uuid:pk>/edit/',   views.expense_edit, name='bidding_expense_edit'),
    path('expenses/<uuid:pk>/delete/', views.expense_delete, name='bidding_expense_delete'),

    path('team/',                   views.member_list, name='bidding_member_list'),
    path('team/<uuid:tk>/invite',   views.invitation_create, name='bidding_invitation_create'),

    # path('contracts/',              views.contracts_list,   name='bidding_contracts_list'),
    # path('contracts/<uuid:pk>/',    views.contract_details, name='bidding_contract_details'),

    # path('contacts/',               views.contacts_list,    name='bidding_contacts_list'),
    # path('contacts/<uuid:pk>/',     views.contact_details,  name='bidding_contact_details'),

    # path('expenses/',               views.expenses_list,    name='bidding_expenses_list'),
    # path('expenses/<uuid:pk>/',     views.expense_details,  name='bidding_expense_details'),

    # path('incomes/',                views.incomes_list,     name='bidding_incomes_list'),
    # path('incomes/<uuid:pk>/',      views.income_details,   name='bidding_income_details'),

]

