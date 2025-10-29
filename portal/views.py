from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

from django.db.models import Q
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
# from django.db.models import Prefetch

from django.views.generic import ListView, DetailView

from django.contrib.auth.models import User

from nas.models import Favorite
from base.models import Tender, Category, Crawler


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

        tenders, filters = self.filter_tenders(Tender.objects.all(), self.query_params)
        self.query_dict['filters'] = filters

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

        last_crawler = Crawler.objects.filter(
            saving_errors=False,
            import_links=False
            ).order_by('finished').last()
        last_updated = last_crawler.finished if last_crawler else None

        context['query_string']       = urlencode(self.query_string)
        context['query_unsorted']     = urlencode(self.query_unsorted)
        context['query_dict']         = self.query_dict

        context['categories']         = all_categories
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

    def get_requete_params(self, requete):
        all_params = requete.GET.dict()
        # print('========================\n', str(all_params), '\n========================\n')
        all_params = {k: v for k, v in all_params.items() if v not in ('', None)}
        if not 'ddlnn' in all_params: all_params['ddlnn'] = timezone.now().date()
        if not 'sort' in all_params: all_params['sort'] = TENDERS_ORDERING_FIELD

        return all_params

    def filter_tenders(slef, tenders, params):

        ff = 0
        if 'q' in params:
            ff += 1
            q = params['q']
            if 'f' in params:
                match params['f']:
                    case 'client':
                        tenders = tenders.filter(Q(client__name__icontains=q))
                    case 'location':
                        tenders = tenders.filter(Q(location__icontains=q))
                    case _:
                        tenders = tenders.filter(Q(title__icontains=q))
            else:
                tenders = tenders.filter(
                    Q(title__icontains=q) | 
                    Q(location__icontains=q) | 
                    Q(client__name__icontains=q)
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
            ff += 1
            ddlnn = params['ddlnn']
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
            if allotted == 'single': 
                tenders = tenders.filter(lots_count=1)
            if allotted == 'multi': 
                tenders = tenders.filter(lots_count__gt=1)
        
        if 'pme' in params:
            ff += 1
            pme = params['pme']
            if pme == 'reserved':
                tenders = tenders.filter(reserved=True)
            if pme == 'open': 
                tenders = tenders.filter(reserved=False)
        
        if 'variant' in params:
            ff += 1
            variant = params['variant']
            if variant == 'accepted':
                tenders = tenders.filter(variant=True)
            if variant == 'rejected':
                tenders = tenders.filter(variant=False)


        # procedure
        # category
        # esign
        # #### labels
        # samples      = '' | 'required' | 'na'
        # meetings     = '' | 'required' | 'na' 
        # visits       = '' | 'required' | 'na' 

        # agrements    = '' | 'required' | 'na' | 'companies'
        # qualifs      = '' | 'required' | 'na' | 'companies'

        return tenders, ff


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

