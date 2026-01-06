from collections import defaultdict, OrderedDict
from django.forms.models import model_to_dict

from django import template

register = template.Library()

@register.simple_tag
def group_lots(items):
    grouped = defaultdict(list)

    for item in items:        
        concurrent  = getattr(item, 'concurrent')
        lot         = getattr(item, 'lot_number')
        grouped[concurrent].append(lot)

    return dict(grouped)

@register.simple_tag
def group_tenders(items):
    grouped = defaultdict(list)

    for item in items:
        opening     = getattr(item, 'opening')
        lot         = getattr(item, 'lot_number')
        grouped[opening].append(lot)

    return dict(grouped)


@register.simple_tag
def group_depos(items):
    grouped = defaultdict(list)

    for item in items:
        opening     = getattr(item, 'opening')
        grouped[opening].append(item)

    return dict(grouped)



@register.filter
def group_by(queryset, field_name):

    groups = OrderedDict()

    for obj in queryset:
        key = getattr(obj, field_name)
        groups.setdefault(key, []).append(obj)

    return [
        {
            field_name: key,
            "amzgaro": items[0],
            "qahnsen": items,
        }
        for key, items in groups.items()
    ]









