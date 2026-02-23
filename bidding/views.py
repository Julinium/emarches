import logging
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Prefetch, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control

from base.context_processors import portal_context
from base.models import Lot, Tender
from bidding.forms import BidForm, ExpenseForm, InvitationForm, TaskForm
from bidding.models import Bid, Expense, Invitation, Task, Team, TeamMember
from bidding.secu import (
    get_colleagues,
    get_team,
    is_active_team_admin,
    is_active_team_member,
    is_team_admin,
    is_team_member,
    update_membership,
)
from nas.choices import (
    BidResults,
    BidStatus,
    BondStatus,
    ExpenseStatus,
    InvitationReplies,
    TaskStatus,
)
from nas.models import Company

TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = 10
BIDS_ITEMS_PER_PAGE = 10
USERS_ITEMS_PER_PAGE = 10
SHOW_INVITATIONS = True

INVITATION_EXPIRY_HOURS = 48
SAFE_INPUT_RE = re.compile(r"^[a-zA-Z0-9_.@-]+$")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def dashboard(request):
    return HttpResponse(_("Dashboard"))


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def invitation_create(request, tk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if request.method != "POST":
        return HttpResponse(_("Bad request"), status=405)

    if not tk:
        return HttpResponse(_("Not found"), status=404)
    team = get_object_or_404(Team, pk=tk)

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    logger = logging.getLogger("portal")

    form = InvitationForm(request.POST)
    if form.is_valid():
        try:
            obj = form.save(commit=False)
            invitee = User.objects.filter(username=obj.username).first()
            if invitee and invitee in team.members.all():
                messages.warning(request, _("Already member"))
            else:
                obj.team = team
                obj.creator = user
                obj.expiry = datetime.now() + timedelta(hours=INVITATION_EXPIRY_HOURS)
                obj.sent_on = datetime.now()
                obj.save()
                logger.info("Invitation created")
                messages.success(request, _("Invitation created"))

        except Exception as xc:
            logger.info(f"Exception creating Invitation: {str(xc)}")
            return HttpResponse(_("Server error raised"), status=500)
    else:
        return HttpResponse(_("Bad request"), status=405)

    # return HttpResponse(_("Server error raised"), status=500)
    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def invitation_cancel(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if request.method != "POST":
        return HttpResponse(_("Bad request"), status=405)

    if not pk:
        return HttpResponse(_("Not found"), status=404)
    invitation = get_object_or_404(Invitation, pk=pk)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )
    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    if invitation.cancelled:
        return HttpResponse(_("Already cancelled"), status=405)
    if invitation.expired:
        return HttpResponse(_("Already expired"), status=405)

    logger = logging.getLogger("portal")

    try:
        invitation.cancelled = True
        # invitation.update(cancelled = True)
        invitation.save()
        logger.info("Invitation cancelled")
        messages.success(request, _("Invitation cancelled successfully"))
        # return HttpResponse(status=200)

    except Exception as xc:
        logger.info(f"Exception Cancelling invitation: {str(xc)}")
        return HttpResponse(_("Server error raised"), status=500)

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def invitation_accept(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if request.method != "POST":
        return HttpResponse(_("Bad request"), status=405)

    if not pk:
        return HttpResponse(_("Not found"), status=404)
    invitation = get_object_or_404(Invitation, pk=pk)

    if invitation.cancelled:
        return HttpResponse(_("Invitation cancelled"), status=405)
    if invitation.expired:
        return HttpResponse(_("Invitation expired"), status=405)
    invitee = invitation.invitee
    if not invitee:
        return HttpResponse(_("Bad request"), status=405)
    if invitee != user:
        return HttpResponse(_("Bad request"), status=405)

    team = get_team(user)
    if get_team(invitation.creator) == team:
        return HttpResponse(_("Bad request") + ": " + _("Already member"), status=405)

    if team and team.members.count() > 1:
        return HttpResponse(
            _("Bad request") + ": " + _("You need to leave your current team first"),
            status=405,
        )

    logger = logging.getLogger("portal")

    confirmed = request.POST.get("confirmed", None)
    if confirmed != "know":
        messages.error(request, _("Please confirm action first"))

    else:
        try:
            # memberships = invitee.memberships.all()
            deleted_ms = 0
            try:
                with transaction.atomic():
                    deleted_ms, pm = invitee.memberships.all().delete()
                    membership = TeamMember.objects.create(  
                        user=invitee,
                        team=invitation.team,
                        active=False,
                    )
                    update_membership(user, invitee, "disable")
                    # TODO: Delete Former Team if empty
                    invitation.reply = InvitationReplies.INV_ACCEPTED
                    invitation.reply_on = datetime.now()
                    invitation.save()
                    logger.info("Invitation acceptance succeeded")
                    messages.success(
                        request,
                        _("You now are a member of the team")
                        + f": {invitation.team.name}",
                    )
                    messages.error(
                        request, _("Ask a team Manager to activate your membership")
                    )
            except Exception as xs:
                logger.info(f"Deleted user membership instances: {deleted_ms}")
                logger.info(f"Invitation acceptance failed: {str(xs)}")
                return HttpResponse(_("Server error raised"), status=500)

        except Exception as xc:
            logger.info(f"Exception Cancelling invitation: {str(xc)}")
            return HttpResponse(_("Server error raised") + f": {str(xc)}", status=500)

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def team_recap(request):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        team = Team.objects.create(  
            name=_("TEAM") + "-" + user.username.upper(),
            creator=user,
        )
        team.add_member(user, manager=True)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return render(request, "bidding/team-member-disabled.html", {"team": team})
        # return HttpResponse(_("Member is not active") + f" in: [{ team }]", status=403)

    if team.members.count() == 1:
        tm = user.memberships.filter(team=team).order_by("joined").last()
        if not tm.manager:
            tm.manager = True
            tm.save()

    pro_context = portal_context(request)
    us = pro_context["user_settings"]

    if us:
        USERS_ITEMS_PER_PAGE = int(us.general_items_per_page)
        SHOW_INVITATIONS = int(us.general_show_invitations)
    USERS_ORDERING_FIELD = "username"

    all_members = team.members.annotate(
        # is_me = F("memberships__user", filter ...),
        is_actife=F("memberships__active"),
        is_manager=F("memberships__manager"),
        joined=F("memberships__joined"),
    )

    colleagues = all_members.exclude(id=user.id).order_by("-is_actife", "-is_manager", USERS_ORDERING_FIELD)
    member_me = all_members.filter(id=user.id).first()

    paginator = Paginator(colleagues, USERS_ITEMS_PER_PAGE)
    page_number = request.GET["page"] if "page" in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    invitable = SHOW_INVITATIONS
    if invitable:
        # invitable = True
        invited = (
            user.received_invitations.exclude(
                reply=InvitationReplies.INV_ACCEPTED,
                # creator=user,
            )
            .exclude(
                # reply=InvitationReplies.INV_ACCEPTED,
                creator=user,
            )
            .filter(
                username=user.username,
                cancelled=False,
                expiry__gte=datetime.now(),
            )
        )
    else:
        invited = Invitation.objects.none()
        # invitable = False

    invitations = user.invitations.exclude(reply=InvitationReplies.INV_ACCEPTED).filter(
        cancelled=False,
        # reply_on__isnull=True,
        expiry__gte=datetime.now(),
    )

    invitation_form = InvitationForm()

    context = {
        "page_obj": page_obj,
        "member_me": member_me,
        "team": team,
        "invitation_form": invitation_form,
        "invitations": invitations,
        "invited": invited,
        "invitable": invitable,
        "manage": is_active_team_admin(user, team),
        "expiry_hours": INVITATION_EXPIRY_HOURS,
    }

    logger = logging.getLogger("portal")
    logger.info("Team members List view")

    return render(request, "bidding/team-recap.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def team_edit(request, tk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if not tk:
        return HttpResponse(
            _("Bad request") + ": " + _(" Team not found or not allowed"), status=405
        )

    peam = get_object_or_404(Team, pk=tk)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    if team != peam:
        return HttpResponse(
            _("Bad request") + ": " + _(" Team not allowed or not found"), status=403
        )

    if request.method != "POST":
        return HttpResponse(_("Bad request"), status=403)

    team_name = request.POST.get("team_name", None)
    rename = True

    if team_name is None:
        rename = False
        messages.error(request, _("Entered name was empty or too short"))

    if rename:
        if len(team_name) < 4:
            rename = False
            messages.error(request, _("Name is too short"))

    if rename:
        if len(team_name) > 64:
            rename = False
            messages.error(request, _("Name is too long"))

    if rename:
        if not SAFE_INPUT_RE.fullmatch(team_name):
            rename = False
            messages.error(request, _("Only letters, numbers and _ . @ - are allowed"))

    if rename:
        team.name = team_name
        team.save()
        messages.success(request, _("Team renamed successfully"))

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def member_disable(request, uk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if not uk:
        return HttpResponse(_("Not found"), status=404)
    member = get_object_or_404(User, pk=uk)

    if member == user:
        return HttpResponse(_("Bad request") + ": " + _("Self enabling"), status=405)

    team = get_team(user)
    if not team:
        return HttpResponse(_("Team not found"), status=404)

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied"), status=403)
    if not is_active_team_member(member, team):
        return HttpResponse(_("Bad request") + ": " + _("Already disabled"), status=405)

    logger = logging.getLogger("portal")

    try:
        um = update_membership(user, member, "disable")
        if um == "disable":
            logger.info("Member disabled successfully")
            messages.success(request, _("Member disabled successfully"))
        else:
            return HttpResponse(_("Server error raised"), status=500)

    except Exception as xc:
        logger.info(f"Exception Disabling member: {str(xc)}")
        return HttpResponse(_("Server error raised"), status=500)

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def member_enable(request, uk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if not uk:
        return HttpResponse(_("Not found"), status=404)
    member = get_object_or_404(User, pk=uk)

    if member == user:
        return HttpResponse(_("Bad request") + ": " + _("Self enabling"), status=405)

    team = get_team(user)
    if not team:
        return HttpResponse(_("Team not found"), status=404)

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied"), status=403)
    if is_active_team_member(member, team):
        return HttpResponse(_("Bad request") + ": " + _("Already enabled"), status=405)

    logger = logging.getLogger("portal")

    try:
        um = update_membership(user, member, "enable")
        if um == "enable":
            logger.info("Member enabled successfully")
            messages.success(request, _("Member enabled successfully"))
        else:
            return HttpResponse(_("Server error raised"), status=500)

    except Exception as xc:
        logger.info(f"Exception Enabling member: {str(xc)}")
        return HttpResponse(_("Server error raised") + ": " + f" {str(xc)}", status=500)

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def member_bossify(request, uk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if not uk:
        return HttpResponse(_("Not found"), status=404)
    member = get_object_or_404(User, pk=uk)

    if member == user:
        return HttpResponse(_("Bad request") + ": " + _("Self editing"), status=405)

    team = get_team(user)
    if not team:
        return HttpResponse(_("Team not found"), status=404)

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied"), status=403)
    if is_team_admin(member, team):
        return HttpResponse(_("Bad request") + ": " + _("Already manager"), status=405)

    logger = logging.getLogger("portal")

    try:
        um = update_membership(user, member, "bossify")
        if um == "bossify":
            logger.info("Member made manager successfully")
            messages.success(request, _("Member made manager successfully"))
        else:
            return HttpResponse(_("Server error raised"), status=500)

    except Exception as xc:
        logger.info(f"Exception making manager a member: {str(xc)}")
        return HttpResponse(_("Server error raised") + ": " + f" {str(xc)}", status=500)

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def member_debossify(request, uk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if not uk:
        return HttpResponse(_("Not found"), status=404)
    member = get_object_or_404(User, pk=uk)

    if member == user:
        return HttpResponse(_("Bad request") + ": " + _("Self editing"), status=405)

    team = get_team(user)
    if not team:
        return HttpResponse(_("Team not found"), status=404)

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied"), status=403)
    if not is_team_admin(member, team):
        return HttpResponse(
            _("Bad request") + ": " + _("Already not manager"), status=405
        )

    logger = logging.getLogger("portal")

    try:
        um = update_membership(user, member, "debossify")
        if um == "debossify":
            logger.info("Member made not manager successfully")
            messages.success(request, _("Member made not manager successfully"))
        else:
            return HttpResponse(_("Server error raised"), status=500)

    except Exception as xc:
        logger.info(f"Exception making not manager a member: {str(xc)}")
        return HttpResponse(_("Server error raised") + ": " + f" {str(xc)}", status=500)

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def member_fire(request, uk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    if not uk:
        return HttpResponse(_("Not found"), status=404)
    member = get_object_or_404(User, pk=uk)

    if member == user:
        return HttpResponse(_("Bad request") + ": " + _("Self editing"), status=405)

    team = get_team(user)
    if not team:
        return HttpResponse(_("Team not found"), status=404)

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied"), status=403)
    if not is_team_member(member, team):
        return HttpResponse(_("Bad request") + ": " + _("Not a member"), status=405)

    logger = logging.getLogger("portal")

    try:
        um = update_membership(user, member, "fire")
        if um == "fire":
            logger.info("Member fired successfully")
            messages.success(request, _("Member fired successfully"))
        else:
            return HttpResponse(_("Server error raised"), status=500)

    except Exception as xc:
        logger.info(f"Exception firing a member: {str(xc)}")
        return HttpResponse(_("Server error raised") + ": " + f" {str(xc)}", status=500)

    return redirect("bidding_team_recap")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tenders_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    pro_context = portal_context(request)
    us = pro_context["user_settings"]

    if us:
        TENDERS_ITEMS_PER_PAGE = int(us.general_items_per_page)
        TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
    TENDERS_ORDERING_FIELD = "deadline"

    def get_req_params(req):
        allowed_keys = [
            "q",
            "page",
            "sort",
        ]

        query_dict = {k: v for k, v in req.GET.items() if k in allowed_keys and v != ""}
        if "sort" not in query_dict:
            query_dict["sort"] = TENDERS_ORDERING_FIELD

        query_string = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k != "page"
        }

        query_unsorted = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k not in ("page", "sort")
        }

        return query_dict, query_string, query_unsorted

    def filter_tenders(tenders, params):
        ff = 0
        if not params:
            return tenders.distinct(), ff

        if "q" in params:
            ff += 1
            q = params["q"]
            tenders = tenders.filter(
                Q(title__icontains=q)
                | Q(reference__icontains=q)
                | Q(chrono__icontains=q)
                | Q(client__name__icontains=q)
                | Q(lots__title__icontains=q)
                | Q(lots__description__icontains=q)
                | Q(lots__bids__title__icontains=q)
            )

        return tenders.distinct(), ff

    def define_context(request):
        context = {}
        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict
        context["full_bar_days"] = TENDER_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    # teams = user.teams.all()
    colleagues = get_colleagues(user)

    bid_tenders = (
        Tender.objects.filter(
            lots__bids__creator__in=colleagues,
        )
        .prefetch_related(
            Prefetch(
                "lots__bids",
                queryset=Bid.objects.filter(
                    creator__in=colleagues,
                ),
                to_attr="team_bids",
            ),
            "openings",
            "lots__bids__tasks",
            "lots__bids__expenses",
            "lots__bids__contracts",
        )
        .order_by(
            "-deadline",
        )
        .distinct()
    )

    tenders, filters = filter_tenders(bid_tenders, query_dict)
    query_dict["filters"] = filters

    sort = query_dict["sort"]

    if sort and sort != "":
        ordering = sort
    else:
        ordering = TENDERS_ORDERING_FIELD

    if ordering[0] == "-":
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
    page_number = request.GET["page"] if "page" in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context["page_obj"] = page_obj

    logger = logging.getLogger("portal")
    logger.info("Bid Tenders List view")

    return render(request, "bidding/tenders-list.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bids_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    manager = is_active_team_admin(user, team)

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    pro_context = portal_context(request)
    us = pro_context["user_settings"]

    if us:
        BIDS_ITEMS_PER_PAGE = int(us.general_items_per_page)
    BIDS_ORDERING_FIELD = "-status"

    def get_req_params(req):
        allowed_keys = [
            "q",
            "status",
            "bond_status",
            "result",
            "company",
            "creator",
            "page",
            "sort",
        ]

        query_dict = {k: v for k, v in req.GET.items() if k in allowed_keys and v != ""}
        if "sort" not in query_dict:
            query_dict["sort"] = BIDS_ORDERING_FIELD

        query_string = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k != "page"
        }

        query_unsorted = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k not in ("page", "sort")
        }

        return query_dict, query_string, query_unsorted

    def filter_bids(bids, params, companies=None, colleagues=None):
        ff = 0
        if not params:
            return bids.distinct(), ff

        if "q" in params:
            ff += 1
            q = params["q"]
            bids = bids.filter(
                Q(title__icontains=q)
                | Q(lot__tender__title__icontains=q)
                | Q(lot__tender__reference__icontains=q)
                | Q(lot__tender__chrono__icontains=q)
                | Q(lot__tender__client__name__icontains=q)
                | Q(lot__title__icontains=q)
                | Q(lot__description__icontains=q)
            )

        if "status" in params:
            ff += 1
            status = params["status"]
            bids = bids.filter(status=status)

        if "result" in params:
            ff += 1
            result = params["result"]
            bids = bids.filter(result=result)

        if "bond_status" in params:
            ff += 1
            bond_status = params["bond_status"]
            bids = bids.filter(bond_status=bond_status)

        if "company" in params and companies:
            ff += 1
            company = params["company"]
            comp_obj = companies.filter(id=company).first()
            bids = bids.filter(company=comp_obj)

        if "creator" in params and colleagues:
            ff += 1
            creator = params["creator"]
            user_obj = colleagues.filter(username=creator).first()
            bids = bids.filter(creator=user_obj)

        return bids.distinct(), ff

    def define_context(request):
        context = {}
        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict
        context["full_bar_days"] = TENDER_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    colleagues = get_colleagues(user)
    companies = Company.objects.filter(user__in=colleagues) 
    
    if companies.count() < 1:
        return HttpResponse(_("No company found !"), status=403)

    all_bids = Bid.objects.filter(
        creator__in=colleagues,
        company__in=companies,
    ).prefetch_related(
        "tasks",
        "expenses",  # "contracts",
    )

    bids, filters = filter_bids(all_bids, query_dict, companies, colleagues)
    query_dict["filters"] = filters

    sort = query_dict["sort"]

    if sort and sort != "":
        ordering = sort
    else:
        ordering = BIDS_ORDERING_FIELD

    if ordering[0] == "-":
        ordering = ordering[1:]
        bids = bids.order_by(
            F(ordering).asc(nulls_last=True),
            BIDS_ORDERING_FIELD,
            "-bond_status",
            "-date_submitted",
        )
    else:
        bids = bids.order_by(
            F(ordering).desc(nulls_last=True),
            BIDS_ORDERING_FIELD,
            "-bond_status",
            "-date_submitted",
        )

    context = define_context(request)

    paginator = Paginator(bids, BIDS_ITEMS_PER_PAGE)
    page_number = request.GET["page"] if "page" in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    bid_status_choices = BidStatus.choices
    bid_result_choices = BidResults.choices
    bond_status_choices = BondStatus.choices

    context["page_obj"] = page_obj
    context["companies"] = companies
    context["colleagues"] = colleagues
    context["bid_status_choices"] = bid_status_choices
    context["bid_result_choices"] = bid_result_choices
    context["bond_status_choices"] = bond_status_choices
    context["manager"] = manager

    logger = logging.getLogger("portal")
    logger.info("Bids List view")

    return render(request, "bidding/bids-list.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bonds_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)
    
    BIDS_ORDERING_FIELD = "-bond_due_date"

    def get_req_params(req):
        allowed_keys = [
            "company",
            "creator",
            "page",
            "sort",
        ]

        query_dict = {k: v for k, v in req.GET.items() if k in allowed_keys and v != ""}
        if "sort" not in query_dict:
            query_dict["sort"] = BIDS_ORDERING_FIELD

        query_string = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k != "page"
        }

        query_unsorted = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k not in ("page", "sort")
        }

        return query_dict, query_string, query_unsorted

    def filter_bids(bids, params):
        ff = 0
        if not params:
            return bids.distinct(), ff

        if "company" in params:
            ff += 1
            company = params["company"]
            bids = bids.filter(company__id=company)

        if "creator" in params:
            ff += 1
            creator = params["creator"]
            bids = bids.filter(creator__username=creator)

        return bids.distinct(), ff

    def define_context(request):
        context = {}
        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict
        # context["full_bar_days"] = TENDER_FULL_PROGRESS_DAYS

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    colleagues = get_colleagues(user)
    companies = Company.objects.filter(user__in=colleagues)  

    # all_bids = Bid.objects.filter(creator__in=colleagues)
    all_bids = Bid.objects.filter(
        company__in=companies,
        creator__in=colleagues,
        )

    bids, filters = filter_bids(all_bids, query_dict)
    query_dict["filters"] = filters

    sort = query_dict["sort"]

    if sort and sort != "":
        ordering = sort
    else:
        ordering = BIDS_ORDERING_FIELD

    if ordering[0] == "-":
        ordering = ordering[1:]
        bids = bids.order_by(F(ordering).asc(nulls_last=True), BIDS_ORDERING_FIELD)
    else:
        bids = bids.order_by(F(ordering).desc(nulls_last=True), BIDS_ORDERING_FIELD)

    context = define_context(request)

    bids_bond_return_overdue = bids.filter(
            bond_amount__isnull=False,
            bond_status=BondStatus.BOND_FILED,
            bond_due_date__lte=datetime.now(),
        )
    
    bids_bond_upcoming = bids.filter(
            bond_amount__isnull=False,
            bond_status=BondStatus.BOND_FILED,
        ).exclude(
            bond_due_date__lte=datetime.now(),
        )

    bids_bond_draft = bids.filter(
            bond_amount__isnull=False,
            bond_status=BondStatus.BOND_PREPARING,
        )

    bids_bond_claimed = bids.filter(
            bond_amount__isnull=False,
            bond_status=BondStatus.BOND_CLAIMED,
        )

    bids_bond_returned = bids.filter(
            bond_amount__isnull=False,
            bond_status=BondStatus.BOND_RETURNED,
        )

    bids_bond_lost = bids.filter(
            bond_amount__isnull=False,
            bond_status=BondStatus.BOND_LOST,
        )


    total_return_overdue = bids_bond_return_overdue.aggregate(total=Sum("bond_amount"))["total"] or 0
    total_upcoming = bids_bond_upcoming.aggregate(total=Sum("bond_amount"))["total"] or 0
    total_draft = bids_bond_draft.aggregate(total=Sum("bond_amount"))["total"] or 0
    total_claimed = bids_bond_claimed.aggregate(total=Sum("bond_amount"))["total"] or 0
    total_returned = bids_bond_returned.aggregate(total=Sum("bond_amount"))["total"] or 0
    total_lost = bids_bond_lost.aggregate(total=Sum("bond_amount"))["total"] or 0
    
    context["bids_bond_return_overdue"] = bids_bond_return_overdue
    context["bids_bond_upcoming"] = bids_bond_upcoming
    context["bids_bond_draft"] = bids_bond_draft
    context["bids_bond_claimed"] = bids_bond_claimed
    context["bids_bond_returned"] = bids_bond_returned
    context["bids_bond_lost"] = bids_bond_lost
    
    context["total_return_overdue"] = total_return_overdue
    context["total_upcoming"] = total_upcoming
    context["total_draft"] = total_draft
    context["total_claimed"] = total_claimed
    context["total_returned"] = total_returned
    context["total_lost"] = total_lost

    bonds_count = bids_bond_return_overdue.count()    
    bonds_count += bids_bond_upcoming.count()
    bonds_count += bids_bond_draft.count()
    bonds_count += bids_bond_claimed.count()
    bonds_count += bids_bond_returned.count()
    bonds_count += bids_bond_lost.count()

    context["colleagues"] = colleagues
    context["companies"] = companies
    context["bonds_count"] = bonds_count

    logger = logging.getLogger("portal")
    logger.info("Bonds List view")

    return render(request, "bidding/bonds-list.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tasks_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    manager = is_active_team_admin(user, team)

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)
    
    TASKS_ORDERING_FIELD = "date_due"

    def get_req_params(req):
        allowed_keys = [
            "q",
            "company",
            "creator",
            "assignee",
            "page",
            "sort",
        ]

        query_dict = {k: v for k, v in req.GET.items() if k in allowed_keys and v != ""}
        if "sort" not in query_dict:
            query_dict["sort"] = TASKS_ORDERING_FIELD

        query_string = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k != "page"
        }

        query_unsorted = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k not in ("page", "sort")
        }

        return query_dict, query_string, query_unsorted

    def filter_tasks(tasks, params):
        ff = 0
        if not params:
            return tasks.distinct(), ff

        if "q" in params:
            ff += 1
            q = params["q"]
            tasks = tasks.filter(
                Q(title__icontains=q)
                | Q(details__icontains=q)
                | Q(bid__title__icontains=q)
                | Q(bid__lot__tender__title__icontains=q)
                | Q(bid__lot__tender__reference__icontains=q)
                | Q(bid__lot__tender__client__name__icontains=q)
            )

        if "company" in params:
            ff += 1
            company = params["company"]
            tasks = tasks.filter(bid__company=company)

        if "creator" in params:
            ff += 1
            creator = params["creator"]
            tasks = tasks.filter(creator__username=creator)

        if "assignee" in params:
            ff += 1
            assignee = params["assignee"]
            tasks = tasks.filter(assignee__username=assignee)

        return tasks.distinct(), ff

    def define_context(request):
        context = {}
        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    colleagues = get_colleagues(user)
    companies = Company.objects.filter(user__in=colleagues)  

    all_tasks = Task.objects.filter(
        bid__creator__in=colleagues,
        bid__company__in=companies,
        )

    tasks, filters = filter_tasks(all_tasks, query_dict)
    query_dict["filters"] = filters

    sort = query_dict["sort"]

    if sort and sort != "":
        ordering = sort
    else:
        ordering = TASKS_ORDERING_FIELD

    if ordering[0] == "-":
        ordering = ordering[1:]
        tasks = tasks.order_by(F(ordering).asc(nulls_last=True), TASKS_ORDERING_FIELD)
    else:
        tasks = tasks.order_by(F(ordering).desc(nulls_last=True), TASKS_ORDERING_FIELD)

    context = define_context(request)


    tasks_overdue = tasks.filter(
            date_due__lte=datetime.now(),
        ).exclude(
            status=TaskStatus.TASK_FINISHED,
        ).exclude(
            status=TaskStatus.TASK_CANCELLED,
        )
    
    tasks_pending = tasks.filter(
            status=TaskStatus.TASK_PENDING,
            date_due__gt=datetime.now(),
        )

    tasks_started = tasks.filter(
            status=TaskStatus.TASK_STARTED,
            date_due__gt=datetime.now(),
        )

    tasks_finished = tasks.filter(
            status=TaskStatus.TASK_FINISHED,
        )

    tasks_cancelled = tasks.filter(
            status=TaskStatus.TASK_CANCELLED,
        )

    
    context["tasks_overdue"] = tasks_overdue
    context["tasks_pending"] = tasks_pending
    context["tasks_started"] = tasks_started
    context["tasks_finished"] = tasks_finished
    context["tasks_cancelled"] = tasks_cancelled
    

    tasks_count = tasks_overdue.count()    
    tasks_count += tasks_pending.count()
    tasks_count += tasks_started.count()
    tasks_count += tasks_finished.count()
    tasks_count += tasks_cancelled.count()

    context["colleagues"] = colleagues
    context["companies"] = companies
    context["tasks_count"] = tasks_count
    context["manager"] = manager

    logger = logging.getLogger("portal")
    logger.info("Tasks List view")

    return render(request, "bidding/tasks-list.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def expenses_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    manager = is_active_team_admin(user, team)
    
    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied") + ": " + _(" Member disabled"), status=403)
    
    EXPENSES_ORDERING_FIELD = "date_paid"

    def get_req_params(req):
        allowed_keys = [
            "q",
            "company",
            "creator",
            'amtn',
            'amtx',
            "page",
            "sort",
        ]

        query_dict = {k: v for k, v in req.GET.items() if k in allowed_keys and v != ""}
        if "sort" not in query_dict:
            query_dict["sort"] = EXPENSES_ORDERING_FIELD

        query_string = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k != "page"
        }

        query_unsorted = {
            k: v
            for k, v in req.GET.items()
            if k in allowed_keys and v != "" and k not in ("page", "sort")
        }

        return query_dict, query_string, query_unsorted

    def filter_expenses(expenses, params):
        ff = 0
        if not params:
            return expenses.distinct(), ff

        if "q" in params:
            ff += 1
            q = params["q"]
            expenses = expenses.filter(
                Q(title__icontains=q)
                | Q(reference__icontains=q)
                | Q(bill_ref__icontains=q)
                | Q(channel__icontains=q)
                | Q(mean_ref__icontains=q)
                | Q(payee__icontains=q)
                | Q(payee_ice__icontains=q)
                | Q(details__icontains=q)
                | Q(contact__name__icontains=q)
                | Q(contact__company__icontains=q)
                | Q(contact__notes__icontains=q)
                | Q(bid__title__icontains=q)
                | Q(bid__lot__tender__title__icontains=q)
                | Q(bid__lot__tender__reference__icontains=q)
                | Q(bid__lot__tender__client__name__icontains=q)
            )

        if "company" in params:
            ff += 1
            company = params["company"]
            expenses = expenses.filter(bid__company=company)

        if "creator" in params:
            ff += 1
            creator = params["creator"]
            expenses = expenses.filter(creator__username=creator)

        if "amtn" in params:
            ff += 1
            amtn = params["amtn"]
            expenses = expenses.filter(amount_paid__gte=amtn)

        if "amtx" in params:
            ff += 1
            amtx = params["amtx"]
            expenses = expenses.filter(amount_paid__lte=amtx)

        return expenses.distinct(), ff

    def define_context(request):
        context = {}
        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)

    colleagues = get_colleagues(user)
    companies = Company.objects.filter(user__in=colleagues)  

    all_expenses = Expense.objects.filter(
        bid__creator__in=colleagues,
        bid__company__in=companies,
        )

    expenses, filters = filter_expenses(all_expenses, query_dict)
    query_dict["filters"] = filters

    sort = query_dict["sort"]

    if sort and sort != "":
        ordering = sort
    else:
        ordering = EXPENSES_ORDERING_FIELD

    if ordering[0] == "-":
        ordering = ordering[1:]
        expenses = expenses.order_by(F(ordering).asc(nulls_last=True), EXPENSES_ORDERING_FIELD)
    else:
        expenses = expenses.order_by(F(ordering).desc(nulls_last=True), EXPENSES_ORDERING_FIELD)

    context = define_context(request)
    
    expenses_pending = expenses.filter(status=ExpenseStatus.XPS_PENDING)
    expenses_paid = expenses.filter(status=ExpenseStatus.XPS_PAID)
    expenses_confirmed = expenses.filter(status=ExpenseStatus.XPS_CONFIRMED)
    expenses_cancelled = expenses.filter(status=ExpenseStatus.XPS_CANCELLED)

    total_pending = expenses_pending.aggregate(total=Sum("amount_paid"))["total"] or 0
    total_paid = expenses_paid.aggregate(total=Sum("amount_paid"))["total"] or 0
    total_confirmed = expenses_confirmed.aggregate(total=Sum("amount_paid"))["total"] or 0
    total_cancelled = expenses_cancelled.aggregate(total=Sum("amount_paid"))["total"] or 0
    
    context["expenses_pending"]   = expenses_pending
    context["expenses_paid"]      = expenses_paid
    context["expenses_confirmed"] = expenses_confirmed
    context["expenses_cancelled"] = expenses_cancelled

    context["total_pending"]   = total_pending
    context["total_paid"]      = total_paid
    context["total_confirmed"] = total_confirmed
    context["total_cancelled"] = total_cancelled
    
    expenses_count = expenses_pending.count()  
    expenses_count += expenses_paid.count()
    expenses_count += expenses_confirmed.count()
    expenses_count += expenses_cancelled.count()

    context["colleagues"] = colleagues
    context["companies"] = companies
    context["expenses_count"] = expenses_count
    context["manager"] = manager

    logger = logging.getLogger("portal")
    logger.info("Expenses List view")

    return render(request, "bidding/expenses-list.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    bid = get_object_or_404(Bid, pk=pk)
    bid = Bid.objects.filter(pk=pk).prefetch_related("tasks", "expenses").first()
    if not bid:
        return HttpResponse(_("Not found"), status=404)

    if not is_team_member(bid.creator, team):
        return HttpResponse(_("Permission denied"), status=403)
    tender = bid.lot.tender
    if not tender:
        return HttpResponse(_("Not found"), status=404)

    context = {"bid": bid}

    return render(request, "bidding/bid-details.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_delete(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    logger = logging.getLogger("portal")

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied") + ": " + _(" Managers only"), status=403)

    if request.method == "POST":
        bid = None
        if pk:
            bid = get_object_or_404(Bid, pk=pk)

        # if not bid or not is_team_member(bid.creator, team):
        #     return HttpResponse(_("Permission denied"), status=403)

        redir = redirect("bidding_bids_list")
        referer = request.META.get("HTTP_REFERER", None)
        if referer:
            if url_has_allowed_host_and_scheme(
                referer,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                redir = redirect(referer)

        confirmed = request.POST.get("confirmed")
        if confirmed != "know":
            messages.error(request, _("Please confirm deletion first"))
            return redir

        if bid.status != BidStatus.BID_CANCELLED:
            messages.error(
                request, _("You can not delete a bid unless it is Cancelled")
            )
            return redir

        if bid.bond_status == BondStatus.BOND_FILED:
            messages.error(request, _("Please check the Bond status before deleting"))
            return redir

        try:
            bid.delete()
            messages.success(request, _("Bid deleted successfully"))

            logger.info("Bid delete successful")
            return redirect("bidding_bids_list")

        except Exception as xc:
            logger.error(f"Bid delete unsuccessful: {str(xc)}")
            return HttpResponse(_("Permission denied"), status=403)

    return HttpResponse(_("Bad request"), status=405)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_edit(request, pk=None, lk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    pro_context = portal_context(request)
    us = pro_context["user_settings"]

    bid = None

    if pk:
        bid = get_object_or_404(Bid, pk=pk)
        if not is_team_member(bid.creator, team):
            return HttpResponse(_("Permission denied"), status=403)
        lot = bid.lot
        tender = lot.tender
    else:
        lot = get_object_or_404(Lot, pk=lk)
        tender = lot.tender

    redir = request.GET.get("redirect", None)
    if redir and not url_has_allowed_host_and_scheme(
        redir, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        redir = None

    creator = bid.creator if bid else user
    companies = creator.companies

    if request.method == "POST":
        form = BidForm(
            request.POST,
            request.FILES,
            instance=bid,
            companies=companies,
            lot=lot,
            usets=us,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.lot = lot
            # if obj._state.adding: obj.creator = user
            obj.creator = creator
            obj.updater = user
            obj.save()

            if redir:
                return redirect(redir)

            return redirect("bidding_bids_list")
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        messages.error(request, f"{field.label}: {error}")

    if request.method == "GET":
        form = BidForm(
            instance=bid,
            companies=companies,
            lot=lot,
            usets=us,
        )

        if bid is None:  # Creating a New instance
            form.fields["date_submitted"].initial = datetime.now()
            form.fields["bid_amount"].initial = lot.estimate
            form.fields["bond_amount"].initial = lot.bond

            client_short = lot.tender.client.short
            if len(client_short) < 1:
                client_short = "[?]"
            words = lot.title.split()
            words_count = 8
            lot_title = (
                lot.title
                if len(words) <= words_count
                else " ".join(words[:words_count]) + " ..."
            )
            bid_title = client_short + " | " + lot.tender.reference + " | " + lot_title

            form.fields["title"].initial = bid_title
            if lot.description:
                desc = lot.description
                form.fields["details"].initial = desc

            if companies.count() == 1:
                form.fields["company"].initial = companies.first()

    return render(
        request,
        "bidding/bid-form.html",
        {
            "form": form,
            "object": bid,
            "tender": tender,
            "lot": lot,
            "redir": redir,
        },
    )


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def task_delete(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    logger = logging.getLogger("portal")

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied") + ": " + _(" Managers only"), status=403)

    if request.method == "POST":
        task = None
        if pk:
            task = get_object_or_404(Task, pk=pk)

        # if not is_team_member(task.creator, team):
        #     return HttpResponse(_("Permission denied") + ": " + _(" Creator is not a member"), status=403)

        bid = task.bid
        if not bid:
            return HttpResponse(_("Permission denied") + ": " + _(" Related bid not found"), status=403)

        redir = redirect("bidding_bid_details", bid.id)
        referer = request.META.get("HTTP_REFERER", None)
        if referer:
            if url_has_allowed_host_and_scheme(
                referer,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                redir = redirect(referer)

        confirmed = request.POST.get("confirmed")
        if confirmed != "know":
            messages.error(request, _("Please confirm deletion first"))
            return redir

        if task.status != TaskStatus.TASK_CANCELLED:
            messages.error(
                request, _("You can not delete a task unless it is Cancelled")
            )
            return redir

        try:
            task.delete()
            messages.success(request, _("Task deleted successfully"))
            logger.info("Task delete: successful")
            return redir

        except Exception as xc:
            logger.error(f"Task delete unsuccessful: {str(xc)}")
            return HttpResponse(_("Permission denied"), status=403)

    return HttpResponse(_("Bad request"), status=405)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def task_edit(request, pk=None, bk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    task = None

    if pk:
        task = get_object_or_404(Task, pk=pk)
        if not is_team_member(task.bid.creator, team):
            return HttpResponse(_("Permission denied"), status=403)
        bid = task.bid
    else:
        bid = get_object_or_404(Bid, pk=bk)

    redir = request.GET.get("redirect", None)
    if redir and not url_has_allowed_host_and_scheme(
        redir, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
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
            form.fields["date_due"].initial = datetime.now()

            colleagues = team.members.all()
            if colleagues.count() == 1:
                form.fields["assignee"].initial = colleagues.first()

    return render(
        request,
        "bidding/task-form.html",
        {
            "form": form,
            "object": task,
            "bid": bid,
            "redir": redir,
        },
    )


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def expense_delete(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_admin(user, team):
        return HttpResponse(_("Permission denied") + ": " + _(" Managers only"), status=403)

    logger = logging.getLogger("portal")

    if request.method == "POST":
        expense = None
        if pk:
            expense = get_object_or_404(Expense, pk=pk)

        # if not is_team_member(expense.creator, team):
        #     return HttpResponse(_("Permission denied") + ": " + _(" Creator is not a member"), status=403)

        bid = expense.bid
        if not bid:
            return HttpResponse(_("Permission denied") + ": " + _(" Related bid not found"), status=403)

        redir = redirect("bidding_bid_details", bid.id)
        referer = request.META.get("HTTP_REFERER", None)
        if referer:
            if url_has_allowed_host_and_scheme(
                referer,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                redir = redirect(referer)

        confirmed = request.POST.get("confirmed")
        if confirmed != "know":
            messages.error(request, _("Please confirm deletion first"))
            return redir

        if expense.status != ExpenseStatus.XPS_CANCELLED:
            messages.error(
                request, _("You can not delete an expense unless it is Cancelled")
            )
            return redir

        try:
            expense.delete()
            messages.success(request, _("Expense deleted successfully"))
            logger.info("Expense delete: successful")
            return redir

        except Exception as xc:
            logger.error(f"Expense delete unsuccessful: {str(xc)}")
            return HttpResponse(_("Permission denied"), status=403)

    return HttpResponse(_("Bad request"), status=405)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def expense_edit(request, pk=None, bk=None):

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    expense = None

    if pk:
        expense = get_object_or_404(Expense, pk=pk)
        if not is_team_member(expense.bid.creator, team):
            return HttpResponse(_("Permission denied"), status=403)
        bid = expense.bid
    else:
        bid = get_object_or_404(Bid, pk=bk)

    redir = request.GET.get("redirect", None)
    if redir and not url_has_allowed_host_and_scheme(
        redir, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
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
            form.fields["bill_date"].initial = datetime.now()
            form.fields["date_paid"].initial = datetime.now()

    return render(
        request,
        "bidding/expense-form.html",
        {
            "form": form,
            "object": expense,
            "bid": bid,
            "redir": redir,
        },
    )


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def bid_file(request, pk=None, ft=None):

    if not ft:
        return HttpResponse(_("Not found"), status=404)

    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse(_("Permission denied"), status=403)

    bid = None
    if pk:
        bid = get_object_or_404(Bid, pk=pk)
    if not bid:
        return HttpResponse(_("Permission denied"), status=403)

    if not is_active_team_member(user, team):
        return HttpResponse(_("Permission denied"), status=403)

    team = get_team(user)
    if not team:
        return HttpResponse(
            _("Permission denied") + ": " + _(" Team not found"), status=403
        )
    if not is_team_member(bid.creator, team):
        return HttpResponse(_("Permission denied"), status=403)

    if ft == "bond":
        file_path = bid.file_bond.url
    elif ft == "receipt":
        file_path = bid.file_receipt.url
    elif ft == "submitted":
        file_path = bid.file_submitted.url
    else:
        return HttpResponse(_("Not found"), status=404)

    file_name = os.path.basename(file_path)
    if not file_name:
        return HttpResponse(_("Permission denied"), status=403)

    response = HttpResponse()
    response["Content-Type"] = "application/octet-stream"
    response["X-Accel-Redirect"] = f"/bids/{ft}/{file_name}"
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    # response['Content-Length'] = os.path.getsize(file_path)
    return response
