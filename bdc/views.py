import os, logging, json, random

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# from uuid import UUID
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.db.models.functions import Lower

from django.conf import settings

from django.contrib import messages
from django.utils.translation import gettext_lazy as trans

from django.db import models
from urllib.parse import urlencode

# from decimal import Decimal

from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator
# from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control, never_cache

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, FileResponse, JsonResponse

from django.contrib.auth.models import User

from bdc.models import PurchaseOrder
from base.models import Category, Client
from base.texter import normalize_text
from base.context_processors import portal_context


BDC_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
BDC_ITEMS_PER_PAGE = 10
WRAP_LONG_TEXT = True
CLIENTS_ITEMS_PER_PAGE = 20

BDC_ORDERING_FIELD = 'deadline'
SHOW_TODAYS_EXPIRED = True
# SHOW_CANCELLED = True
# LINK_PREFIX = settings.LINK_PREFIX
RABAT_TZ = ZoneInfo('Africa/Casablanca')

# DCE_SHOW_MODAL = True
# DEADLINE_BACK_DAYS = 1

@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bdc_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us: 
        BDC_FULL_PROGRESS_DAYS = int(us.p_orders_full_bar_days)
        BDC_ORDERING_FIELD = us.p_orders_ordering_field
        BDC_ITEMS_PER_PAGE = int(us.p_orders_items_per_page)
        SHOW_TODAYS_EXPIRED = us.p_orders_show_expired
        WRAP_LONG_TEXT = us.general_wrap_long_text
        # SHOW_CANCELLED = us.tenders_show_cancelled



    # p_orders_items_per_page = models.CharField(max_length=10, choices=ItemsPerPage.choices, default=ItemsPerPage.IPP_010, verbose_name=_('P. Orders: Items per page'))


    def get_req_params(req):
        allowed_keys = [
            'q', 'f', 'category', 'page', 'sort',
            'ddlnn', 'ddlnx', 'publn', 'publx', 'winners',
            'delin', 'delix', 'amoun', 'amoux', 'results', 
            'exact',
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        
        if not 'sort' in query_dict:
            query_dict['sort'] = BDC_ORDERING_FIELD
        
        if not 'ddlnn' in query_dict:
            query_dict['ddlnn'] = datetime.now(RABAT_TZ).strftime("%Y-%m-%d")
            
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
                        if 'exact' in params and params['exact'] == '1':
                            bdcs = bdcs.filter(client__name__exact=q)
                        else:
                            bdcs = afas(bdcs, ['cliwords'], q)
                        # bdcs = afas(bdcs, ['cliwords'], q)
                    case 'location':
                        bdcs = afas(bdcs, ['locwords'], q)
                    case 'reference':
                        bdcs = afas(bdcs, ['refwords'], q)
                    case 'winners':
                        bdcs = afas(bdcs, ['winner_entity'], q)
                    case 'articles':
                        bdcs = afas(bdcs, ['articles__title', 'articles__specifications', 'articles__warranties'], q)
                    case _:
                        bdcs = afas(bdcs, ['keywords'], q)
            else:
                bdcs = afas(bdcs, [
                    'keywords', 'cliwords','locwords', 'refwords', 'winner_entity', 
                    'articles__title', 'articles__specifications', 'articles__warranties'
                    ], q)

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

        if 'delin' in params:
            ff += 1
            delin = params['delin']
            bdcs = bdcs.filter(deliberated__gte=delin)
        if 'delix' in params:
            ff += 1
            delix = params['delix']
            bdcs = bdcs.filter(deliberated__lte=delix)

        if 'amoun' in params:
            ff += 1
            amoun = params['amoun']
            bdcs = bdcs.filter(winner_amount__gte=amoun)
        if 'amoux' in params:
            ff += 1
            amoux = params['amoux']
            bdcs = bdcs.filter(winner_amount__lte=amoux)
                
        if 'category' in params:
            ff += 1
            category = params['category']
            bdcs = bdcs.filter(category__id=category)
        
        if 'results' in params:
            ff += 1
            results = params['results']
            match results:
                case 'no':
                    bdcs = bdcs.filter(deliberated__isnull=True)
                case 'deliberated':
                    bdcs = bdcs.filter(deliberated__isnull=False)
                case 'awarded':
                    bdcs = bdcs.filter(winner_entity__isnull=False)
                case 'unsuccessful':
                    bdcs = bdcs.filter(unsuccessful=True)
                # case 'articles':
                #     bdcs = afas(bdcs, ['articles__title', 'articles__specifications', 'articles__warranties'], q)
                # case _:
                #     bdcs = afas(bdcs, ['keywords'], q)

        return bdcs.distinct(), ff

    def define_context(request):
        context = {}

        context['query_string']       = urlencode(query_string)
        context['query_unsorted']     = urlencode(query_unsorted)
        context['query_dict']         = query_dict

        context['full_bar_days']      = BDC_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    all_bdcs = PurchaseOrder.objects.all()
    bdcs, filters = filter_bdcs(all_bdcs, query_dict, request.user)

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = [sort]
        if sort == 'published': ordering = ['-published']
        if sort == '-published': ordering = ['published']
    else: ordering = []

    ordering.append('-created')

    query_dict['filters'] = filters

    bdcs = bdcs.order_by(
            *ordering
        ).select_related(
            'client', 'category'
        ).prefetch_related(
            'articles', 'attachements',
            )

    context = define_context(request)

    paginator = Paginator(bdcs, BDC_ITEMS_PER_PAGE)
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
    
    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us:
        WRAP_LONG_TEXT = us.general_wrap_long_text

    bdc = get_object_or_404(PurchaseOrder.objects.select_related(
                'client', 'category'
            ).prefetch_related(
                'articles', 'attachements'
            ), id=pk)

    if not bdc : return HttpResponse(status=404)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    full_bar_days = int(us.tenders_full_bar_days) if us.tenders_full_bar_days else BDC_FULL_PROGRESS_DAYS
    
    empties = ['', '-', '---', '/']
    
    context = { 
        'bdc'           : bdc,
        'full_bar_days' : full_bar_days,
        'empties'       : empties,
        }

    logger = logging.getLogger('portal')
    logger.info(f"PurchaseOrder details view: {bdc.id}")

    return render(request, 'bdc/bdc-details.html', context)


def client_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us: 
        CLIENTS_ITEMS_PER_PAGE = int(us.general_items_per_page)
        WRAP_LONG_TEXT = us.general_wrap_long_text
    CLIENTS_ORDERING_FIELD = 'name'

    def get_req_params(req):
        allowed_keys = [
            'q', 'page', 'sort',
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        if not 'sort' in query_dict:
            query_dict['sort'] = CLIENTS_ORDERING_FIELD
            
        query_string = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != '' and k != 'page'
        }

        query_unsorted = {
            k: v for k, v in req.GET.items()
            if k in allowed_keys and v != '' and k not in ('page', 'sort')
        }

        return query_dict, query_string, query_unsorted

    def filter_clients(clients, params):
        ff = 0
        if not params : return clients.distinct(), ff

        if 'q' in params:
            ff += 1
            q = params['q']
            clients = clients.filter(name__icontains=q)

        return clients.distinct(), ff

    def define_context(request):
        context = {}
        context['query_string']       = urlencode(query_string)
        context['query_unsorted']     = urlencode(query_unsorted)
        context['query_dict']         = query_dict

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)
    
    assa = timezone.now()
    all_clients = Client.objects.annotate(
        bdcs_count=Count('purchase_orders', filter=Q(
            purchase_orders__deadline__gte=assa))
    ).filter(bdcs_count__gt=0)

    clients, filters = filter_clients(all_clients, query_dict)

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = [sort]
        if sort == 'bdcs_count': ordering = ['-bdcs_count']
        if sort == '-bdcs_count': ordering = ['tenders_count']
    else: ordering = []

    # ordering.append('-created')

    query_dict['filters'] = filters


    if ordering == ['name']:
        clients = clients.annotate(name_lower=Lower('name')).order_by('name_lower')
    elif ordering == ['-name']:
        clients = clients.annotate(name_lower=Lower('name')).order_by('-name_lower')
    else: 
        clients = clients.order_by(*ordering)

    context = define_context(request)

    paginator = Paginator(clients, CLIENTS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj
    context['clients'] = clients

    logger = logging.getLogger('portal')
    logger.info(f"PO's Clients List view")

    return render(request, 'bdc/clients-list.html', context)


def locations_list(request):
    json_path = os.path.join(settings.BASE_DIR, 'scraper', 'data', 'regions-cities.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            states = json.load(f)
    except FileNotFoundError:
        states = [] 
        return HttpResponse('File Not Found Error', code=404)
        # Or raise a 404 / show error page
    except json.JSONDecodeError:
        states = []
        return HttpResponse('JSON Decode Error', code=405)
        # Handle corrupted JSON

    context = {
        'states': states
    }

    logger = logging.getLogger('portal')
    logger.info(f"PO's Locations List view")
    
    return render(request, 'bdc/locations-list.html', context)


# @login_required(login_url="account_login")
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
# def tender_details_chrono(request, ch=None):

#     user = request.user
#     if not user or not user.is_authenticated :
#         return HttpResponse(status=403)
#     if not ch : return HttpResponse(status=404)

#     tender = get_object_or_404(PurchaseOrder, chrono=ch)

#     if not tender : return HttpResponse(status=404)
    
#     return redirect('portal_tender_detail', tender.id)


# @login_required(login_url="account_login")
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
# def tender_get_file(request, pk=None, fn=None):

#     if request.method != 'GET': return HttpResponse(status=405)
#     if pk == None or fn == None: return HttpResponse(status=404)

#     user = request.user
#     if not user or not user.is_authenticated : 
#         return HttpResponse(status=403)

#     tender = get_object_or_404(PurchaseOrder, id=pk)
#     if not tender : return HttpResponse(status=404)
    
#     dce_dir = os.path.join(os.path.join(settings.DCE_MEDIA_ROOT, 'dce'), settings.DL_PATH_PREFIX + tender.chrono)
#     file_path = os.path.join(os.path.join('dce', settings.DL_PATH_PREFIX + tender.chrono), fn)
#     file_fp = os.path.join(dce_dir, fn)

#     if os.path.exists(file_fp):
#         file_size = os.path.getsize(file_fp)
#         response = HttpResponse()
#         response['Content-Type'] = 'application/octet-stream'
#         response['X-Accel-Redirect'] = f'/dce/{file_path}'
#         response['Content-Disposition'] = f'attachment; filename="{ fn }"'
#         response['Content-Length'] = os.path.getsize(file_fp)
#         Download.objects.create(
#             tender=tender, 
#             user=user, 
#             size_read = tender.size_read, 
#             size_bytes = file_size if file_size else tender.size_bytes, )

#         logger = logging.getLogger('portal')
#         logger.info(f"PurchaseOrder File Download: {tender.id} (={tender.size_bytes}B)")
#         return response

#     return HttpResponse(status=404)

