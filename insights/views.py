import logging
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control

from django.db.models import F, Q, Count, Sum, Min, Max, FloatField, ExpressionWrapper
from django.db.models.functions import NullIf

from django.core.paginator import Paginator

from base.context_processors import portal_context

from base.models import Concurrent, Tender


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
    BIDDERS_ORDERING_FIELD = 'last_win' #'bidders_count'

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
            part_count = Count('deposits', distinct=True), 
            wins_count = Count('deposits', filter=Q(deposits__winner=True), distinct=True), 
            bids_sum   = Sum('deposits__amount_b', filter=Q(deposits__amount_b__isnull=False), distinct=True), 
            wins_sum   = Sum('deposits__amount_w', filter=Q(deposits__winner=True), distinct=True), 
            last_win   = Max('deposits__date', filter=Q(deposits__winner=True)), 
            last_part  = Max('deposits__date', filter=Q(deposits__amount_b__isnull=False)), 
        ).annotate(
            succ_rate = ExpressionWrapper(
                F("wins_sum") * 100.0 / NullIf(F("bids_sum"), 0),
                output_field=FloatField(),
            )
        )

    bidders, filters = filter_bidders(all_bidders, query_dict)
    query_dict['filters'] = filters

# 
    # HALF_OUTER = 125.66
    # HALF_INNER = 87.96
    # for b in bidders:
    #     try:
    #         b.win_arc = HALF_INNER * (b.wins_sum / b.bids_sum) if b.bids_sum else 0
    #         b.par_arc = HALF_OUTER * (b.wins_count / b.part_count) if b.part_count else 0
    #     except:
    #         b.win_arc, b.par_arc = 0, 0

# 



    sort = query_dict['sort']

    if sort and sort != '':
        ordering = sort
    else: ordering = 'wins_sum'

    if ordering == '-name' or ordering == 'name':
        bidders = bidders.order_by(ordering)
    elif ordering[0] == '-':
        ordering = ordering[1:]
        bidders = bidders.order_by(F(ordering).asc(nulls_last=True))
    else:
        bidders = bidders.order_by(F(ordering).desc(nulls_last=True))


    context = define_context(request)

    paginator = Paginator(bidders, BIDDERS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj'] = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Bidders List view")

    return render(request, 'insights/bidders-list.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bidder_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    bidder = get_object_or_404(Concurrent.objects.prefetch_related('deposits'), id=pk)

    if not bidder : return HttpResponse(status=404)

    admin_rejects  = bidder.deposits.filter(admin='x')
    admin_accepts  = bidder.deposits.filter(admin='a')
    admin_reserves = bidder.deposits.filter(admin='r')
    tech_rejects   = bidder.deposits.filter(reject_t=True)
    selects        = bidder.deposits.filter(amount_b__isnull=False)
    winners        = bidder.deposits.filter(amount_w__isnull=False)
    particips      = bidder.deposits.annotate(tider = F('opening__tender')).order_by('tider').distinct("tider")


    context = { 
        'bidder'         : bidder,
        'admin_rejects'  : admin_rejects,
        'admin_accepts'  : admin_accepts,
        'admin_reserves' : admin_reserves,
        'tech_rejects'   : tech_rejects,
        'selects'        : selects,
        'winners'        : winners,
        'particips'      : particips,
    }

    logger = logging.getLogger('portal')
    logger.info(f"Bidder details view: {bidder.id}")

    return render(request, 'insights/bidder-details.html', context)

