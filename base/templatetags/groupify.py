from collections import defaultdict, OrderedDict
from django.forms.models import model_to_dict

from django import template
from decimal import Decimal

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


@register.simple_tag
def progrefy(R, D):

    R = Decimal(R)
    D = Decimal(D)

    if R == 0: return 0
    
    min_val = R - R * Decimal("0.26")
    max_val = R + R * Decimal("0.26")

    if D < min_val:
        D = min_val
    elif D > max_val:
        D = max_val
    d_percent = ((D - min_val) / (max_val - min_val)) * Decimal("100")

    return round(d_percent)




