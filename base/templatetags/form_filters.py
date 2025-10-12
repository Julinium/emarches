from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    """Add a CSS class to a field's widget classes."""
    if not hasattr(field, 'field'):  # Check if field is a BoundField
        return field  # Return unchanged if not a BoundField (e.g., string)
    attrs = field.field.widget.attrs
    current = attrs.get('class', '')
    attrs['class'] = f"{current} {css_class}".strip()
    return field