from datetime import datetime, timedelta

from django.shortcuts import render

VPS_SERVER_MONTH = 64



def home(request):
    target = 0
    mail_server = VPS_SERVER_MONTH

    today = datetime.now().date()
    # epoch_zero=today
    # epoch_zero.day=1
    # epoch_zero.month=1
    epoch_zero = datetime(today.year, 1, 1)
    run_days = today - epoch_zero.date()
    

    period_name = today.strftime('%Y')
    period_progress = 23
    amount_progress = 34

    amount_funded   = 1300
    amount_goal     = 5700


    context = {}

    return render(request, 'base/home.html')

# Custom errors handling

# def custom_400_view(request, exception): #bad_request
#     return render(request, "base/errors/400.html", status=400)

# def custom_403_view(request, exception): #permission_denied
#     return render(request, "base/errors/403.html", status=403)

# def custom_404_view(request, exception): #page_not_found
#     return render(request, "base/errors/404.html", status=404)

# def custom_500_view(request): #server_error
#     return render(request, "base/errors/500.html", status=500)

