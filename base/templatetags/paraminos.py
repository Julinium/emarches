import ast
import json

from django import template
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def stringify(value):
    return str(value)

