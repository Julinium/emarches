from django import template
from django.utils.html import format_html
from django.utils.translation import gettext as _

register = template.Library()

@register.simple_tag(takes_context=True)
def protected_value(context, obj, value, required_permissions=None, fallback_mode="cta"):
    """
    Returns `value` if user is authenticated and satisfies required permissions.
    Otherwise, returns a fallback placeholder or CTA HTML snippet.

    Usage:
        {% protected_value my_object secret_value required_permissions='app.view_model' %}
        {% protected_value my_object "Secret" required_permissions='app.change_model' fallback_mode="placeholder" %}
    """
    request = context.get('request')

    # If request is missing or user is anonymous, deny access
    if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
        return _render_fallback(fallback_mode)

    user = request.user

    # Normalize permissions parameter into a list
    if isinstance(required_permissions, str):
        perms = [required_permissions]
    elif isinstance(required_permissions, (list, tuple)):
        perms = list(required_permissions)
    else:
        perms = []

    # Check object-level or standard Django permissions
    if perms:
        # Check standard user permissions (or django-guardian object perms if passed obj)
        has_perms = user.has_perms(perms)
        if not has_perms:
            return _render_fallback(fallback_mode)

    # All checks passed: return the original value
    return value


def _render_fallback(mode="cta"):
    """Renders translatable placeholders or HTML snippets."""
    if mode == "placeholder":
        # Translatable inline placeholder
        hidden_text = _("Hidden Content")
        return format_html('<span class="text-muted font-italic">[{}]</span>', hidden_text)

    # Default 'cta' mode: Call-to-Action button redirecting to login
    cta_label = _("Log in to view")
    return format_html(
        '<a href="/accounts/login/" class="btn btn-sm btn-primary permission-cta">{}</a>',
        cta_label
    )