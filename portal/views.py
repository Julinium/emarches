from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

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

        self.query_params = request.GET.copy()
        self.query_params.pop('page', None)
        self.query_string = self.query_params.urlencode()
        self.sorter = self.request.GET.get('sort', TENDERS_ORDERING_FIELD)
        self.query_params.pop('sort', None)
        self.query_unsorted = self.query_params.urlencode()

    def get_queryset(self):
        today_now = timezone.now()
        sorter = self.sorter
        
        if sorter and sorter != '': ordering = [sorter]
        else: ordering = []
        ordering.append('id')

        tenders = Tender.objects.filter(
                deadline__gte=today_now,
            ).order_by(
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

        context['query_string']       = self.query_string
        context['query_unsorted']     = self.query_unsorted
        context['categories']         = all_categories
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS
        context['last_updated']       = last_updated

        context['sorter']             = self.sorter #request.GET.get('sort', TENDERS_ORDERING_FIELD)

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

