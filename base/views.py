# from django.shortcuts import render
from django.http import HttpResponse
from base.models import Client

def home(request):
    clients = Client.objects.filter(short=None)

    str = ""
    i = 0
    for c in clients:
        str += f"=== c.name\n"
        c.save()
        i += 1


    return HttpResponse(f"============ {i} / { clients.count() } ============")