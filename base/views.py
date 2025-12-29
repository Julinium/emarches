from django.shortcuts import render


VPS_SERVER_MONTH = 64

# APP server
# DB server
# Mail server
# Developper
# Domain name

# $53.62
# $63.81 incl. 19% VAT

# Error pages in nginx




def home(request):
    target = 0
    mail_server = VPS_SERVER_MONTH
    context = {}

    return render(request, 'base/home.html')

# Custom errors handling

def custom_400_view(request, exception): #bad_request
    return render(request, "base/errors/400.html", status=400)

def custom_403_view(request, exception): #permission_denied
    return render(request, "base/errors/403.html", status=403)

def custom_404_view(request, exception): #page_not_found
    return render(request, "base/errors/404.html", status=404)

def custom_500_view(request): #server_error
    return render(request, "base/errors/500.html", status=500)

