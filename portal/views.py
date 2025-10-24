from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Prefetch
# from datetime import datetime

from django.views.generic import ListView

from django.contrib.auth.models import User

from nas.models import Favorite
from base.models import Tender


TENDERS_ITEMS_PER_PAGE = 10
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
                deadline__gte=today_now
            ).order_by(
                TENDERS_ORDERING_FIELD, 'id'
            ).select_related('client').prefetch_related(
                'lots', 'favorites', 'downloads', 'comments', 
                # 'lots__agrements', 'lots__qualifs', 
                # 'lots__samples', 'lots__visits', 'lots__meetings', 
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

        # Annotate each workshop with has_samples
        # return render(request, 'tenders/list.html', {'tenders': tenders})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

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


    # workshops = Tender.objects.prefetch_related(
    #     Prefetch(
    #         'lots__agrements',
    #         # queryset=Lot.objects.filter(age__lt=10),  # Example filter
    #         # to_attr='young_agrements'
    #     ),
    #     Prefetch(
    #         'lots__samples',
    #         # queryset=Trip.objects.filter(date__year=2025),
    #         # to_attr='recent_samples'
    #     ),
    #     'lots'  # Still need workers for the base relation
    # )
