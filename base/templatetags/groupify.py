from collections import defaultdict
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

@register.simple_tag
def referefy(estimate, offers):

    amounts = [o.get("amount_w") for o in offers if o.get("amount_w") is not None]
    if not amounts:
        return None, None
    M = sum(amounts) / len(amounts)
    R = (estimate + M) / 2
    return M, R