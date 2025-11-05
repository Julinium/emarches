import os, logging, json

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import UUID
from django.core.paginator import Paginator

from django.conf import settings

from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from django.db import models
from django.db.models import Q
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.cache import cache_control, never_cache

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, FileResponse, JsonResponse

from django.contrib.auth.models import User

from nas.models import UserSetting, Download, TenderView, Favorite, Company, Folder
from base.models import Tender, Category, Procedure, Crawler, Agrement, Qualif
from base.texter import normalize_text
from nas.forms import FavoriteForm
from portal.bs_icons import bicons

# Default Settings
TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = 10
TENDERS_ORDERING_FIELD = 'deadline'
SHOW_TODAYS_EXPIRED = True
SHOW_CANCELLED = True
LINK_PREFIX = settings.LINK_PREFIX
RABAT_TZ = ZoneInfo('Africa/Casablanca')

DCE_SHOW_MODAL = False

@login_required(login_url="account_login")
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

        query_dict = {
            k: v for k, v in req.GET.items() if v != ''
        }
        
        if not 'ddlnn' in query_dict:
            query_dict['ddlnn'] = datetime.now(RABAT_TZ).date().strftime("%Y-%m-%d")
        
        if not 'sort' in query_dict:
            query_dict['sort'] = TENDERS_ORDERING_FIELD
            
        query_string = {
            k: v for k, v in req.GET.items() if v != '' and k != 'page'
        }

        query_unsorted = {
            k: v for k, v in req.GET.items()
            if v != '' and k not in ('page', 'sort')
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

        context['categories']         = all_categories
        context['procedures']         = all_procedures
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS
        context['last_updated']       = last_updated

        # context['sorter']             = self.sorter
        context['bicons']             = bicons

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)
    all_tenders = Tender.objects.all()
    tenders, filters = filter_tenders(all_tenders, query_dict, request.user)

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = [sort]
        # if sort == 'published': ordering = ['-published']
        # if sort == '-published': ordering = ['published']
    else: ordering = []

    ordering.append('id')

    query_dict['filters'] = filters

    tenders = tenders.order_by(
            *ordering
        ).select_related(
            'client', 'category', 'mode', 'procedure'
        ).prefetch_related(
            'favorites', 'downloads', 'comments', 'changes',
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

    logger = logging.getLogger('portal')
    logger.info(f"Tender List view")


    return render(request, 'portal/tender-list.html', context)


@login_required(login_url="account_login")
def tender_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    tender = get_object_or_404(Tender.objects.select_related(
                'client', 'category', 'mode', 'procedure'
            ).prefetch_related(
                'downloads',
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

    us = get_user_settings(request)
    full_bar_days = int(us.tenders_full_bar_days) if us.tenders_full_bar_days else TENDER_FULL_PROGRESS_DAYS
    context = { 
        'tender'        : tender,
        'link_prefix'   : LINK_PREFIX,
        'bicons'        : bicons,
        'total_size'    : total_size,
        'files_info'    : files_info,
        'dce_modal'     : DCE_SHOW_MODAL,
        'addresses'     : addresses,
        'full_bar_days' : full_bar_days,
        }
    
    TenderView.objects.create(
        tender=tender, 
        user=user, )

    logger = logging.getLogger('portal')
    logger.info(f"Tender details view: {tender.id}")

    return render(request, 'portal/tender-details.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_get_file(request, pk=None, fn=None):

    if request.method != 'GET': return HttpResponse(status=403)
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
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
def favorite_toggle(request, pk=None):
    
    if request.method != 'GET': return HttpResponse(status=403)
    if pk == None : return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    tender = get_object_or_404(Tender, id=pk)
    if not tender : return HttpResponse(status=404)
    tender = get_object_or_404(Tender, pk=pk)
    user = request.user

    action = request.POST.get('action')

    logger = logging.getLogger('portal')
    # ------------------- REMOVE -------------------
    if action == 'remove':
        deleted, _ = Favorite.objects.filter(user=user, tender=tender).delete()
        logger.info(f"Tender UnFavorite: { tender.id }")
        return JsonResponse({
            'status': 'removed',
            'favorited': False
        })

    # ------------------- ADD / UPDATE -------------------
    favorite, created = Favorite.objects.get_or_create(
        user=user, tender=tender,
        defaults={'company': None}
    )

    form = FavoriteForm(request.POST, user=user, tender=tender, instance=favorite)
    if form.is_valid():
        form.save()
        logger.info(f"Tender Favorite: { tender.id }")
        return JsonResponse({
            'status': 'added' if created else 'updated',
            'favorited': True,
            'favorite_id': str(favorite.id)
        })
    else:
        return JsonResponse({
            'status': 'error',
            'errors': form.errors
        }, status=400)

    return HttpResponse(status=404)


@login_required
def company_folder_choices(request):
    companies = Company.objects.filter(user=request.user).values('id', 'name')
    folders = Folder.objects.filter(user=request.user).values('id', 'name')

    return JsonResponse({
        'companies': list(companies),
        'folders': list(folders),
    })


def get_user_settings(request):
    return UserSetting.objects.filter(user = request.user).first()


