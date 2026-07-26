import ast
import datetime
from decimal import Decimal

SAFE_GLOBALS = {
    'datetime': datetime,
    'Decimal': Decimal,
}

# CHANGES_FIELDS = {
#     'cancelled': _('Cancelled'),
#     'title': _('Tender Object'),
#     'reference':_('Reference'),
#     'published':_('Date Published'),
#     'deadline': _('Deadline'),
#     'estimate': _('Estimate'),
#     'bond': _('Guarantee'),
#     'size_bytes': _('Files bytes'),
#     'size_read': _('Files size'),
#     'contact_name': _('Contact name'),
#     'contact_phone': _('Contact phone'),
#     'contact_email': _('Contact email'),
#     'contact_fax': _('Contact fax'),

#     'address_opening': _('Opening Address'),
#     'address_bidding': _('Bidding Address'),
#     'address_withdrawal': _('Withdrawal Address'),
#     'esign': _('Electronic signature'),
#     'ebid': _('Electronic bidding'),
#     'location': _('Execution location'),
#     'variant': _('Variants'),
#     'reserved': _('Reserved'),
#     'plans_price': _('Plans price'),
#     'lots_count': _('Lots count'),
#     'lot': _('Lots'),
#     'link': _('Link'),
#     'acronym': _('Acronym'),
#     'chrono': _('Number'),
#     'category': _('Category'),
#     'mode': _('Mode'),
#     'procedure': _('Procedure'),
#     'client': _('Public client'),

#     'qualif': _('Qualifications'),
#     'agrement': _('Licenses'),
#     'meeting': _('Meetings'),
#     'sample': _('Samples'),
#     'visit': _('Visits'),

#     'domains': _('Domains'),
#     'qualifs': _('Qualifications'),
#     'agrements': _('Licenses'),
#     'meetings': _('Meetings'),
#     'samples': _('Samples'),
#     'visits': _('Visits'),
# }

def safe_eval_repr(expr_str):
    """
    Safely parses a string containing Python repr structures including
    datetime, timezone, and Decimal objects without arbitrary code execution.
    """
    if not expr_str:
        return []

    # Parse the string into an Abstract Syntax Tree (AST)
    parsed_tree = ast.parse(expr_str, mode='eval')

    # Ensure only literal types and explicit safe constructors exist in the string
    for node in ast.walk(parsed_tree):
        if isinstance(node, (ast.Call, ast.Attribute, ast.Name)):
            # Check if the function/object name is permitted
            name = ""
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                name = node.func.attr

            if name and name not in {'datetime', 'timezone', 'utc', 'Decimal', 'int', 'str', 'float'}:
                raise ValueError(f"Unsafe node detected in expression: {name}")

    # Compile and evaluate strictly against isolated safe globals/locals
    code = compile(parsed_tree, filename='<string>', mode='eval')
    return eval(code, {"__builtins__": None}, SAFE_GLOBALS)



def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for: return x_forwarded_for.split(",")[0].strip()
    else: return request.META.get("REMOTE_ADDR")