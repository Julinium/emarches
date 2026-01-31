import ast
import json

from django import template
from django.utils.translation import gettext as _

register = template.Library()

CHANGES_FIELDS = {
    'cancelled': _('Cancelled'),
    'title': _('Tender Object'),
    'reference':_('Reference'),
    'published':_('Date Published'),
    'deadline': _('Deadline'),
    'estimate': _('Estimate'),
    'bond': _('Guarantee'),
    'size_bytes': _('Actual files size'),
    'size_read': _('Displayed files size'),
    'contact_name': _('Contact name'),
    'contact_phone': _('Contact phone'),
    'contact_email': _('Contact email'),
    'contact_fax': _('Contact fax'),

    'address_opening': _('Opening Address'),
    'address_bidding': _('Bidding Address'),
    'address_withdrawal': _('Withdrawal Address'),
    'esign': _('Electronic signature'),
    'ebid': _('Electronic bidding'),
    'location': _('Execution location'),
    'variant': _('Variants'),
    'reserved': _('Reserved'),
    'plans_price': _('Plans price'),
    'lots_count': _('Lots count'),
    'lot': _('Lots'),
    'link': _('Link'),
    'acronym': _('Acronym'),
    'chrono': _('Number'),
    'category': _('Category'),
    'mode': _('Mode'),
    'procedure': _('Procedure'),
    'client': _('Public client'),

    'qualif': _('Qualifications'),
    'agrement': _('Licenses'),
    'meeting': _('Meetings'),
    'sample': _('Samples'),
    'visit': _('Visits'),
}


@register.filter
def dictify(value):
    try:
        evaled = ast.literal_eval(value)
        json_str = json.dumps(evaled)
        data = json.loads(json_str)

        for item in data:
            item['field'] = str(CHANGES_FIELDS.get(item['field'], item['field']))
        return data
    except json.JSONDecodeError:
        return []

@register.filter
def stringify(value):
    return str(value)



# @register.filter
# def progressify(value, full=30):
#     try:
#         ratio = int(100 * value / full)
#         return max(0, min(ratio, 100))
#     except: return 0