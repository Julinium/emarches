
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from nas.models import Profile

@login_required
def profile(request):
    user = request.user
    # profile = profile
    try:
        profile = user.profile
    except:
        profile = Profile(user=user)
        profile.save()

    context = {
        'user': user,
        'profile': user.profile,
    }

    if not user.profile.onboarded:
        return redirect('nas_onboard')

    return render(request, 'nas/profile.html', context)


@login_required
def onboard(request):
    context = {
        'user': request.user,
        'profile': request.user.profile,
    }
    return render(request, 'nas/onboard.html', context)