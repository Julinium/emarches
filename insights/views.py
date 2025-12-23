from django.shortcuts import render
from django.http import HttpResponse


def dashboard(request):
    return HttpResponse('Dashboard Home')

def bidders_list(request):
    return HttpResponse('Bidders List')
