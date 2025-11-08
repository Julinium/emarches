
from nas.models import UserSetting, Favorite

def portal_context(request):

    context = {}
    user = request.user
    if not user or not user.is_authenticated:
        return context
        
    user_settings = UserSetting.objects.filter(user = request.user).first()
    faved_ids = user.favorites.values_list('tender', flat=True)

    context['user_settings'] = user_settings
    context['faved_ids'] = faved_ids

    return context



