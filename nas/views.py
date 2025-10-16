
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from nas.models import Profile
from nas.forms import UserProfileForm

@login_required
def profile_view(request):    
    user = request.user
    try:
        profile = user.profile
    except:
        profile = Profile(user=user)
        profile.save()

    context = {
        'user': user,
        'profile': user.profile,
    }

    # if not user.profile.onboarded:
    #     return redirect('nas_profile_edit')

    return render(request, 'nas/profile-view.html', context)


@login_required
def profile_edit(request):
    user = request.user
    try:
        profile = user.profile
    except:
        profile = Profile(user=user)
        profile.save()
    # referer = request.META.get('HTTP_REFERER', None)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, request=request)
        if form.is_valid():
            form.save()
            return redirect('nas_profile_view')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = UserProfileForm(instance=profile, request=request)
    return render(request, 'nas/profile-edit.html', {'form': form})


@login_required
def onboard(request):
    context = {
        'user': request.user,
        'profile': request.user.profile,
    }
    return render(request, 'nas/onboard.html', context)