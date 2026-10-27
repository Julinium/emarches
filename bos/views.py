import io
import json
from datetime import datetime, date, timedelta
import requests
from django.shortcuts import render, redirect
from django.db.models import Q, Value, FloatField
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.http import HttpResponse

from .models import Bulletin, SearchLog, DownloadLog

from .helper import deaccentify, loggify
max_date_range = 365 * 5
results_limit = 50

def search(request):
    query = request.GET.get('q', '').strip()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    
    if not request.GET:
        exact_search = True
    else:
        exact_search = 'exact' in request.GET
    
    today = date.today()
    results = []
    
    # Parse incoming date strings safely
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
    except ValueError:
        start_date = None

    try:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
    except ValueError:
        end_date = None

    # Apply custom date range logic if any bound is missing
    if not start_date and not end_date:
        end_date = today
        start_date = end_date - timedelta(days=max_date_range)
    elif start_date and not end_date:
        one_year_later = start_date + timedelta(days=max_date_range)
        end_date = min(one_year_later, today)
    elif not start_date and end_date:
        start_date = end_date - timedelta(days=max_date_range)

    # Base queryset with date range filters applied
    bulletins = Bulletin.objects.filter(bo_date__gte=start_date, bo_date__lte=end_date)
    
    truncated = False

    # Process search query if provided
    normalized_query = deaccentify(query)
    
    if query and len(query) >= 3:
        search_query = SearchQuery(normalized_query, search_type='websearch', config='french_unaccent')
        num_matches = bulletins.filter(bo_num__icontains=normalized_query
            ).annotate(
                rank=Value(3.0, output_field=FloatField())
            ).order_by('-rank', '-bo_date')

        filter_matches = bulletins.filter(
                extracted_text__icontains=normalized_query
            ).annotate(
                rank=Value(2.0, output_field=FloatField())
            ).order_by('-rank', '-bo_date')
        
        vector_matches = bulletins.filter(
                search_vector=search_query
            ).annotate(
                rank=SearchRank('search_vector', search_query)
            ).order_by('-rank', '-bo_date')

        text_matches = filter_matches if exact_search else vector_matches

        db_matches = num_matches
        db_matches |= text_matches

        if len(db_matches) > results_limit:
            db_matches = db_matches[:results_limit]
            truncated = True
            
        for b in db_matches:
            results.append({
                "bo_pk": b.pk,
                "bo_num": b.bo_num,
                "date": b.bo_date,
                "rank": b.rank,
                "url": b.bo_url
            })

    elif not query:
        db_matches = bulletins.order_by('-bo_date')
        if len(db_matches) > results_limit:
            db_matches = db_matches[:results_limit]
            truncated = True

        for b in db_matches:
            results.append({
                "bo_pk": b.pk,
                "bo_num": b.bo_num,
                "date": b.bo_date,
                "rank": 0,
                "url": b.bo_url
            })


    try: 
        search_log = loggify(request)
        search_log.search_query = query
        search_log.date_fm = start_date_str
        search_log.date_to = end_date_str
        search_log.results_count = len(db_matches)
        search_log.truncated = truncated
        search_log.exact_check = exact_search

        search_log.save()
    except Exception as xc:
        print(xc)
    

    return render(request, 'bos/search.html', {
        'results': results, 
        'query': query,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'truncated': truncated,
        'exact_checked': exact_search,
    })


def home(request):
    return render(request, "bos/home.html")


def log_pdf_download(request, pk=None):
    if not pk : return HttpResponse(404)
    bo = Bulletin.objects.filter(id=pk).first()
    if not bo : return HttpResponse(404)
    target_url = bo.bo_url
    bo_numero = bo.bo_num

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    DownloadLog.objects.create(
        url=target_url,
        numero=bo_numero,
        ip_address=ip,
        user_agent=request.headers.get('User-Agent', '')
    )

    return redirect(target_url)