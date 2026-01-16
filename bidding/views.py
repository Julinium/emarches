import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from urllib.parse import urlencode
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.models import User

# from django.utils.translation import gettext_lazy as _

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control

from django.db.models import F, Prefetch # , Q, Count, Sum, Min, Max, DecimalField, ExpressionWrapper
# from django.db.models.functions import NullIf, Round
# from decimal import Decimal

from django.core.paginator import Paginator

from base.context_processors import portal_context

from bidding.models import Bid, Team, TeamMember
from base.models import Tender, Lot

from bidding.forms import BidForm

BIDS_ITEMS_PER_PAGE = 25


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard(request):
    return HttpResponse('Dashboard')


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bids_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    if us: 
        BIDS_ITEMS_PER_PAGE = int(us.general_items_per_page)
    BIDS_ORDERING_FIELD = 'date_submitted'

    def get_req_params(req):
        allowed_keys = [
            'q', 'w', 'n', 'x', 'p', 's', 'page', 'sort',
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        if not 'sort' in query_dict:
            query_dict['sort'] = BIDS_ORDERING_FIELD
            
        query_string = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != '' and k != 'page'
        }

        query_unsorted = {
            k: v for k, v in req.GET.items()
            if k in allowed_keys and v != '' and k not in ('page', 'sort')
        }

        return query_dict, query_string, query_unsorted

    def filter_bids(bids, params):
        ff = 0
        if not params : return bids.distinct(), ff

        if 'q' in params:
            ff += 1
            q = params['q']
            bids = bids.filter(name__icontains=q)

        if 'n' in params:
            ff += 1
            n = params['n']
            bids = bids.filter(wins_sum__gte=n)

        if 'x' in params:
            ff += 1
            x = params['x']
            bids = bids.filter(wins_sum__lte=x)

        if 'w' in params:
            ff += 1
            w = params['w']
            if w == "0":
                bids = bids.filter(wins_count=0)
            elif w == "1":
                bids = bids.filter(wins_count=1)
            elif w == "2":
                bids = bids.filter(wins_count__gte=1)
            elif w == "11":
                bids = bids.filter(wins_count__gte=10)

        if 'p' in params:
            ff += 1
            p = params['p']
            if p == "0":
                bids = bids.filter(part_count=0)
            elif p == "1":
                bids = bids.filter(part_count=1)
            elif p == "2":
                bids = bids.filter(part_count__gte=1)
            elif p == "11":
                bids = bids.filter(part_count__gte=10)

        if 's' in params:
            ff += 1
            s = params['s']
            if s == "1":
                bids = bids.filter(succ_rate=100)
            elif s == "6":
                bids = bids.filter(succ_rate__gte=50)
            elif s == "4":
                bids = bids.filter(succ_rate__lte=50)

        return bids.distinct(), ff

    def define_context(request):
        context = {}
        context['query_string']       = urlencode(query_string)
        context['query_unsorted']     = urlencode(query_unsorted)
        context['query_dict']         = query_dict

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    if user.teams.count() < 1:
        team = Team.objects.create(
            name=user.username.upper(),
            creator=user,
        )
        team.add_member(user, patron=True)

    teams = user.teams.all()
    # team  = 

    colleagues = user.teams.first().members.all()

    if teams:
        all_bids = Bid.objects.filter(creator__in=colleagues)

        bid_tenders = Tender.objects.filter(
                lots__bids__creator__in=colleagues,
            ).prefetch_related(
                Prefetch(
                    "lots__bids",
                    queryset=Bid.objects.filter(creator__in=colleagues,),
                    to_attr="team_bids",
                )
            ).order_by(
                '-deadline',
            ).distinct()
    else:
        all_bids = Bid.objects.none()
        bid_tenders = Tender.objects.none()

    bids, filters = filter_bids(all_bids, query_dict)
    query_dict['filters'] = filters

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = sort
    else: ordering = BIDS_ORDERING_FIELD

    if ordering[0] == '-':
        ordering = ordering[1:]
        bids = bids.order_by(
            F(ordering).asc(nulls_last=True), BIDS_ORDERING_FIELD
            )
    else:
        bids = bids.order_by(
            F(ordering).desc(nulls_last=True), BIDS_ORDERING_FIELD
            )

    context = define_context(request)

    paginator = Paginator(bid_tenders, BIDS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    # context['colleagues']  = colleagues
    # context['bid_tenders'] = bid_tenders
    context['page_obj']    = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Bids List view")

    return render(request, 'bidding/bids-list.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)
    
    bid = get_object_or_404(Bid, pk=pk)
    corrected = bid.amount_c != None and bid.amount_c != bid.amount_s
    context = {
        "bid"       : bid,
        "corrected" : corrected,
    }

    return render(request, 'bidding/bid-details.html', context)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_delete(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    bid = None

    if pk:
        bid = get_object_or_404(Bid, pk=pk)
        tender = bid.lot.tender
    else:
        tender = get_object_or_404(Tender, pk=tk)        

    if not bid:
        return HttpResponse(status=404)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_edit(request, pk=None, tk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    
    bid = None

    if pk:
        bid = get_object_or_404(Bid, pk=pk)
        tender = bid.lot.tender
    else:
        tender = get_object_or_404(Tender, pk=tk)        

    if request.method == "POST":
        form = BidForm(
            request.POST,
            instance=bid,
            user=user,
            tender=tender,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.tender = tender
            obj.creator = user
            obj.save()
            return redirect("bidding_bids_list")
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        messages.error(request, f"{field.label}: {error}")
    else:
        form = BidForm(
            instance=bid,
            user=user,
            tender=tender,
        )
        if bid is None:
            form.fields["date_submitted"].initial   = datetime.now()

            if tender.lots.count() == 1:
                lot = tender.lots.first()
                form.fields["lot"].initial              = lot
                form.fields["amount_s"].initial         = lot.estimate
                form.fields["bond_amount"].initial      = lot.bond
                if lot.description: 
                    desc = lot.description
                    form.fields["details"].initial      = desc

            companies = user.companies
            if companies.count() == 1:
                form.fields["company"].initial      = companies.first()


    return render(request, 'bidding/bids/bid_form.html', {
        "form"  : form,
        "object": bid,
        "tender": tender,
    })



