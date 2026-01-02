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


# @register.simple_tag
# def offsettify(optimal, amount):
#     o, r = None, None
#     if optimal != None and amount != None : 
#         if optimal != 0 : 
#             o = amount - optimal
#             r = 100 * ((amount - optimal) / optimal)

#     return {"slip": o, "ratio": r}


@register.filter
def group_by(queryset, field_name):

    # def statify(estimate, offers):
    #     amounts = [o.amount_a for o in offers]
    #     mean = sum(amounts) / len(amounts) if amounts else None
    #     mid = (estimate + mean) / 2 if amounts else None

    #     return [mean, mid]

    groups = OrderedDict()

    for obj in queryset:
        key = getattr(obj, field_name)
        groups.setdefault(key, []).append(obj)

    return [
        {
            field_name: key,
            # "averaum": statify(items[0].lot.estimate, items)[0],
            # "optimum": statify(items[0].lot.estimate, items)[1],
            "amzgaro": items[0],
            "qahnsen": items,
        }
        for key, items in groups.items()
    ]


# @register.filter
# def group_by(queryset, field_name):
    
#     def statify(estimate, offers):
#         amounts = [o.amount_a for o in offers]
#         mean = sum(amounts) / len(amounts) if amounts else None
#         mid = (estimate + mean) / 2 if amounts else None
#         return [mean, mid]
    
#     def referify(optimal, amount):
#         o, r = None, None
#         if optimal != None and amount != None : 
#             if optimal != 0 : 
#                 o = amount - optimal
#                 r = 100 * ((amount - optimal) / optimal)

#         return {"slip": o, "ratio": r}


#     groups = OrderedDict()

#     for obj in queryset:
#         key = getattr(obj, field_name)
#         groups.setdefault(key, []).append(obj)

#     grouped = [
#         {
#             field_name: key,
#             "averaum": statify(items[0].lot.estimate, items)[0],
#             "optimum": statify(items[0].lot.estimate, items)[1],
#             # "ref_slip" : referify,
#             "amzgaro": items[0],
#             "qahnsen": items,
#         }
#         for key, items in groups.items()
#     ]


#     for group in grouped:
#         qs = group["qahnsen"]
#         qahnsen = [model_to_dict(obj) for obj in qs]
#         # qahnsen = list(group["qahnsen"].values())
#         optimal = group["optimum"]

#         for depo in qahnsen:
#             # depo = model_to_dict(depo)
#             amount  = depo["amount_a"]
#             offset  = referify(optimal, amount)
#             depo["ref_slip"] = offset["slip"]
    
#     print( '\n\n\n================', grouped,'================\n\n\n')
    
#     return grouped









