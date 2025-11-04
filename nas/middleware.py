
from django.conf import settings
from django.utils import translation
from nas.models import UserSetting
# from django.conf import global_settings

class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                user_settings = request.user.settings.first()
                preferred_language = user_settings.preferred_language
                request.session[settings.SESSION_LANGUAGE_KEY] = preferred_language
            except UserSetting.DoesNotExist:
                pass  # Fallback to default behavior
        
        response = self.get_response(request)
        return response