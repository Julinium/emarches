from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def user_profile(request):
    context = {}
    user = request.user
    if user.is_authenticated: 
        context["user"] = user
    return render(request, 'authy/user-profile.html', context)
