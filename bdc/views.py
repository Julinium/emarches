import os, logging, json, random

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.db.models.functions import Lower

from django.conf import settings

from django.contrib import messages
from django.utils.translation import gettext_lazy as trans

from django.db import models
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control, never_cache
from django.utils.decorators import method_decorator

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, FileResponse, JsonResponse

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
import tempfile

from django.contrib.auth.models import User

# from easy_pdf.views import PDFTemplateView

from bdc.models import PurchaseOrder
from base.models import Category, Client
from nas.models import Sticky
from bdc.models import PurchaseOrder
from base.texter import normalize_text
from base.context_processors import portal_context


BDC_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
BDC_ITEMS_PER_PAGE = 10
BDC_FIRST_ARTICLES = 10
CLIENTS_ITEMS_PER_PAGE = 20

BDC_ORDERING_FIELD = 'deadline'
SHOW_TODAYS_EXPIRED = True

RABAT_TZ = ZoneInfo('Africa/Casablanca')


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
        
        dates_set = set(['ddlnn', 'ddlnx', 'publn', 'publx', 'delin', 'delix'])
        if dates_set.isdisjoint(query_dict):
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
            bdcs = bdcs.filter(deliberated__date__gte=delin)
        if 'delix' in params:
            ff += 1
            delix = params['delix']
            bdcs = bdcs.filter(deliberated__date__lte=delix)

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
def bdc_favorite_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    # us = get_user_settings(request)
    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us: 
        BDC_FULL_PROGRESS_DAYS = int(us.p_orders_full_bar_days)
        BDC_ORDERING_FIELD = us.p_orders_ordering_field
        BDC_ITEMS_PER_PAGE = int(us.p_orders_items_per_page)
        # SHOW_TODAYS_EXPIRED = us.p_orders_show_expired

    sort = request.GET.get('sort', BDC_ORDERING_FIELD)
    page = request.GET.get('page', None)
    query_dict = {'sort': sort, 'page': page}
    query_string = {'sort': sort}
    query_unsorted = {}

    sort = request.GET.get('sort', BDC_ORDERING_FIELD)

    if sort and sort != '':
        ordering = [sort]
    else: ordering = []

    ordering.append('id')

    pontext = portal_context(request)
    pinned_ids = pontext.get('pinned_ids', None)

    bdcs = PurchaseOrder.objects.filter(
        id__in=pinned_ids
    )

    bdcs = bdcs.order_by(
            *ordering
        ).select_related(
            'client', 'category'
        ).prefetch_related(
            'stickies',
            )

    context = {}
    context['query_string']       = urlencode(query_string)
    context['query_unsorted']     = urlencode(query_unsorted)
    context['query_dict']         = query_dict
    context['full_bar_days']      = BDC_FULL_PROGRESS_DAYS

    paginator = Paginator(bdcs, BDC_ITEMS_PER_PAGE)
    page_number = query_dict['page'] if 'page' in query_dict else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Favorite PO's List view")

    return render(request, 'bdc/bdc-favorite-list.html', context)


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
    full_bar_days = int(us.p_orders_full_bar_days) if us.p_orders_full_bar_days else BDC_FULL_PROGRESS_DAYS
    first_articles = int(us.p_orders_first_articles) if us.p_orders_first_articles else BDC_FIRST_ARTICLES

    # all_articles = bdc.articles
    featured = bdc.articles.all()[:first_articles] #if 
    extra = bdc.articles.count() - first_articles
    ddl_classes = 'fw-bold'
    if bdc.days_to_go < full_bar_days / 5:
        ddl_classes += ' text-danger'
    if bdc.days_to_go >= full_bar_days:
        ddl_classes += ' text-success'

    pinned = bdc.stickies.filter(user=user).first()

    context = {
        'bdc'           : bdc,
        'full_bar_days' : full_bar_days,
        # 'empties'       : ['-', '--', '_', '__', '---', '/', '?', ' ', ''],
        'pinned'        : pinned,
        'featured'      : featured,
        'extra'         : extra,
        'ddl_classes'   : ddl_classes,
        }

    logger = logging.getLogger('portal')
    logger.info(f"PurchaseOrder details view: {bdc.id}")

    return render(request, 'bdc/bdc-details.html', context)


@login_required(login_url="account_login")
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bdc_items_pdf(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)
    
    bdc = get_object_or_404(PurchaseOrder.objects.select_related(
                'client', #'category'
            ).prefetch_related(
                'articles', #'attachements'
            ), id=pk)

    # if not bdc : return HttpResponse(status=404)
    crm = trans("Generated by ")

    context = {
        "crm": crm + ' ' + 'eMarches.com',
        "bdc": bdc,
    }

    html_string = render_to_string("bdc/bdc-articles-pdf.html", context)

    # Convert to PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf_bytes = html.write_pdf()

    # Return as download
    pdf_file_name = f'eMarches.com-{ bdc.chrono }.pdf'
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{ pdf_file_name }"'
    return response


# @method_decorator(login_required, name='dispatch')
# class ItemsPDFView(PDFTemplateView):
#     template_name = 'bdc/bdc-articles-pdf.html'

#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         try:
#             bdc = PurchaseOrder.objects.filter(id=self.kwargs['pk']).first()
#             context.update({
#                 'bdc': bdc,
#             })
#         except: pass

#         return context


def client_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us: 
        CLIENTS_ITEMS_PER_PAGE = int(us.general_items_per_page)
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
        if sort == '-bdcs_count': ordering = ['bdcs_count']
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


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bdc_stickies_add(request, pk=None):
    
    if request.method != 'POST': return HttpResponse(status=405)
    if pk == None : return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    purchase_order = get_object_or_404(PurchaseOrder, id=pk)
    if not purchase_order : return HttpResponse(status=404)

    logger = logging.getLogger('portal')

    sticked = Sticky.objects.filter(purchase_order=purchase_order, user=user).first()
    if not sticked:
        sticked = Sticky.objects.create(
            user=user,
            purchase_order=purchase_order,
        )
        logger.info(f"Purchase Order Favorited successfully: { purchase_order.id }")
        # messages.success(request, trans('Item successfully added to your Favorites'))

        return HttpResponse(purchase_order.id, status=200)
    logger.info(f"Failed to favorite Purchase Order: { purchase_order.id }")
    return HttpResponse(status=500)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bdc_stickies_remove(request, pk=None):

    if request.method != 'POST': return HttpResponse(status=405)
    if pk == None : return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    purchase_order = get_object_or_404(PurchaseOrder, id=pk)
    if not purchase_order : return HttpResponse(status=404)

    logger = logging.getLogger('portal')
    sticked = Sticky.objects.filter(purchase_order=purchase_order, user=user)

    deleted, _ = sticked.delete()
    if deleted > 0:
        logger.info(f"Purchase Order Unfavorited successfully: { purchase_order.id }")
        return HttpResponse(purchase_order.id, status=200)

    logger.info(f"Failed to unfavorite Purchase Order: { purchase_order.id }")
    return HttpResponse(status=500)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bdc_stickies_remove_all(request):

    if request.method != 'POST': return HttpResponse(status=405)

    user = request.user
    if not user or not user.is_authenticated :
        return HttpResponse(status=403)
    
    # perimeter = request.POST.get('perimeter', '') 
    data = json.loads(request.body)
    perimeter   = data.get('perimeter', 'all')

    # perimeters = ['expired', 'deliberated', 'awarded', 'unsuccessful', 'all']
    sticked = Sticky.objects.filter(user=user)
    if perimeter == 'expired':
        sticked = sticked.filter(purchase_order__deadline__lt=datetime.now(RABAT_TZ))
    elif perimeter == 'deliberated':
        sticked = sticked.filter(purchase_order__deliberated__isnull=False)
    elif perimeter == 'awarded':
        sticked = sticked.filter(purchase_order__winner_entity__isnull=False)
    elif perimeter == 'unsuccessful':
        sticked = sticked.filter(purchase_order__unsuccessful=True)
    elif perimeter == '':
        sticked = None
        
    count = sticked.count() if sticked else 0
    bla = f'perimeter = [{ perimeter }], count = [{ count }]'

    logger = logging.getLogger('portal')
    if count > 0:
        deleted, _ = sticked.delete()
        if deleted != count:
            logger.info(f"Failed to unfavorite Purchase Orders.")
            return HttpResponse(bla, status=500)
        logger.info(f"All Purchase Order Unfavorited successfully.")
    else:
        logger.info(f"Nothing to Unfavorite.")

    return HttpResponse(bla, status=200)


