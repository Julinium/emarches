from collections import defaultdict, OrderedDict
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
def offsettify(optimal, amount):
    o, r = None, None
    if optimal != None and amount != None : 
        if optimal != 0 : 
            o = amount - optimal
            r = 100 * ((amount - optimal) / optimal)

    return {"slip": o, "ratio": r}


@register.filter
def group_by(queryset, field_name):
    """
    Groups a queryset by a model field.

    Usage:
        {% for group in queryset|group_by:"field1" %}
            {{ group.field1 }}
            {% for item in group.items %}
                {{ item }} ...
            {% endfor %}
        {% endfor %}
    """

    def statify(estimate, offers):
        amounts = [o.amount_a for o in offers]
        mean = sum(amounts) / len(amounts) if amounts else None
        mid = (estimate + mean) / 2 if amounts else None

        return [mean, mid]

    groups = OrderedDict()

    for obj in queryset:
        key = getattr(obj, field_name)
        groups.setdefault(key, []).append(obj)

    return [
        {
            field_name: key,
            "averaum": statify(items[0].lot.estimate, items)[0],
            "optimum": statify(items[0].lot.estimate, items)[1],
            "amzgaro": items[0],
            "qahnsen": items,
        }
        for key, items in groups.items()
    ]



    