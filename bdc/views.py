import os, logging, json, random

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import datetime
from zoneinfo import ZoneInfo
# from uuid import UUID
from django.core.paginator import Paginator

from django.conf import settings

from django.contrib import messages
from django.utils.translation import gettext_lazy as trans

from django.db import models
from django.db.models import Count, Sum, Q
from urllib.parse import urlencode

# from decimal import Decimal

from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator
# from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control, never_cache

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, FileResponse, JsonResponse

from django.contrib.auth.models import User

# from nas.models import UserSetting
from bdc.models import PurchaseOrder
from base.models import Category, Client
from base.texter import normalize_text
from base.context_processors import portal_context


# Default Settings
TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = 10
# CLIENTS_ITEMS_PER_PAGE = 20
TENDERS_ORDERING_FIELD = 'deadline'
SHOW_TODAYS_EXPIRED = True
SHOW_CANCELLED = True
LINK_PREFIX = settings.LINK_PREFIX
RABAT_TZ = ZoneInfo('Africa/Casablanca')

DCE_SHOW_MODAL = True


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bdc_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us: 
        TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
        TENDERS_ORDERING_FIELD = us.tenders_ordering_field
        TENDERS_ITEMS_PER_PAGE = int(us.tenders_items_per_page)
        SHOW_TODAYS_EXPIRED = us.tenders_show_expired
        SHOW_CANCELLED = us.tenders_show_cancelled



    def get_req_params(req):
        allowed_keys = [
            'q', 'f', 'category', 'page', 'sort',
            'ddlnn', 'ddlnx', 'publn', 'publx', 
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        
        # if not 'ddlnn' in query_dict:
        #     query_dict['ddlnn'] = datetime.now(RABAT_TZ).date().strftime("%Y-%m-%d")
        
        if not 'sort' in query_dict:
            query_dict['sort'] = TENDERS_ORDERING_FIELD
            
        query_string = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != '' and k != 'page'
        }

        query_unsorted = {
            k: v for k, v in req.GET.items()
            if k in allowed_keys and v != '' and k not in ('page', 'sort')
        }

        return query_dict, query_string, query_unsorted

    def filter_bdcs(bdcs, params, user):
        
        def afas(queryset, field_names, phrase):
            phrase = normalize_text(phrase, False)
            words = [word.strip() for word in phrase.split() if word.strip()]
            if words:
                or_query = Q()
                for field in field_names:
                    field_q = Q()
                    for word in words:
                        field_q &= Q(**{f"{field}__icontains": word})
                    or_query |= field_q
                queryset = queryset.filter(or_query)

            return queryset
        ff = 0
        
        if not params or not user: return bdcs.distinct(), ff

        if 'q' in params:
            ff += 1
            q = params['q']
            if 'f' in params:
                match params['f']:
                    case 'client':
                        bdcs = afas(bdcs, ['cliwords'], q)
                    case 'location':
                        bdcs = afas(bdcs, ['locwords'], q)
                    case 'reference':
                        bdcs = afas(bdcs, ['refwords'], q)
                    case _:
                        bdcs = afas(bdcs, ['keywords'], q)
            else:
                bdcs = afas(bdcs, ['keywords', 'cliwords','locwords', 'refwords'], q)

        if 'ddlnn' in params:
            ddlnn = params['ddlnn']
            bdcs = bdcs.filter(deadline__gte=ddlnn)
            if ddlnn == datetime.now(RABAT_TZ).strftime("%Y-%m-%d"): 
                if not SHOW_TODAYS_EXPIRED:
                    bdcs = bdcs.exclude(deadline__lt=datetime.now(RABAT_TZ))
            else:
                ff += 1

        if 'ddlnx' in params:
            ff += 1
            ddlnx = params['ddlnx']
            bdcs = bdcs.filter(deadline__date__lte=ddlnx)

        if 'publn' in params:
            ff += 1
            publn = params['publn']
            bdcs = bdcs.filter(published__gte=publn)
        if 'publx' in params:
            ff += 1
            publx = params['publx']
            bdcs = bdcs.filter(published__lte=publx)
                
        if 'category' in params:
            ff += 1
            category = params['category']
            bdcs = bdcs.filter(category__id=category)

        return bdcs.distinct(), ff

    def define_context(request):
        context = {}

        all_categories = Category.objects.all()

        context['query_string']       = urlencode(query_string)
        context['query_unsorted']     = urlencode(query_unsorted)
        context['query_dict']         = query_dict

        # context['categories']         = all_categories
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)
    all_bdcs = PurchaseOrder.objects.all()
    # all_bdcs = all_bdcs.filter(
    #     deliberated__isnull=False, 
    #     winner_entity__isnull=False,
    #     unsuccessful=True
    #     )
    bdcs, filters = filter_bdcs(all_bdcs, query_dict, request.user)

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = [sort]
        if sort == 'published': ordering = ['-published']
        if sort == '-published': ordering = ['published']
    else: ordering = []

    ordering.append('id')

    query_dict['filters'] = filters

    bdcs = bdcs.order_by(
            *ordering
        ).select_related(
            'client', 'category'
        ).prefetch_related(
            'articles', 'attachements',
            )

    context = define_context(request)

    paginator = Paginator(bdcs, TENDERS_ITEMS_PER_PAGE)
    page_number = query_dict['page'] if 'page' in query_dict else 1
    if '.' in str(page_number) or ',' in str(page_number): 
        page_number = page_number.replace(',', '').replace('.', '')
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Purchase Orders List view")


    return render(request, 'bdc/bdc-list.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bdc_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    bdc = get_object_or_404(PurchaseOrder.objects.select_related(
                'client', 'category'
            ).prefetch_related(
                'articles', 'attachements'
            ), id=pk)

    if not bdc : return HttpResponse(status=404)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    full_bar_days = int(us.tenders_full_bar_days) if us.tenders_full_bar_days else TENDER_FULL_PROGRESS_DAYS
    context = { 
        'bdc'           : bdc,
        'full_bar_days' : full_bar_days,
        }

    logger = logging.getLogger('portal')
    logger.info(f"PurchaseOrder details view: {bdc.id}")

    return render(request, 'bdc/bdc-details.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_details_chrono(request, ch=None):

    user = request.user
    if not user or not user.is_authenticated :
        return HttpResponse(status=403)
    if not ch : return HttpResponse(status=404)

    tender = get_object_or_404(PurchaseOrder, chrono=ch)

    if not tender : return HttpResponse(status=404)
    
    return redirect('portal_tender_detail', tender.id)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_get_file(request, pk=None, fn=None):

    if request.method != 'GET': return HttpResponse(status=405)
    if pk == None or fn == None: return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    tender = get_object_or_404(PurchaseOrder, id=pk)
    if not tender : return HttpResponse(status=404)
    
    dce_dir = os.path.join(os.path.join(settings.DCE_MEDIA_ROOT, 'dce'), settings.DL_PATH_PREFIX + tender.chrono)
    file_path = os.path.join(os.path.join('dce', settings.DL_PATH_PREFIX + tender.chrono), fn)
    file_fp = os.path.join(dce_dir, fn)

    if os.path.exists(file_fp):
        file_size = os.path.getsize(file_fp)
        response = HttpResponse()
        response['Content-Type'] = 'application/octet-stream'
        response['X-Accel-Redirect'] = f'/dce/{file_path}'
        response['Content-Disposition'] = f'attachment; filename="{ fn }"'
        response['Content-Length'] = os.path.getsize(file_fp)
        Download.objects.create(
            tender=tender, 
            user=user, 
            size_read = tender.size_read, 
            size_bytes = file_size if file_size else tender.size_bytes, )

        logger = logging.getLogger('portal')
        logger.info(f"PurchaseOrder File Download: {tender.id} (={tender.size_bytes}B)")
        return response

    return HttpResponse(status=404)

