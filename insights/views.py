import logging
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control

from django.db.models import F, Q, Count, Sum, Min, Max, FloatField, ExpressionWrapper
from django.core.paginator import Paginator

from base.context_processors import portal_context

from base.models import Concurrent


BIDDERS_ITEMS_PER_PAGE = 25
# SHOW_TODAYS_EXPIRED = True
# SHOW_CANCELLED = True


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard(request):
    return HttpResponse('Dashboard Home')


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bidders_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us: 
        BIDDERS_ITEMS_PER_PAGE = int(us.general_items_per_page)
        # SHOW_TODAYS_EXPIRED = us.tenders_show_expired
    BIDDERS_ORDERING_FIELD = '-last_win' #'bidders_count'

    def get_req_params(req):
        allowed_keys = [
            'q', 'w', 'n', 'x', 'p', 's', 'page', 'sort',
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        if not 'sort' in query_dict:
            query_dict['sort'] = BIDDERS_ORDERING_FIELD
            
        query_string = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != '' and k != 'page'
        }

        query_unsorted = {
            k: v for k, v in req.GET.items()
            if k in allowed_keys and v != '' and k not in ('page', 'sort')
        }

        return query_dict, query_string, query_unsorted

    def filter_bidders(bidders, params):
        ff = 0
        if not params : return bidders.distinct(), ff

        if 'q' in params:
            ff += 1
            q = params['q']
            bidders = bidders.filter(name__icontains=q)

        if 'n' in params:
            ff += 1
            n = params['n']
            bidders = bidders.filter(wins_sum__gte=n)

        if 'x' in params:
            ff += 1
            x = params['x']
            bidders = bidders.filter(wins_sum__lte=x)

        if 'w' in params:
            ff += 1
            w = params['w']
            if w == "0":
                bidders = bidders.filter(wins_count=0)
            elif w == "1":
                bidders = bidders.filter(wins_count=1)
            elif w == "2":
                bidders = bidders.filter(wins_count__gte=1)
            elif w == "11":
                bidders = bidders.filter(wins_count__gte=10)

        if 'p' in params:
            ff += 1
            p = params['p']
            if p == "0":
                bidders = bidders.filter(part_count=0)
            elif p == "1":
                bidders = bidders.filter(part_count=1)
            elif p == "2":
                bidders = bidders.filter(part_count__gte=1)
            elif p == "11":
                bidders = bidders.filter(part_count__gte=10)

        if 's' in params:
            ff += 1
            s = params['s']
            if s == "1":
                bidders = bidders.filter(succ_rate=100)
            elif s == "6":
                bidders = bidders.filter(succ_rate__gte=50)
            elif s == "4":
                bidders = bidders.filter(succ_rate__lte=50)

        return bidders.distinct(), ff

    def define_context(request):
        context = {}
        context['query_string']       = urlencode(query_string)
        context['query_unsorted']     = urlencode(query_unsorted)
        context['query_dict']         = query_dict

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    all_bidders = Concurrent.objects.annotate(
            part_count = Count('bidders__minutes', distinct=True),
            bids_count = Count('selected_bids__minutes', distinct=True),
            wins_count = Count('winner_bids__minutes', distinct=True),
            bids_sum   = Sum('selected_bids__amount_before', distinct=True),
            wins_sum   = Sum('winner_bids__amount', distinct=True),
            last_win   = Max('winner_bids__minutes__date_end'),
            last_part  = Max('bidders__minutes__date_end'),
        ).filter(
            bids_sum__gt=0,
        ).annotate(
            succ_rate  = ExpressionWrapper(
                F("wins_sum") * 100.0 / F("bids_sum"),
                output_field=FloatField(),
            )
        )

    #     # .prefetch_related(
    #     #     'bidders', 'admin_rejects', 'admin_accepts', 
    #     #     'admin_reserves', 'tech_rejects', 
    #     #     'selected_bids', 'winner_bids'
    #     # )

    # all_bidders = Concurrent.objects.all().prefetch_related(
    #             'bidders', 'admin_rejects', 'admin_accepts', 
    #             'admin_reserves', 'tech_rejects', 
    #             'selected_bids', 'winner_bids'
    #         )


    bidders, filters = filter_bidders(all_bidders, query_dict)

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = [sort]
    else: ordering = []

    ordering.append('-wins_sum')

    query_dict['filters'] = filters

    # if ordering == []: ordering = ['-name']

    bidders = bidders.order_by(*ordering)
    # bidders = bidders.order_by('-wins_sum')

    context = define_context(request)

    paginator = Paginator(bidders, BIDDERS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj
    # context['bidders'] = bidders


    logger = logging.getLogger('portal')
    logger.info(f"Bidders List view")

    return render(request, 'insights/bidders-list.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bidder_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    bidder = get_object_or_404(
        Concurrent.objects.prefetch_related(
            'bidders', 
            'admin_rejects', 
            'admin_accepts', 
            'admin_reserves', 
            'tech_rejects', 
            'selected_bids', 
            'winner_bids' 
        # ).annotate(
        #     bidders_sum     = Sum('selected_bids__amount_after'),
        #     winner_bids_sum = Sum('winner_bids__amount'),
        )
        , id=pk)

    if not bidder : return HttpResponse(status=404)
    # bidder = bidder.annotate(
    #         bids_sum     = Sum('selected_bids__amount_after', distinct=True),
    #         wins_sum     = Sum('winner_bids__amount', distinct=True),
    # )

    # lwb = bidder.winner_bids.order_by('minutes').first()
    # latest_win = lwb.minutes.date_end if lwb else None
    # bs = bidder.bidders_sum if bidder.bidders_sum else 0
    # ws = bidder.winner_bids_sum if bidder.winner_bids_sum else 0

    # success_rate = ws / bs if bs > 0 else None
    # success_rate = round(100 * success_rate, 2) if success_rate else None

    context = { 
            'bidder'        : bidder,
            # 'success_rate'  : round(100 * success_rate, 2) if success_rate else None,
            # 'latest_win'    : latest_win,
            }

    logger = logging.getLogger('portal')
    logger.info(f"Bidder details view: {bidder.id}")

    return render(request, 'insights/bidder-details.html', context)

