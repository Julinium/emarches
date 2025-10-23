from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.views.generic import ListView

from django.contrib.auth.models import User

from nas.models import Favorite
from base.models import Tender


TENDERS_ITEMS_PER_PAGE = 20
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
        running_tenders = Tender.objects.filter(
                deadline__gte=today_now
            ).order_by(
                TENDERS_ORDERING_FIELD, 'id'
            ).select_related('client').prefetch_related('lots')

        return running_tenders
    
    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    
    #     iced_company = get_company(self.ice)
    #     if len(iced_company) > 0:
    #         context['iced_company'] = iced_company

    #     return context
