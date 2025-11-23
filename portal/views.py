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

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control, never_cache

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, FileResponse, JsonResponse

from django.contrib.auth.models import User

from nas.models import UserSetting, Download, TenderView, Favorite, Company, Folder
from base.models import Tender, Category, Client, Lot, Procedure, Crawler, Agrement, Qualif
from base.texter import normalize_text
from base.context_processors import portal_context


# Default Settings
TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = 10
CLIENTS_ITEMS_PER_PAGE = 20
TENDERS_ORDERING_FIELD = 'deadline'
SHOW_TODAYS_EXPIRED = True
SHOW_CANCELLED = True
LINK_PREFIX = settings.LINK_PREFIX
RABAT_TZ = ZoneInfo('Africa/Casablanca')

DCE_SHOW_MODAL = True


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    us = get_user_settings(request)
    if us: 
        TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
        TENDERS_ORDERING_FIELD = us.tenders_ordering_field
        TENDERS_ITEMS_PER_PAGE = int(us.tenders_items_per_page)
        SHOW_TODAYS_EXPIRED = us.tenders_show_expired
        SHOW_CANCELLED = us.tenders_show_cancelled



    def get_req_params(req):
        allowed_keys = [
            'q', 'f', 'estin', 'estix', 'bondn', 'bondx', 
            'ddlnn', 'ddlnx', 'publn', 'publx', 'allotted',
            'category', 'procedure', 'ebid', 'esign', 
            'pme', 'variant', 'agrements', 'qualifs',
            'samples', 'meetings', 'visits', 'page', 'sort',
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        
        if not 'ddlnn' in query_dict:
            query_dict['ddlnn'] = datetime.now(RABAT_TZ).date().strftime("%Y-%m-%d")
        
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

    def filter_tenders(tenders, params, user):
        
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
        
        if not params or not user: return tenders.distinct(), ff

        if not SHOW_CANCELLED:
            tenders = tenders.filter(cancelled=False)

        if 'q' in params:
            ff += 1
            q = params['q']
            if 'f' in params:
                match params['f']:
                    case 'client':
                        tenders = afas(tenders, ['cliwords'], q)
                    case 'location':
                        tenders = afas(tenders, ['locwords'], q)
                    case 'reference':
                        tenders = afas(tenders, ['refwords'], q)
                    case _:
                        tenders = afas(tenders, ['keywords'], q)
            else:
                tenders = afas(tenders, ['keywords', 'cliwords','locwords', 'refwords'], q)                

        if 'estin' in params:
            ff += 1
            estin = params['estin']
            tenders = tenders.filter(estimate__gte=estin)
        if 'estix' in params:
            ff += 1
            estix = params['estix']
            tenders = tenders.filter(estimate__lte=estix)

        if 'bondn' in params:
            ff += 1
            bondn = params['bondn']
            tenders = tenders.filter(bond__gte=bondn)
        if 'bondx' in params:
            ff += 1
            bondx = params['bondx']
            tenders = tenders.filter(bond__lte=bondx)

        if 'ddlnn' in params:
            ddlnn = params['ddlnn']
            tenders = tenders.filter(deadline__gte=ddlnn)
            if ddlnn == datetime.now(RABAT_TZ).strftime("%Y-%m-%d"): 
                if not SHOW_TODAYS_EXPIRED:
                    tenders = tenders.exclude(deadline__lt=datetime.now(RABAT_TZ))
            else:
                ff += 1

        if 'ddlnx' in params:
            ff += 1
            ddlnx = params['ddlnx']
            tenders = tenders.filter(deadline__date__lte=ddlnx)

        if 'publn' in params:
            ff += 1
            publn = params['publn']
            tenders = tenders.filter(published__gte=publn)
        if 'publx' in params:
            ff += 1
            publx = params['publx']
            tenders = tenders.filter(published__lte=publx)
        
        if 'allotted' in params:
            ff += 1
            allotted = params['allotted']
            if allotted == 'single': tenders = tenders.filter(lots_count=1)
            if allotted == 'multi': tenders = tenders.filter(lots_count__gt=1)
        
        if 'pme' in params:
            ff += 1
            pme = params['pme']
            if pme == 'reserved': tenders = tenders.filter(reserved=True)
            if pme == 'open': tenders = tenders.filter(reserved=False)
        
        if 'category' in params:
            ff += 1
            category = params['category']
            tenders = tenders.filter(category__id=category)

        if 'procedure' in params:
            ff += 1
            procedure = params['procedure']
            tenders = tenders.filter(procedure__id=procedure)

        if 'ebid' in params:
            ff += 1
            ebid = params['ebid']
            if ebid == 'required': tenders = tenders.filter(ebid=1)
            if ebid == 'optional': tenders = tenders.filter(ebid=0)
            if ebid == 'na': tenders = tenders.exclude(ebid=0).exclude(ebid=1)

        if 'variant' in params:
            ff += 1
            variant = params['variant']
            if variant == 'accepted': tenders = tenders.filter(variant=True)
            if variant == 'rejected': tenders = tenders.filter(variant=False)

        if 'samples' in params:
            ff += 1
            samples = params['samples']
            if samples == 'required': tenders = tenders.filter(has_samples=True)
            if samples == 'na': tenders = tenders.filter(has_samples=False)

        if 'meetings' in params:
            ff += 1
            meetings = params['meetings']
            if meetings == 'required': tenders = tenders.filter(has_meetings=True)
            if meetings == 'na': tenders = tenders.filter(has_meetings=False)

        if 'visits' in params:
            ff += 1
            visits = params['visits']
            if visits == 'required': tenders = tenders.filter(has_visits=True)
            if visits == 'na': tenders = tenders.filter(has_visits=False)

        if 'agrements' in params:
            ff += 1
            agrements = params['agrements']
            if agrements == 'required': tenders = tenders.filter(has_agrements=True)
            if agrements == 'na': tenders = tenders.filter(has_agrements=False)
            if agrements == 'companies':
                if user.is_authenticated:
                    user_agrements = Agrement.objects.filter(companies__user=user)
                    tenders = tenders.filter(lots__agrements__in=user_agrements)

        if 'qualifs' in params:
            ff += 1
            qualifs = params['qualifs']
            if qualifs == 'required': tenders = tenders.filter(has_qualifs=True)
            if qualifs == 'na': tenders = tenders.filter(has_qualifs=False)
            if qualifs == 'companies':
                if user.is_authenticated:
                    user_qualifs = Qualif.objects.filter(companies__user=user)
                    tenders = tenders.filter(lots__qualifs__in=user_qualifs)

        return tenders.distinct(), ff

    def define_context(request):
        context = {}

        all_categories = Category.objects.all()
        all_procedures = Procedure.objects.all()

        last_crawler = Crawler.objects.filter(saving_errors=False, import_links=False).order_by('finished').last()
        last_updated = last_crawler.finished if last_crawler else None

        context['query_string']       = urlencode(query_string)
        context['query_unsorted']     = urlencode(query_unsorted)
        context['query_dict']         = query_dict

        # context['categories']         = all_categories
        context['procedures']         = all_procedures
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS
        context['last_updated']       = last_updated

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)
    all_tenders = Tender.objects.all()
    tenders, filters = filter_tenders(all_tenders, query_dict, request.user)

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = [sort]
        if sort == 'published': ordering = ['-published']
        if sort == '-published': ordering = ['published']
    else: ordering = []

    ordering.append('id')

    query_dict['filters'] = filters

    tenders = tenders.order_by(
            *ordering
        ).select_related(
            'client', 'category', 'mode', 'procedure'
        ).prefetch_related(
            'favorites', 'views',
            'downloads', 'comments', 'changes',
            )

    context = define_context(request)

    paginator = Paginator(tenders, TENDERS_ITEMS_PER_PAGE)
    page_number = query_dict['page'] if 'page' in query_dict else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj
    # context['faved_ids'] = user.favorites.values_list('tender', flat=True)

    logger = logging.getLogger('portal')
    logger.info(f"Tender List view")


    return render(request, 'portal/tender-list.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_details_chrono(request, ch=None):

    user = request.user
    if not user or not user.is_authenticated :
        return HttpResponse(status=403)
    if not ch : return HttpResponse(status=404)

    tender = get_object_or_404(Tender, chrono=ch)

    if not tender : return HttpResponse(status=404)
    
    return redirect('portal_tender_detail', tender.id)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    tender = get_object_or_404(Tender.objects.select_related(
                'client', 'category', 'mode', 'procedure'
            ).prefetch_related(
                'downloads', 'views', 'favorites',
                'domains', 'lots', 'lots__agrements', 'lots__qualifs',
                'lots__meetings', 'lots__samples', 'lots__visits'
            ), id=pk)

    if not tender : return HttpResponse(status=404)

    files_list = []
    total_size = 0
    dce_dir = os.path.join(
        os.path.join(settings.DCE_MEDIA_ROOT, 'dce'), 
        settings.DL_PATH_PREFIX + tender.chrono
        )
    if os.path.exists(dce_dir): files_list = os.listdir(dce_dir)

    files_info = []
    if len(files_list) > 0:
        for entry in files_list:
            full_path = os.path.join(dce_dir, entry)
            if os.path.exists(full_path):
                if os.path.isfile(full_path):
                    sizens = os.path.getsize(full_path)
                    total_size += sizens
                    files_info.append({"name": entry, "size": sizens})
        
    files_count = len(files_info)
    if tender.address_withdrawal == tender.address_bidding and \
        tender.address_withdrawal == tender.address_opening:
        addresses = [tender.address_withdrawal]
    else:
        addresses = [tender.address_withdrawal, tender.address_bidding, tender.address_opening]

    favorited = tender.favorites.filter(user=user).first()
    # form = FavoriteForm(user=user, tender=tender, instance=favorited)

    us = get_user_settings(request)
    full_bar_days = int(us.tenders_full_bar_days) if us.tenders_full_bar_days else TENDER_FULL_PROGRESS_DAYS
    context = { 
        'tender'        : tender,
        'link_prefix'   : LINK_PREFIX,
        'total_size'    : total_size,
        'files_info'    : files_info,
        'dce_modal'     : DCE_SHOW_MODAL,
        'addresses'     : addresses,
        'full_bar_days' : full_bar_days,
        'favorited'     : favorited,
        }
    
    TenderView.objects.create(
        tender=tender, 
        user=user, )

    logger = logging.getLogger('portal')
    logger.info(f"Tender details view: {tender.id}")

    tolerance_dn = 20.0
    tolerance_up = 20.0    
    offers_count = 1
    
    context['offer_litteral'] = trans('OFFER')
    context['offers_count'] = max(offers_count, 1)
    context['tolerance_dn'] = tolerance_dn
    context['tolerance_up'] = tolerance_up

    return render(request, 'portal/tender-details.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_get_file(request, pk=None, fn=None):

    if request.method != 'GET': return HttpResponse(status=405)
    if pk == None or fn == None: return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    tender = get_object_or_404(Tender, id=pk)
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
        logger.info(f"Tender File Download: {tender.id} (={tender.size_bytes}B)")
        return response

    return HttpResponse(status=404)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_favorite(request, pk=None):
    
    if request.method != 'POST': return HttpResponse(status=405)
    if pk == None : return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    tender = get_object_or_404(Tender, id=pk)
    if not tender : return HttpResponse(status=404)

    logger = logging.getLogger('portal')

    favorited = Favorite.objects.filter(tender=tender, user=user).first()
    if not favorited:
        favorited = Favorite.objects.create(
            user=user,
            tender=tender,
        )
        logger.info(f"Tender Favorite: { tender.id }")
        # messages.success(request, trans('Item successfully added to your Favorites'))

        return HttpResponse(tender.id, status=200)
    logger.info(f"Failed Tender Favorite: { tender.id }")
    return HttpResponse(status=500)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_unfavorite(request, pk=None):

    if request.method != 'POST': return HttpResponse(status=405)
    if pk == None : return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    tender = get_object_or_404(Tender, id=pk)
    if not tender : return HttpResponse(status=404)

    logger = logging.getLogger('portal')

    deleted, _ = Favorite.objects.filter(tender=tender, user=user).delete()
    if deleted > 0:
        logger.info(f"Tender Unfavorite: { tender.id }")
        # messages.success(request, trans('Item successfully removed from your Favorites'))
        return HttpResponse(tender.id, status=200)

    logger.info(f"Failed Tender Unfavorite: { tender.id }")
    return HttpResponse(status=500)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_favorite_clean(request, span=None):
    
    if request.method != 'POST': return HttpResponse(status=405)
    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    cleanables = None
    if span:
        if span == 'all':
            cleanables = user.favorites.all()
        if span == 'cancelled':
            cleanables = user.favorites.filter(tender__cancelled=True)
        if span == 'expired':
            wassa = datetime.now(RABAT_TZ)
            cleanables = user.favorites.filter(tender__deadline__lt=wassa)
    
    logger = logging.getLogger('portal')
    if cleanables:
        trash, xxx = cleanables.delete()
        logger.info(f"Favorite Tender Cleanup: { span } => { trash } items")
        messages.success(request, trans('Favorite items cleaned') + f': { trash }')
    else:
        logger.info(f"Favorite Tender Cleanup: { span } => No items cleaned up")
        messages.warning(request, trans('Nothing to clean up.'))

    return redirect('portal_tender_favorite_list')

    # return render(request, 'portal/tender-favorite-list.html', {})


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_favorite_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    us = get_user_settings(request)
    if us:
        TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
        TENDERS_ORDERING_FIELD = us.tenders_ordering_field
        TENDERS_ITEMS_PER_PAGE = int(us.tenders_items_per_page)
        SHOW_TODAYS_EXPIRED = us.tenders_show_expired
        SHOW_CANCELLED = us.tenders_show_cancelled

    sort = request.GET.get('sort', TENDERS_ORDERING_FIELD)
    page = request.GET.get('page', None)
    query_dict = {'sort': sort, 'page': page}
    query_string = {'sort': sort}
    query_unsorted = {}

    sort = request.GET.get('sort', TENDERS_ORDERING_FIELD)

    if sort and sort != '':
        ordering = [sort]
    else: ordering = []

    ordering.append('id')

    # faved_ids = user.favorites.values_list('tender', flat=True)

    pontext = portal_context(request)
    faved_ids = pontext.get('faved_ids', None)

    tenders = Tender.objects.filter(
        id__in=faved_ids
    )

    tenders = tenders.order_by(
            *ordering
        ).select_related(
            'client', 'category', 'mode', 'procedure'
        ).prefetch_related(
            'favorites', 'views',
            'downloads', 'comments', 'changes',
            )

    context = {}
    context['query_string']       = urlencode(query_string)
    context['query_unsorted']     = urlencode(query_unsorted)
    context['query_dict']         = query_dict
    context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS

    paginator = Paginator(tenders, TENDERS_ITEMS_PER_PAGE)
    page_number = query_dict['page'] if 'page' in query_dict else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Favorite Tender List view")

    return render(request, 'portal/tender-favorite-list.html', context)


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
    logger.info(f"Locations List view")
    
    return render(request, 'portal/locations-list.html', context)


def clients_list(request):

    us = get_user_settings(request)
    if us: 
        CLIENTS_ITEMS_PER_PAGE = int(us.tenders_items_per_page)
        SHOW_TODAYS_EXPIRED = us.tenders_show_expired
        SHOW_CANCELLED = us.tenders_show_cancelled

    assa = timezone.now()
    clients = Client.objects.annotate(
        tenders_count=Count('tenders', filter=Q(
            tenders__deadline__gte=assa, 
            tenders__cancelled=False)),
        total_estimate=Sum('tenders__estimate', filter=Q(
            tenders__deadline__gte=assa, 
            tenders__cancelled=False))
    ).filter(tenders_count__gt=0).order_by('-tenders_count', 'name')

    context = {}

    # context['clients'] = clients

    paginator = Paginator(clients, CLIENTS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Clients List view")

    return render(request, 'portal/clients-list.html', context)

def get_user_settings(request):
    return UserSetting.objects.filter(user = request.user).first()


