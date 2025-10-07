# from django.shortcuts import render
from django.http import HttpResponse
from base.models import FileToGet

def home(request):
    ftg = FileToGet.objects.all()
    return HttpResponse(f"============ {ftg.count()} ============")