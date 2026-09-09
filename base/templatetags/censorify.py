from django import template
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as trans
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag
def censorify(user, value='-', url="/accounts/login/", next_path=None, btn_text=None):
    
    if not user or not user.is_authenticated:
        if not btn_text: btn_text = trans("Sign in")
        # url = "/accounts/login/"

        if next_path:
            url += f"?{urlencode({'next': next_path})}"

        return format_html(
            '<a href="{}" class="btn btn-sm btn-outline-primary py-1 my-1 small"><i class="bi bi-lock text-danger me-1"></i>{}</a>',
            url,
            btn_text
        )

    return value

    # TODO: Implement permission check logic

    # if user and user.is_authenticated and user.has_perm(perm_name):
    #     return value

    # return format_html(
    #     '<a href="{}" class="btn btn-sm btn-outline-primary p-1"><i class="bi bi-lock text-danger"></i>{}</a>',
    #     url,
    #     btn_text
    # )