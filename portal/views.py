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
            ).order_by(
                TENDERS_ORDERING_FIELD, 'id'
            ).select_related('client').prefetch_related(
                'lots', 'favorites', 'downloads', 'comments', 
                'lots__agrements', 'lots__qualifs', 
                'lots__samples', 'lots__visits', 'lots__meetings', 
                )
        for tender in tenders:
            tender.is_reserved = any(lot.reserved == True for lot in tender.lots.all())
            tender.has_agrements = any(lot.agrements.exists() for lot in tender.lots.all())
            tender.has_qualifs = any(lot.qualifs.exists() for lot in tender.lots.all())
            tender.has_samples = any(lot.samples.exists() for lot in tender.lots.all())
            tender.has_visits = any(lot.visits.exists() for lot in tender.lots.all())
            tender.has_meetings = any(lot.meetings.exists() for lot in tender.lots.all())
            tender.is_variant = any(lot.variant == True for lot in tender.lots.all())

        return tenders
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_categories = Category.objects.all()
        # category_translations = {
        #     'works': _('Travaux'),
        #     'supplies': _('Fourniture'),
        #     'services': _('Services'),
        #     }
        # translated_category = category_translations.get(product.category, product.category)

        context['categories']         = all_categories
        context['full_bar_days']      = TENDER_FULL_PROGRESS_DAYS
        
        context['icon_multi_lots']    = 'grid'
        context['icon_location']      = 'geo'
        context['icon_client']        = 'bank'

        context['icon_is_reserved']   = 'sign-yield-fill'
        context['icon_is_variant']    = 'shuffle'
        context['icon_has_agrements'] = 'shield-fill-check'
        context['icon_has_qualifs']   = 'mortarboard-fill'
        context['icon_has_samples']   = 'palette2'
        context['icon_has_visits']    = 'person-walking'
        context['icon_has_meetings']  = 'chevron-bar-contract'

        context['icon_changes']       = 'pencil-square'
        context['icon_favorites']     = 'heart'
        context['icon_downloads']     = 'download'
        context['icon_comments']      = 'chat-square-text'

        context['icon_ebid']          = 'laptop'
        context['icon_esign']         = 'usb-drive'
        context['icon_no_ebid']       = 'briefcase'


        return context

