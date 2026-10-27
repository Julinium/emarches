import unicodedata
from bos.models import Bulletin, SearchLog
from django.contrib.postgres.search import SearchVector

def deaccentify(input_str):
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


def reindex():
    print("Re-indexing bulletins with french_unaccent...")
    bulletins = Bulletin.objects.filter(extracted_text__isnull = False).exclude(extracted_text="")
    count = bulletins.count()
    print(f"Started handling {count} bulletins ...")

    for i, b in enumerate(bulletins, 1):
        if i % 10 == 0:
            print(f"Processing items up to {i} from {count} ...")
        if b.extracted_text:
            b.search_vector = SearchVector('extracted_text', config='french_unaccent')
            b.save(update_fields=['search_vector'])

    print("Re-indexing complete!")


def loggify(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    search_log = SearchLog.objects.create(
        url=request.build_absolute_uri(),
        method=request.method,
        ip_address=ip,
        user_agent=request.headers.get('User-Agent', ''),
        query_params=request.GET.urlencode(),
        user=request.user if request.user.is_authenticated else None
    )

    return search_log