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
        TENDERS_ORDERING_FIELD = '-estimate'
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
            # tender.is_variant = any(lot.variant == True for lot in tender.lots.all())

        return tenders

        # Annotate each workshop with has_samples
        # return render(request, 'tenders/list.html', {'tenders': tenders})
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    
    #     iced_company = get_company(self.ice)
    #     if len(iced_company) > 0:
    #         context['iced_company'] = iced_company

    #     return context


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
