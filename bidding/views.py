from django.shortcuts import render
from django.http import HttpResponse


def dashboard(request):
    return HttpResponse('Dashboard')

def bids_list(request):
    return HttpResponse('Bids List')

def bid_details(request):
    return HttpResponse('Bid Details')


