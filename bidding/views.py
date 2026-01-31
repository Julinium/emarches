import os, logging
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import HttpResponse
from urllib.parse import urlencode
from datetime import datetime, date, timezone
from django.contrib import messages
from django.contrib.auth.models import User

from django.conf import settings

from django.utils.translation import gettext_lazy as _

from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control

from django.db.models import F , Q, Prefetch #, Count, Sum, Min, Max, DecimalField, ExpressionWrapper
# from django.db.models.functions import NullIf, Round
# from decimal import Decimal

from django.core.paginator import Paginator

from base.context_processors import portal_context
from nas.models import Company
from nas.choices import BidStatus, BidResults, BondStatus

from bidding.models import Bid, Team, Task, Expense
from base.models import Tender, Lot

from bidding.forms import BidForm, TaskForm, ExpenseForm
from bidding.secu import is_team_admin, is_team_member

TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = 25
BIDS_ITEMS_PER_PAGE = 25


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard(request):
    return HttpResponse('Dashboard')



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tenders_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    team = user.teams.first()
    if not team: return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    
    if us: 
        TENDERS_ITEMS_PER_PAGE = int(us.general_items_per_page)
        TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
    TENDERS_ORDERING_FIELD = 'deadline'

    def get_req_params(req):
        allowed_keys = [
            'q', 'page', 'sort',
            ]

        query_dict = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != ''
        }
        if not 'sort' in query_dict:
            query_dict['sort'] = TENDERS_ORDERING_FIELD
            
        query_string = {
            k: v for k, v in req.GET.items() if k in allowed_keys and v != '' and k != 'page'
        }

        query_unsorted = {
            k: v for k, v in req.GET.items()
            if k in allowed_keys and v != '' and k not in ('page', 'sort')
        }

        return query_dict, query_string, query_unsorted

    def filter_tenders(tenders, params):
        ff = 0
        if not params : return tenders.distinct(), ff

        if 'q' in params:
            ff += 1
            q = params['q']
            tenders = tenders.filter(
                Q(title__icontains=q) | 
                Q(reference__icontains=q) | 
                Q(chrono__icontains=q) | 
                Q(client__name__icontains=q) | 
                Q(lots__title__icontains=q) | 
                Q(lots__description__icontains=q) | 
                Q(lots__bids__title__icontains=q)
            )
        
        return tenders.distinct(), ff

    def define_context(request):
        context = {}
        context['query_string']   = urlencode(query_string)
        context['query_unsorted'] = urlencode(query_unsorted)
        context['query_dict']     = query_dict
        context['full_bar_days']  = TENDER_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    if user.teams.count() < 1:
        team = Team.objects.create(
            name=user.username.upper(),
            creator=user,
        )
        team.add_member(user, patron=True)

    teams = user.teams.all()
    colleagues = user.teams.first().members.all()

    if teams:
        bid_tenders = Tender.objects.filter(
                lots__bids__creator__in=colleagues,
            ).prefetch_related(
                Prefetch(
                    "lots__bids",
                    queryset=Bid.objects.filter(creator__in=colleagues,),
                    to_attr="team_bids",
                ),
                'openings',
                "lots__bids__tasks",
                "lots__bids__expenses",
                "lots__bids__contracts",
            ).order_by(
                '-deadline',
            ).distinct()
    else:
        bid_tenders = Tender.objects.none()

    tenders, filters = filter_tenders(bid_tenders, query_dict)
    query_dict['filters'] = filters

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = sort
    else: ordering = TENDERS_ORDERING_FIELD

    if ordering[0] == '-':
        ordering = ordering[1:]
        tenders = tenders.order_by(
            F(ordering).asc(nulls_last=True), TENDERS_ORDERING_FIELD
            )
    else:
        tenders = tenders.order_by(
            F(ordering).desc(nulls_last=True), TENDERS_ORDERING_FIELD
            )

    context = define_context(request)

    paginator = Paginator(tenders, TENDERS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj']    = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Bid Tenders List view")

    return render(request, 'bidding/tenders-list.html', context)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bids_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    team = user.teams.first()
    if not team: return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    
    if us: 
        BIDS_ITEMS_PER_PAGE = int(us.general_items_per_page)
    BIDS_ORDERING_FIELD = '-status'

    def get_req_params(req):
        allowed_keys = [
            'q', 'status', 'bond_status', 'result', 'company', 'creator',
            'page', 'sort',
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

    def filter_bids(bids, params, companies=None, colleagues=None):
        ff = 0
        if not params : return bids.distinct(), ff

        if 'q' in params:
            ff += 1
            q = params['q']
            bids = bids.filter(
                Q(title__icontains=q) | 
                Q(lot__tender__title__icontains=q) | 
                Q(lot__tender__reference__icontains=q) | 
                Q(lot__tender__chrono__icontains=q) | 
                Q(lot__tender__client__name__icontains=q) | 
                Q(lot__title__icontains=q) | 
                Q(lot__description__icontains=q)
            )

        if 'status' in params:
            ff += 1
            status = params['status']
            bids = bids.filter(
                status=status
            )

        if 'result' in params:
            ff += 1
            result = params['result']
            bids = bids.filter(
                result=result
            )

        if 'bond_status' in params:
            ff += 1
            bond_status = params['bond_status']
            bids = bids.filter(
                bond_status=bond_status
            )

        if 'company' in params:
            ff += 1
            company = params['company']
            comp_obj = companies.filter(id=company).first()
            bids = bids.filter(
                company=comp_obj
            )

        if 'creator' in params:
            ff += 1
            creator = params['creator']
            user_obj = colleagues.filter(username=creator).first()
            bids = bids.filter(
                creator=user_obj
            )

        return bids.distinct(), ff

    def define_context(request):
        context = {}
        context['query_string']   = urlencode(query_string)
        context['query_unsorted'] = urlencode(query_unsorted)
        context['query_dict']     = query_dict
        context['full_bar_days']  = TENDER_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    if user.teams.count() < 1:
        team = Team.objects.create(
            name=user.username.upper(),
            creator=user,
        )
        team.add_member(user, patron=True)

    teams = user.teams.all()
    colleagues = user.teams.first().members.all()
    companies = Company.objects.filter(user__in=colleagues)
    if companies.count() < 1: return HttpResponse(_("No company found !"), status=403)
    
    if teams:
        all_bids = Bid.objects.filter(
            creator__in=colleagues
        # ).prefetch_related(
        #     "tasks", "expenses", "contracts",
        )
    else:
        all_bids = Bid.objects.none()

    bids, filters = filter_bids(all_bids, query_dict, companies, colleagues)
    query_dict['filters'] = filters

    sort = query_dict['sort']

    if sort and sort != '':
        ordering = sort
    else: ordering = BIDS_ORDERING_FIELD

    if ordering[0] == '-':
        ordering = ordering[1:]
        bids = bids.order_by(
            F(ordering).asc(nulls_last=True), BIDS_ORDERING_FIELD,
            "-bond_status",
            "-date_submitted"
            )
    else:
        bids = bids.order_by(
            F(ordering).desc(nulls_last=True), BIDS_ORDERING_FIELD,
            "-bond_status",
            "-date_submitted"
            )

    context = define_context(request)

    paginator = Paginator(bids, BIDS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    bid_status_choices = BidStatus.choices
    bid_result_choices = BidResults.choices
    bond_status_choices = BondStatus.choices

    context['page_obj']              = page_obj
    context['companies']             = companies
    context['colleagues']            = colleagues
    context['bid_status_choices']    = bid_status_choices
    context['bid_result_choices']    = bid_result_choices
    context['bond_status_choices']   = bond_status_choices

    logger = logging.getLogger('portal')
    logger.info(f"Bids List view")

    return render(request, 'bidding/bids-list.html', context)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bonds_list(request):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    team = user.teams.first()
    if not team: return HttpResponse(status=403)

    pro_context = portal_context(request)
    us = pro_context['user_settings']
    
    if us: 
        BIDS_ITEMS_PER_PAGE = int(us.general_items_per_page)
        # TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
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
        context['query_string']   = urlencode(query_string)
        context['query_unsorted'] = urlencode(query_unsorted)
        context['query_dict']     = query_dict
        context['full_bar_days']  = TENDER_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    if user.teams.count() < 1:
        team = Team.objects.create(
            name=user.username.upper(),
            creator=user,
        )
        team.add_member(user, patron=True)

    teams = user.teams.all()
    colleagues = user.teams.first().members.all()

    if teams:
        all_bids = Bid.objects.filter(
            creator__in=colleagues
        # ).prefetch_related(
        #     "tasks", "expenses", "contracts",
        )
    else:
        all_bids = Bid.objects.none()

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

    paginator = Paginator(bids, BIDS_ITEMS_PER_PAGE)
    page_number = request.GET['page'] if 'page' in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages: page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context['page_obj']    = page_obj

    logger = logging.getLogger('portal')
    logger.info(f"Bonds List view")

    return render(request, 'bidding/bonds-list.html', context)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)
    
    team = user.teams.first()
    if not team: return HttpResponse(status=403)
    
    bid = get_object_or_404(Bid, pk=pk)
    bid = Bid.objects.filter(pk=pk).prefetch_related("tasks", "expenses").first()
    if not bid: return HttpResponse(status=404)

    if not is_team_member(bid.creator, team): return HttpResponse(status=403)
    tender = bid.lot.tender
    if not tender: return HttpResponse(status=404)

    context = {"bid" : bid}

    return render(request, 'bidding/bid-details.html', context)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_delete(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)

    team = user.teams.first()
    if not team: return HttpResponse(status=403)

    logger = logging.getLogger('portal')

    if not is_team_admin(user, team): return HttpResponse(status=403)

    if request.method == "POST":

        bid = None
        if pk: bid = get_object_or_404(Bid, pk=pk)

        if not is_team_admin(bid.creator, team): return HttpResponse(status=403)

        confirmed = request.POST.get('confirmed')
        if confirmed != 'know' :
            messages.error(request, _("Please confirm deletion first"))
            referer = request.META.get('HTTP_REFERER', None)
            if referer:
                return redirect(referer)
            return redirect("bidding_bids_list")

        if bid.status != BidStatus.BID_CANCELLED:
            messages.error(request, _("You can not delete a bid unless it is Cancelled"))
            referer = request.META.get('HTTP_REFERER', None)
            if referer:
                return redirect(referer)
            return redirect("bidding_bids_list")

        if bid.bond_status == BondStatus.BOND_FILED:
            messages.error(request, _("Please check the Bond status before deleting"))
            referer = request.META.get('HTTP_REFERER', None)
            if referer:
                return redirect(referer)
            return redirect("bidding_bids_list")

        try:
            bid.delete()
            messages.success(request, _("Bid deleted successfully"))
            # referer = request.META.get('HTTP_REFERER', None)

            logger.info(f"Bid delete: successful")

            # if referer:
            #     return redirect(referer)
            return redirect("bidding_bids_list")

        except Exception as xc: 
            return HttpResponse(status=403)
            logger.error(f"Bid delete: unsuccessful")

    return HttpResponse(status=405)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_edit(request, pk=None, lk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)
    
    team = user.teams.first()
    if not team: return HttpResponse(status=403)

    pro_context = portal_context(request)
    us          = pro_context['user_settings']

    bid = None

    if pk:
        bid = get_object_or_404(Bid, pk=pk)
        if not is_team_member(bid.creator, team): return HttpResponse(status=403)
        lot = bid.lot
        tender = lot.tender
    else:
        lot = get_object_or_404(Lot, pk=lk)
        tender = lot.tender

    redir = request.GET.get('redirect', None)
    if redir and not url_has_allowed_host_and_scheme(
        redir, allowed_hosts={request.get_host()},
        require_https=request.is_secure()):
        redir = None

    if request.method == "POST":
        form = BidForm(
            request.POST, 
            request.FILES,
            instance=bid,
            user=user,
            lot=lot,
            usets=us,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.lot = lot
            obj.creator = user
            obj.save()

            if redir:
                return redirect(redir)

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
            lot=lot,
            usets=us,
        )
        if bid is None:
            form.fields["date_submitted"].initial   = datetime.now()
            form.fields["bid_amount"].initial         = lot.estimate
            form.fields["bond_amount"].initial      = lot.bond

            client_short = lot.tender.client.short
            if len(client_short) < 1: client_short = "[?]"
            words = lot.title.split()
            words_count = 8
            lot_title = lot.title if len(words) <= words_count else " ".join(words[:words_count]) + " ..."
            bid_title = client_short + " | " + lot.tender.reference + " | " + lot_title 

            form.fields["title"].initial            = bid_title
            if lot.description:
                desc = lot.description
                form.fields["details"].initial      = desc

            companies = user.companies
            if companies.count() == 1:
                form.fields["company"].initial      = companies.first()


    return render(request, 'bidding/bid-form.html', {
        "form"  : form,
        "object": bid,
        "tender": tender,
        "lot"   : lot,
        "redir" : redir,
    })



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def task_edit(request, pk=None, bk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)
    
    team = user.teams.first()
    if not team: return HttpResponse(status=403)

    task = None

    if pk:
        task = get_object_or_404(Task, pk=pk)
        if not is_team_member(task.bid.creator, team): return HttpResponse(status=403)
        bid = task.bid
    else:
        bid = get_object_or_404(Bid, pk=bk)

    redir = request.GET.get('redirect', None)
    if redir and not url_has_allowed_host_and_scheme(
        redir, allowed_hosts={request.get_host()},
        require_https=request.is_secure()):
        redir = None

    if request.method == "POST":
        form = TaskForm(
            request.POST, 
            # request.FILES,
            instance=task,
            user=user,
            bid=bid,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.bid = bid
            obj.creator = user
            obj.save()

            if redir:
                return redirect(redir)

            return redirect("bidding_bid_details", bid.id)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        messages.error(request, f"{field.label}: {error}")
    else:
        form = TaskForm(
            instance=task,
            user=user,
            bid=bid,
        )
        if task is None:
            form.fields["date_due"].initial   = datetime.now()

            colleagues = team.members.all()
            if colleagues.count() == 1:
                form.fields["assignee"].initial      = colleagues.first()


    return render(request, 'bidding/task-form.html', {
        "form"  : form,
        "object": task,
        "bid"   : bid,
        "redir" : redir,
    })



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def expense_edit(request, pk=None, bk=None):

    user = request.user
    if not user or not user.is_authenticated : 
        return HttpResponse(status=403)
    
    team = user.teams.first()
    if not team: return HttpResponse(status=403)

    expense = None

    if pk:
        expense = get_object_or_404(Expense, pk=pk)
        if not is_team_member(expense.bid.creator, team): return HttpResponse(status=403)
        bid = expense.bid
    else:
        bid = get_object_or_404(Bid, pk=bk)

    redir = request.GET.get('redirect', None)
    if redir and not url_has_allowed_host_and_scheme(
        redir, allowed_hosts={request.get_host()},
        require_https=request.is_secure()):
        redir = None

    if request.method == "POST":
        form = ExpenseForm(
            request.POST,
            request.FILES,
            instance=expense,
            user=user,
            bid=bid,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.bid = bid
            obj.creator = user
            obj.save()

            if redir:
                return redirect(redir)

            return redirect("bidding_bid_details", bid.id)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        messages.error(request, f"{field.label}: {error}")
    else:
        form = ExpenseForm(
            instance=expense,
            user=user,
            bid=bid,
        )
        if expense is None:
            form.fields["bill_date"].initial   = datetime.now()
            form.fields["date_paid"].initial   = datetime.now()


    return render(request, 'bidding/expense-form.html', {
        "form"  : form,
        "object": expense,
        "bid"   : bid,
        "redir" : redir,
    })



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_file(request, pk=None, ft=None):

    if not ft: return HttpResponse(status=404)

    user = request.user
    if not user or not user.is_authenticated : return HttpResponse(status=403)

    bid = None
    if pk: bid = get_object_or_404(Bid, pk=pk)
    if not bid : return HttpResponse(status=403)

    team = user.teams.first()
    if not team: return HttpResponse(status=403)
    if not is_team_member(bid.creator, team): return HttpResponse(status=403)

    if ft == 'bond': file_path = bid.file_bond.url
    elif ft == 'receipt': file_path = bid.file_receipt.url
    elif ft == 'submitted': file_path = bid.file_submitted.url
    else: return HttpResponse(status=404)

    file_name = os.path.basename(file_path)
    if not file_name : return HttpResponse(status=403)

    response = HttpResponse()
    response['Content-Type'] = 'application/octet-stream'
    response['X-Accel-Redirect'] = f"/bids/{ft}/{file_name}"
    response['Content-Disposition'] = f'attachment; filename="{ file_name }"'
    # response['Content-Length'] = os.path.getsize(file_path)
    return response



