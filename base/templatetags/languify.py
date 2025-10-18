from django import template
# from django.urls import resolve, reverse
from django.conf import settings

register = template.Library()

@register.simple_tag(takes_context=True)
def switch_language(context, lang_code):
    request = context['request']
    path = request.path
    path_parts = path.split('/')

    valid_languages = [lang[0] for lang in settings.LANGUAGES]

    if len(path_parts) > 1 and path_parts[1] in valid_languages:  # Adjust for your language codes
        path_parts[1] = lang_code
    else:
        path_parts.insert(1, lang_code)
    new_path = '/'.join(path_parts)
    # Preserve query parameters
    query_string = request.GET.urlencode()
    if query_string:
        new_path = f"{new_path}?{query_string}"
    return new_path