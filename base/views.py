# from django.shortcuts import render
from django.http import HttpResponse
# from base.models import Client

def home(request):
    # clients = Client.objects.filter(short__contains='/')

    # i = 0
    # for c in clients:
    #     c.short = c.short.replace("/", "").strip()
    #     c.save()
    #     i += 1


    # return HttpResponse(f"============ {i} / { clients.count() } ============")
    return HttpResponse(f"========================")