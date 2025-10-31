from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

from django.db.models import Q
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import Http404

from django.views.generic import ListView, DetailView

from django.contrib.auth.models import User

from nas.models import Favorite
from base.models import Tender, Category, Procedure, Crawler, Agrement, Qualif


TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = settings.TENDERS_ITEMS_PER_PAGE
TENDERS_ORDERING_FIELD = 'deadline'


@method_decorator(login_required, name='dispatch')
class TenderListView(ListView):

    model = Tender
    template_name = 'portal/tender-list.html'
    context_object_name = 'tenders'
    paginate_by = TENDERS_ITEMS_PER_PAGE

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.sorter = self.request.GET.get('sort', TENDERS_ORDERING_FIELD)

        self.query_params = self.get_requete_params(self.request)
        self.query_dict = self.query_params

        self.query_params.pop('page', None)
        self.query_string = self.query_params
        self.query_params.pop('sort', '')
        self.query_unsorted = self.query_params

    def get_queryset(self):

        sorter = self.sorter
        
        if sorter and sorter != '': ordering = [sorter]
        else: ordering = []
        ordering.append('id')

        tenders, filters = self.filter_tenders(Tender.objects.filter(cancelled=False), 
                                                self.query_params, self.request)
        self.query_dict['filters'] = filters
        # self.query_dict['filted_items'] = filted_items

        tenders = tenders.order_by(
                *ordering
            ).select_related(
                'client', 'category', 'mode', 'procedure'
            ).prefetch_related(
                'favorites', 'downloads', 'comments', 'changes',
                )
        return tenders
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_categories = Category.objects.all()
        all_procedures = Procedure.objects.all()

        last_crawler = Crawler.objects.filter(
            saving_errors=False,
            import_links=False
            ).order_by('finished').last()
        last_updated = last_crawler.finished if last_crawler else None

        context['query_string']       = urlencode(self.query_string)
        context['query_unsorted']     = urlencode(self.query_unsorted)
        context['query_dict']         = self.query_dict

        context['categories']         = all_categories
        context['procedures']         = all_procedures
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS
        context['last_updated']       = last_updated

        context['sorter']             = self.sorter

        context['icon_filters']       = 'front text-warning'
        context['icon_estimate']      = 'cash-coin'
        context['icon_bond']          = 'bookmark-check'
        context['icon_published']     = 'clock'
        context['icon_multi_lots']    = 'ui-radios-grid'        # 'grid' # 'ui-checks-grid'
        context['icon_location']      = 'pin-map'               # 'geo'
        context['icon_client']        = 'briefcase'             # 'house-door' # 'bank'
        context['icon_deadline']      = 'hourglass-bottom'      # 'calendar4-event'
        context['icon_reference']     = 'tag'

        context['icon_restricted']    = 'intersect'             # 'bell-slash-fill'
        context['icon_reserved']      = 'sign-yield-fill'
        context['icon_variant']       = 'shuffle'
        context['icon_has_agrements'] = 'shield-fill-check'
        context['icon_has_qualifs']   = 'mortarboard-fill'
        context['icon_has_samples']   = 'palette2'
        context['icon_has_visits']    = 'person-walking'
        context['icon_has_meetings']  = 'chevron-bar-contract'

        context['icon_changes']       = 'activity'              # 'pencil-square'
        context['icon_favorites']     = 'heart'
        context['icon_downloads']     = 'arrow-down-square'     # 'download'
        context['icon_comments']      = 'chat-square-quote'

        context['icon_ebid']          = 'pc-display-horizontal' # 'laptop'
        context['icon_esign']         = 'usb-drive'             # 'device-ssd'
        context['icon_no_ebid']       = 'pc-display-horizontal' # 'briefcase-fill'

        return context

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(queryset, page_size)
        page = self.request.GET.get('page')
        try:
            tenders = paginator.page(page)
        except PageNotAnInteger:
            tenders = paginator.page(1)
        except EmptyPage:
            tenders = paginator.page(paginator.num_pages)
        return (paginator, tenders, tenders.object_list, tenders.has_other_pages())



    def get_requete_params(self, requete):
        all_params = requete.GET.dict()
        all_params = {k: v for k, v in all_params.items() if v not in ('', None)}
        if not 'ddlnn' in all_params: all_params['ddlnn'] = timezone.now().date().strftime("%Y-%m-%d")
        if not 'sort' in all_params: all_params['sort'] = TENDERS_ORDERING_FIELD

        if 'category' in all_params:
            c = all_params['category']
            all_params['category'] = str(c)
        if 'procedure' in all_params:
            p = all_params['procedure']
            all_params['procedure'] = str(p)

        return all_params

    def filter_tenders(slef, tenders, params, requete):

        ff = 0
        if 'q' in params:
            ff += 1
            q = params['q']
            if 'f' in params:
                match params['f']:
                    case 'client':
                        tenders = tenders.filter(Q(client__name__icontains=q) | Q(client__keywords__icontains=q))
                    case 'location':
                        tenders = tenders.filter(Q(location__icontains=q) | Q(locwords__icontains=q))
                    case 'reference':
                        tenders = tenders.filter(Q(refwords__icontains=q) | Q(reference__icontains=q))
                    case _:
                        tenders = tenders.filter(Q(keywords__icontains=q) | Q(title__icontains=q))
            else:
                tenders = tenders.filter(
                    Q(client__name__icontains=q) | Q(client__keywords__icontains=q) | 
                    Q(location__icontains=q) | Q(locwords__icontains=q) | 
                    Q(refwords__icontains=q) | Q(reference__icontains=q) | 
                    Q(keywords__icontains=q) | Q(title__icontains=q)
                )

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
            if ddlnn != timezone.now().date().strftime("%Y-%m-%d"): 
                ff += 1
            tenders = tenders.filter(deadline__date__gte=ddlnn)
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
                user = requete.user
                if user.is_authenticated:
                    user_agrements = Agrement.objects.filter(companies__user=user)
                    tenders = tenders.filter(lots__agrements__in=user_agrements)

        if 'qualifs' in params:
            ff += 1
            qualifs = params['qualifs']
            if qualifs == 'required': tenders = tenders.filter(has_qualifs=True)
            if qualifs == 'na': tenders = tenders.filter(has_qualifs=False)
            if qualifs == 'companies':
                user = requete.user
                if user.is_authenticated:
                    user_qualifs = Qualif.objects.filter(companies__user=user)
                    tenders = tenders.filter(lots__qualifs__in=user_qualifs)


        # has_samples = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Samples required"))
        # has_meetings = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("In-site visits scheduled"))
        # has_visits = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Meetings scheduled"))

        # #### icons

        # has_agrements = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Licenses required"))
        # has_qualifs = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Qualifications required"))
        # agrements    = '' | 'companies' | 'required' | 'na'
        # qualifs      = '' | 'companies' | 'required' | 'na'

        return tenders.distinct(), ff


@method_decorator(login_required, name='dispatch')
class TenderDetailView(DetailView):
    model = Tender
    template_name = 'portal/tender-details.html'
    context_object_name = 'tender'

    
    def get_queryset(self, **kwargs):
        queryset = super().get_queryset(**kwargs)

        queryset = queryset.select_related(
                'client', 'category', 'mode', 'procedure'
            ).prefetch_related(
                'domains', 'lots', 'lots__agrements', 'lots__qualifs',
                'lots__meetings', 'lots__samples', 'lots__visits'
            )

        return queryset

