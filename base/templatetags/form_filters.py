from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    if not hasattr(field, 'field'):
        return field
    attrs = field.field.widget.attrs
    current = attrs.get('class', '')
    attrs['class'] = f"{current} {css_class}".strip()
    return field