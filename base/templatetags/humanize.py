from django import template
# from django.urls import resolve, reverse
# from django.conf import settings
# from humanize import metric

register = template.Library()

@register.filter
def metrify(value, precision=2):
    if value is None or value == 0:
        return '0'
    try:
        num = int(value)
    except (ValueError, TypeError):
        return str(value)
    return metric(num, "", precision)#.replace(" ", '')



@register.filter
def progrefy(value, full_bar=30):
    if value is None or value == 0 or full_bar < 1:
        return 0
    tg = int(value)
    fb = int(full_bar)
    try:
        ratio = int(100 * tg / fb)
        progress = max(0, min(ratio, 100))
        return progress
    except: 
        return 0


def metric(value: float, unit: str = "", precision: int = 3) -> str:

    import math

    if not math.isfinite(value):
        return _format_not_finite(value)
    exponent = int(math.floor(math.log10(abs(value)))) if value != 0 else 0

    if exponent >= 33 or exponent < -30:
        return scientific(value, precision - 1) + unit

    value /= 10 ** (exponent // 3 * 3)
    if exponent >= 3:
        ordinal_ = "kMGTPEZYRQ"[exponent // 3 - 1]
    elif exponent < 0:
        ordinal_ = "mμnpfazyrq"[(-exponent - 1) // 3]
    else:
        ordinal_ = ""
    value_ = format(value, f".{int(max(0, precision - exponent % 3 - 1))}f")
    if not (unit or ordinal_) or unit in ("°", "′", "″"):
        space = ""
    else:
        space = " "

    return f"{value_}{ordinal_}{unit}"