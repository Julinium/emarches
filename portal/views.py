from django.shortcuts import render
from django.utils import timezone
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Prefetch
# from datetime import datetime

from django.views.generic import ListView

from django.contrib.auth.models import User

from nas.models import Favorite
from base.models import Tender, Category


TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = settings.TENDERS_ITEMS_PER_PAGE
TENDERS_ORDERING_FIELD = 'deadline'


@method_decorator(login_required, name='dispatch')
class TenderListView(ListView):

    model = Tender
    template_name = 'portal/tender-list.html'
    context_object_name = 'tenders'
    paginate_by = TENDERS_ITEMS_PER_PAGE

    def get_queryset(self):
        TENDERS_ORDERING_FIELD = '-published'
        today_now = timezone.now()
        tenders = Tender.objects.filter(
                deadline__gte=today_now,
                # procedure__restricted=True
            ).order_by(
                TENDERS_ORDERING_FIELD, 'id'
            ).select_related(
                'client', 'category', 'kind', 'mode', 'procedure'
            ).prefetch_related(
                # 'lots', 
                'favorites', 'downloads', 'comments', 'changes', 
                # 'lots__agrements', 'lots__qualifs', 
                # 'lots__samples', 'lots__visits', 'lots__meetings', 
                )

        return tenders
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_categories = Category.objects.all()

        context['categories']         = all_categories
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS

        context['icon_multi_lots']    = 'ui-checks-grid'        # 'grid'
        context['icon_location']      = 'pin-map'               # 'geo'
        context['icon_client']        = 'bank'

        context['icon_restricted']    = 'intersect'             # 'bell-slash-fill'
        context['icon_reserved']      = 'sign-yield-fill'
        context['icon_variant']       = 'shuffle'
        context['icon_has_agrements'] = 'shield-fill-check'
        context['icon_has_qualifs']   = 'mortarboard-fill'
        context['icon_has_samples']   = 'palette2'
        context['icon_has_visits']    = 'person-walking'
        context['icon_has_meetings']  = 'chevron-bar-contract'

        context['icon_changes']       = 'pencil-square'
        context['icon_favorites']     = 'heart'
        context['icon_downloads']     = 'arrow-down-square'     # 'download'
        context['icon_comments']      = 'chat-square-quote'

        context['icon_ebid']          = 'pc-display-horizontal' # 'laptop'
        context['icon_esign']         = 'usb-drive'             # 'device-ssd'
        context['icon_no_ebid']       = 'briefcase-fill'


        return context

