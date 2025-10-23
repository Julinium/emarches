from django.shortcuts import render
from django.http import HttpResponse

def tender_list(request):
    return HttpResponse('Tenders List', status=200)
