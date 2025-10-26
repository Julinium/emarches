from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Prefetch
# from datetime import datetime

from django.views.generic import ListView, DetailView

from django.contrib.auth.models import User

from nas.models import Favorite
from base.models import Tender, Category, Crawler


TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = settings.TENDERS_ITEMS_PER_PAGE
TENDERS_ORDERING_FIELD = 'published'


@method_decorator(login_required, name='dispatch')
class TenderListView(ListView):

    model = Tender
    template_name = 'portal/tender-list.html'
    context_object_name = 'tenders'
    paginate_by = TENDERS_ITEMS_PER_PAGE

    def get_queryset(self):
        today_now = timezone.now()
        tenders = Tender.objects.filter(
                deadline__gte=today_now,
            ).order_by(
                TENDERS_ORDERING_FIELD, 'id'
            ).select_related(
                'client', 'category', 'mode', 'procedure'
            ).prefetch_related(
                'favorites', 'downloads', 'comments', 'changes',
                )

        return tenders
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_categories = Category.objects.all()

        last_crawler = Crawler.objects.filter(saving_errors=False).order_by('finished').last()
        last_updated = last_crawler.finished if last_crawler else None

        context['categories']         = all_categories
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS
        context['last_updated']       = last_updated

        context['icon_multi_lots']    = 'ui-radios-grid'        # 'grid' # 'ui-checks-grid'
        context['icon_location']      = 'pin-map'               # 'geo'
        context['icon_client']        = 'bank'
        context['icon_deadline']      = 'calendar4-event'
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all fields for the model instance
        context['fields'] = [(field.name, field.value_to_string(self.object)) 
                            for field in Tender._meta.get_fields() 
                            if field.concrete and not field.many_to_many]
        return context


    # def get_queryset(self):
    #     return Tender.objects.select_related(
    #             'user__profile'
    #         ).prefetch_related(
    #             'agrements', 'qualifs'
    #         ).filter(user=self.request.user, active=True)