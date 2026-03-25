import json
import logging
import os

from datetime import datetime

from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.core.paginator import Paginator

from django.db.models import Count, Exists, F, OuterRef, Q, Sum, Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from django.utils.translation import gettext_lazy as trans
from django.views.decorators.cache import cache_control

from base.context_processors import portal_context
from base.models import (
        Agrement, Category, Client, Crawler, FileToGet, 
        Deposit, Domain, Procedure, Qualif, Tender,
    )
from base.texter import normalize_text
from bidding.models import Bid
from bidding.secu import get_colleagues
from nas.models import Company, Download, Favorite, TenderView

# Default Settings
TENDER_FULL_PROGRESS_DAYS = settings.TENDER_FULL_PROGRESS_DAYS
TENDERS_ITEMS_PER_PAGE = 10
CLIENTS_ITEMS_PER_PAGE = 20
TENDERS_ORDERING_FIELD = "deadline"
SHOW_TODAYS_EXPIRED = True
SHOW_CANCELLED = True
LINK_PREFIX = settings.LINK_PREFIX
RABAT_TZ = ZoneInfo("Africa/Casablanca")

DCE_SHOW_MODAL = True

logger_portal = logging.getLogger("portal")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    pro_context = portal_context(request)
    us = pro_context["user_settings"]
    if us:
        TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
        TENDERS_ORDERING_FIELD = us.tenders_ordering_field
        TENDERS_ITEMS_PER_PAGE = int(us.tenders_items_per_page)
        SHOW_TODAYS_EXPIRED = us.tenders_show_expired
        SHOW_CANCELLED = us.tenders_show_cancelled

    def get_req_params(req):
        query_pars = req.GET.items()
        allowed_keys = [
            "q",
            "f",
            "estin",
            "estix",
            "bondn",
            "bondx",
            "ddlnn",
            "ddlnx",
            "publn",
            "publx",
            "allotted",
            "category",
            "procedure",
            "ebid",
            "esign",
            "pme",
            "variant",
            "agrements",
            "qualifs",
            "samples",
            "meetings",
            "visits",
            "page",
            "sort",
            "results",
            "exact",
        ]

        query_dict = {k: v for k, v in query_pars if k in allowed_keys and v != ""}

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

        if "ddlnn" not in query_dict:
            # if query_unsorted == {}:
            query_dict["ddlnn"] = datetime.now(RABAT_TZ).date().strftime("%Y-%m-%d")

        return query_dict, query_string, query_unsorted

    def filter_tenders(tenders, params, user):

        def afas(queryset, field_names, phrase):
            phrase = normalize_text(phrase, False)
            words = [word.strip() for word in phrase.split() if word.strip()]
            if words:
                or_query = Q()
                for field in field_names:
                    field_q = Q()
                    for word in words:
                        field_q &= Q(**{f"{field}__icontains": word})
                    or_query |= field_q
                queryset = queryset.filter(or_query)

            return queryset

        ff = 0

        if not params or not user:
            return tenders.distinct(), ff

        if not SHOW_CANCELLED:
            tenders = tenders.filter(cancelled=False)

        if "q" in params:
            ff += 1
            q = params["q"]
            if "f" in params:
                match params["f"]:
                    case "client":
                        tenders = tenders.filter(client__name__icontains=q)
                    case "location":
                        tenders = tenders.filter(location__icontains=q)
                    case "reference":
                        tenders = afas(tenders, ["refwords"], q)
                    case "domains":
                        if "exact" in params:
                            tenders = tenders.filter(domains__name=q)
                        else:
                            tenders = afas(tenders, ["domwords"], q)
                    case _:
                        tenders = afas(tenders, ["keywords"], q)
            else:
                tenders = afas(
                    tenders,
                    ["keywords", "cliwords", "locwords", "refwords", "domwords"],
                    q,
                )

        if "estin" in params:
            ff += 1
            estin = params["estin"]
            tenders = tenders.filter(estimate__gte=estin)
        if "estix" in params:
            ff += 1
            estix = params["estix"]
            tenders = tenders.filter(estimate__lte=estix)

        if "bondn" in params:
            ff += 1
            bondn = params["bondn"]
            tenders = tenders.filter(bond__gte=bondn)
        if "bondx" in params:
            ff += 1
            bondx = params["bondx"]
            tenders = tenders.filter(bond__lte=bondx)

        if "ddlnn" in params:
            ddlnn = params["ddlnn"]
            tenders = tenders.filter(deadline__gte=ddlnn)
            if ddlnn == datetime.now(RABAT_TZ).strftime("%Y-%m-%d"):
                if not SHOW_TODAYS_EXPIRED:
                    tenders = tenders.exclude(deadline__lt=datetime.now(RABAT_TZ))
            else:
                ff += 1

        if "ddlnx" in params:
            ff += 1
            ddlnx = params["ddlnx"]
            tenders = tenders.filter(deadline__date__lte=ddlnx)

        if "publn" in params:
            ff += 1
            publn = params["publn"]
            tenders = tenders.filter(published__gte=publn)
        if "publx" in params:
            ff += 1
            publx = params["publx"]
            tenders = tenders.filter(published__lte=publx)

        if "allotted" in params:
            ff += 1
            allotted = params["allotted"]
            if allotted == "single":
                tenders = tenders.filter(lots_count=1)
            if allotted == "multi":
                tenders = tenders.filter(lots_count__gt=1)

        if "pme" in params:
            ff += 1
            pme = params["pme"]
            if pme == "reserved":
                tenders = tenders.filter(reserved=True)
            if pme == "open":
                tenders = tenders.filter(reserved=False)

        if "category" in params:
            ff += 1
            category = params["category"]
            tenders = tenders.filter(category__id=category)

        if "procedure" in params:
            ff += 1
            procedure = params["procedure"]
            tenders = tenders.filter(procedure__id=procedure)

        if "ebid" in params:
            ff += 1
            ebid = params["ebid"]
            if ebid == "required":
                tenders = tenders.filter(ebid=1)
            if ebid == "optional":
                tenders = tenders.filter(ebid=0)
            if ebid == "na":
                tenders = tenders.exclude(ebid=0).exclude(ebid=1)

        if "variant" in params:
            ff += 1
            variant = params["variant"]
            if variant == "accepted":
                tenders = tenders.filter(variant=True)
            if variant == "rejected":
                tenders = tenders.filter(variant=False)

        if "samples" in params:
            ff += 1
            samples = params["samples"]
            if samples == "required":
                tenders = tenders.filter(has_samples=True)
            if samples == "na":
                tenders = tenders.filter(has_samples=False)

        if "meetings" in params:
            ff += 1
            meetings = params["meetings"]
            if meetings == "required":
                tenders = tenders.filter(has_meetings=True)
            if meetings == "na":
                tenders = tenders.filter(has_meetings=False)

        if "visits" in params:
            ff += 1
            visits = params["visits"]
            if visits == "required":
                tenders = tenders.filter(has_visits=True)
            if visits == "na":
                tenders = tenders.filter(has_visits=False)

        if "agrements" in params:
            ff += 1
            agrements = params["agrements"]
            if agrements == "required":
                tenders = tenders.filter(has_agrements=True)
            if agrements == "na":
                tenders = tenders.filter(has_agrements=False)
            if agrements == "companies":
                if user.is_authenticated:
                    user_agrements = Agrement.objects.filter(companies__user=user)
                    tenders = tenders.filter(lots__agrements__in=user_agrements)

        if "qualifs" in params:
            ff += 1
            qualifs = params["qualifs"]
            if qualifs == "required":
                tenders = tenders.filter(has_qualifs=True)
            if qualifs == "na":
                tenders = tenders.filter(has_qualifs=False)
            if qualifs == "companies":
                if user.is_authenticated:
                    user_qualifs = Qualif.objects.filter(companies__user=user)
                    tenders = tenders.filter(lots__qualifs__in=user_qualifs)

        if "results" in params:
            ff += 1
            results = params["results"]
            if results == "with_minutes":
                tenders = tenders.filter(openings__isnull=False)
            if results == "no_minutes":
                tenders = tenders.filter(openings__isnull=True)

            winners = Deposit.objects.filter(
                opening__tender=OuterRef("pk"), winner=True
            ).values("pk")

            if results == "partial":
                tenders = (
                    tenders.filter(openings__isnull=False)
                    .annotate(
                        has_winner=Exists(winners),
                        failed_lots=Count(
                            "openings",
                            filter=~Q(openings__deposits__winner=True),
                            distinct=True,
                        ),
                    )
                    .filter(has_winner=True, failed_lots__gt=0)
                )

            if results == "unsuccessful":
                tenders = (
                    tenders.filter(openings__isnull=False)
                    .annotate(
                        has_winner=Exists(winners),
                    )
                    .filter(has_winner=False)
                )

        return tenders.distinct(), ff

    def define_context(request):
        context = {}

        all_categories = Category.objects.all()
        all_procedures = Procedure.objects.all()

        last_crawler = (
            Crawler.objects.filter(saving_errors=False, import_links=False)
            .order_by("finished")
            .last()
        )
        last_updated = last_crawler.finished if last_crawler else None

        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict

        context["procedures"] = all_procedures
        context["full_bar_days"] = TENDER_FULL_PROGRESS_DAYS
        context["last_updated"] = last_updated

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)
    all_tenders = Tender.objects.all()
    tenders, filters = filter_tenders(all_tenders, query_dict, request.user)

    sort = query_dict["sort"]

    if sort and sort != "":
        ordering = [sort]
        if sort == "published":
            ordering = ["-published"]
        if sort == "-published":
            ordering = ["published"]
    else:
        ordering = []

    ordering.append("-created")

    query_dict["filters"] = filters

    if "minutes_end" in ordering or "-minutes_end" in ordering:
        tenders = tenders.annotate(minutes_end=F("openings__date"))

    colleagues = get_colleagues(user)

    tenders = (
        tenders.prefetch_related(
            "favorites",
            "views",
            "openings",
            "downloads",
            "changes",
        )
        .select_related("client", "category", "mode", "procedure")
        .annotate(
            team_bids=Count(
                "lots__bids",
                filter=Q(lots__bids__creator__in=colleagues),
                distinct=True,
            )
        )
        .order_by(*ordering)
    )

    context = define_context(request)

    paginator = Paginator(tenders, TENDERS_ITEMS_PER_PAGE)
    page_number = query_dict["page"] if "page" in query_dict else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context["page_obj"] = page_obj
    context["colleagues"] = colleagues

    logger_portal.info("Tenders list view", extra={"request": request})
    return render(request, "portal/tender-list.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_details_chrono(request, ch=None):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    if not ch:
        logger_portal.warning("E405: Bad request parameter", extra={"request": request})
        return HttpResponse(trans("Bad request"), status=405)

    tender = get_object_or_404(Tender, chrono=ch)

    logger_portal.info("Tenders details chrono redirect", extra={"request": request})
    return redirect("portal_tender_details", tender.id)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_details(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    tender = get_object_or_404(
        Tender.objects.select_related(
            "client", "category", "mode", "procedure"
        ).prefetch_related(
            "downloads",
            "views",
            "favorites",
            "openings",
            "domains",
            "lots",
            "lots__agrements",
            "lots__qualifs",
            "lots__meetings",
            "lots__samples",
            "lots__visits",
            # "lots__bids",
            # "bids",
        ),
        id=pk,
    )

    # if not tender:
    #     return HttpResponse(trans("Not found"), status=404)

    favorited = tender.favorites.filter(user=user).first()

    pro_context = portal_context(request)
    us = pro_context["user_settings"]
    full_bar_days = (
        int(us.tenders_full_bar_days)
        if us.tenders_full_bar_days
        else TENDER_FULL_PROGRESS_DAYS
    )

    colleagues = get_colleagues(user)
    companies = Company.objects.filter(user__in=colleagues)

    bids = (
        Bid.objects.filter(
            lot__tender=tender, 
            creator__in=colleagues,
            company__in=companies,
        ).distinct().order_by("lot", "bid_amount", "date_submitted")
    )

    context = {
        "tender": tender,
        "link_prefix": LINK_PREFIX,
        "dce_modal": DCE_SHOW_MODAL,
        "full_bar_days": full_bar_days,
        "favorited": favorited,
        "bids": bids,
    }

    TenderView.objects.create(
        tender=tender,
        user=user,
    )

    tolerance_dn = 25.0
    if tender.category.label == "Travaux":
        tolerance_dn = 20.0
    tolerance_up = 20.0
    offers_count = 1

    context["offer_litteral"] = trans("OFFER")
    context["offers_count"] = max(offers_count, 1)
    context["tolerance_dn"] = tolerance_dn
    context["tolerance_up"] = tolerance_up

    logger_portal.info("Tenders details view", extra={"request": request})
    return render(request, "portal/tender-details.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_get_file(request, pk=None, fn=None):

    if request.method != "GET":
        logger_portal.warning("E405: Bad request method", extra={"request": request})
        return HttpResponse(trans("Bad request"), status=405)

    if pk is None or fn is None:
        logger_portal.warning("E405: Bad request paramters", extra={"request": request})
        return HttpResponse(trans("Bad request"), status=405)

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    tender = get_object_or_404(Tender, id=pk)
    # if not tender:
    #     return HttpResponse(trans("Not found"), status=404)

    dce_dir = os.path.join(
        os.path.join(settings.DCE_MEDIA_ROOT, "dce"),
        settings.DL_PATH_PREFIX + tender.chrono,
    )
    file_path = os.path.join(
        os.path.join("dce", settings.DL_PATH_PREFIX + tender.chrono), fn
    )
    file_fp = os.path.join(dce_dir, fn)

    # TODO: Allow users to request files for Tenders if not found. 
    # In such case, add a FileToGet instance if not already added.

    if os.path.exists(file_fp):
        file_size = os.path.getsize(file_fp)
        response = HttpResponse()
        response["Content-Type"] = "application/octet-stream"
        response["X-Accel-Redirect"] = f"/dce/{file_path}"
        response["Content-Disposition"] = f'attachment; filename="{fn}"'
        response["Content-Length"] = os.path.getsize(file_fp)
        Download.objects.create(
            tender=tender,
            user=user,
            size_read=tender.size_read,
            size_bytes=file_size if file_size else tender.size_bytes,
        )

        logger_portal.info("Tenders file download launched", extra={"request": request})
        return response

    logger_portal.warning("File not found", extra={"request": request})
    return HttpResponse(trans("Not found"), status=404)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_req_file(request, pk=None):

    if request.method != "POST":
        logger_portal.warning("E405: Bad request method", extra={"request": request})
        return HttpResponse(trans("Bad request"), status=405)

    if pk is None:
        logger_portal.warning("E405: Bad request paramters", extra={"request": request})
        return HttpResponse(trans("Not found"), status=405)

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    tender = get_object_or_404(Tender, id=pk)
    # if not tender:
    #     return HttpResponse(trans("Not found"), status=404)

    logger_portal.info("Tender Files requested", extra={"request": request})

    file_to_get = FileToGet.objects.filter(tender=tender).first()
    if not file_to_get:
        file_to_get = FileToGet.objects.create(tender=tender, reason='Requested')
        return HttpResponse(tender.id, status=200)

    # logger_portal.info("Tender Files already requested", extra={"request": request})
    return HttpResponse(tender.id, status=201)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_favorite(request, pk=None):

    if request.method != "POST":
        logger_portal.warning("E405: Bad request method", extra={"request": request})
        return HttpResponse(trans("Bad request"), status=405)

    if pk is None:
        logger_portal.warning("E405: Bad request paramters", extra={"request": request})
        return HttpResponse(trans("Not found"), status=405)

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    tender = get_object_or_404(Tender, id=pk)
    # if not tender:
    #     return HttpResponse(trans("Not found"), status=404)

    favorited = Favorite.objects.filter(tender=tender, user=user).first()
    if not favorited:
        favorited = Favorite.objects.create(
            user=user,
            tender=tender,
        )
        logger_portal.info("Tender added to Favorites", extra={"request": request})
        return HttpResponse(tender.id, status=200)

    logger_portal.warning("E500: Failed Tender Favorite", extra={"request": request})
    return HttpResponse(trans("Failed adding Tender to Favorites"), status=500)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_unfavorite(request, pk=None):

    if request.method != "POST":
        logger_portal.warning("E405: Bad request method", extra={"request": request})
        return HttpResponse(trans("Bad request"), status=405)

    if pk is None:
        logger_portal.warning("E405: Bad request paramters", extra={"request": request})
        return HttpResponse(trans("Not found"), status=405)

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    tender = get_object_or_404(Tender, id=pk)
    # if not tender:
    #     return HttpResponse(trans("Not found"), status=404)

    deleted, _ = Favorite.objects.filter(tender=tender, user=user).delete()
    if deleted > 0:
        logger_portal.info("Tender removed from Favorites", extra={"request": request})
        return HttpResponse(tender.id, status=200)

    logger_portal.warning("E500: Failed removing Tender from favorites", extra={"request": request})
    return HttpResponse(trans("Failed removing Tender from favorites"), status=500)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_favorite_clean(request, span=None):

    if request.method != "POST":
        logger_portal.warning("E405: Bad request method", extra={"request": request})
        return HttpResponse(trans("Bad request"), status=405)

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    cleanables = None
    if span:
        if span == "all":
            cleanables = user.favorites.all()
        if span == "cancelled":
            cleanables = user.favorites.filter(tender__cancelled=True)
        if span == "expired":
            wassa = datetime.now(RABAT_TZ)
            cleanables = user.favorites.filter(tender__deadline__lt=wassa)

    if cleanables:
        trash, xxx = cleanables.delete()
        logger_portal.info(f"Favorite Tender Cleanup: { trash }", extra={"request": request})
        messages.success(request, trans("Favorite items cleaned") + f": {trash}")
    else:
        logger_portal.info("No favorites cleaned up", extra={"request": request})
        messages.warning(request, trans("Nothing to clean up."))

    return redirect("portal_tender_favorite_list")


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tender_favorite_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    pro_context = portal_context(request)
    us = pro_context["user_settings"]
    if us:
        TENDER_FULL_PROGRESS_DAYS = int(us.tenders_full_bar_days)
        TENDERS_ORDERING_FIELD = us.tenders_ordering_field
        TENDERS_ITEMS_PER_PAGE = int(us.tenders_items_per_page)

    sort = request.GET.get("sort", TENDERS_ORDERING_FIELD)
    page = request.GET.get("page", None)
    query_dict = {"sort": sort, "page": page}
    query_string = {"sort": sort}
    query_unsorted = {}

    sort = request.GET.get("sort", TENDERS_ORDERING_FIELD)

    if sort and sort != "":
        ordering = [sort]
    else:
        ordering = []

    ordering.append("id")

    pontext = portal_context(request)
    faved_ids = pontext.get("faved_ids", None)

    tenders = Tender.objects.filter(id__in=faved_ids)

    colleagues = get_colleagues(user)

    tenders = (
        tenders.select_related("client", "category", "mode", "procedure")
        .prefetch_related(
            "favorites",
            "views",
            "downloads",
            "changes",
        )
        .annotate(
            team_bids=Count(
                "lots__bids",
                filter=Q(lots__bids__creator__in=colleagues),
                distinct=True,
            )
        )
        .order_by(*ordering)
    )

    context = {}
    context["query_string"] = urlencode(query_string)
    context["query_unsorted"] = urlencode(query_unsorted)
    context["query_dict"] = query_dict
    context["full_bar_days"] = TENDER_FULL_PROGRESS_DAYS

    paginator = Paginator(tenders, TENDERS_ITEMS_PER_PAGE)
    page_number = query_dict["page"] if "page" in query_dict else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context["page_obj"] = page_obj
    logger_portal.info("Favorite Tender List view", extra={"request": request})
    return render(request, "portal/tender-favorite-list.html", context)


@login_required(login_url="account_login")
def locations_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    json_path = os.path.join(settings.BASE_DIR, "scraper", "data", "regions-cities.json")

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            states = json.load(f)
    except FileNotFoundError:
        states = []
        logger_portal.exception("E500: Locations json not found", extra={"request": request})
        return HttpResponse("Locations list not found", code=500)
        # Or raise a 404 / show error page
    except json.JSONDecodeError:
        states = []
        logger_portal.exception("E500: Failed reading locations json", extra={"request": request})
        return HttpResponse("Locations list not found", code=500)
        # Handle corrupted JSON

    context = {"states": states}

    logger_portal.info("Locations List view", extra={"request": request})
    return render(request, "portal/locations-list.html", context)


@login_required(login_url="account_login")
def client_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    pro_context = portal_context(request)
    us = pro_context["user_settings"]
    if us:
        CLIENTS_ITEMS_PER_PAGE = int(us.general_items_per_page)
    CLIENTS_ORDERING_FIELD = "latest_published"

    def get_req_params(req):
        allowed_keys = ["q", "page", "sort",]

        query_dict = {k: v for k, v in req.GET.items() if k in allowed_keys and v != ""}
        if "sort" not in query_dict:
            query_dict["sort"] = CLIENTS_ORDERING_FIELD

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

    def filter_clients(clients, params):
        ff = 0
        if not params:
            return clients.distinct(), ff

        if "q" in params:
            ff += 1
            q = params["q"]
            clients = clients.filter(name__icontains=q)
        return clients.distinct(), ff

    def define_context(request):
        context = {}
        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)
    assa = timezone.now()
    ongoing_tenders = Q(
            tenders__deadline__gte=assa, 
            # tenders__cancelled=False,
        )
    all_clients = Client.objects.annotate(
            all_tenders_count=Count("tenders"),
            all_total_estimate=Sum("tenders__estimate", default=0),
            tenders_count=Count("tenders", filter=ongoing_tenders),
            total_estimate=Sum("tenders__estimate", filter=ongoing_tenders, default=0),
            latest_published = Max("tenders__published")
        ).filter(
            all_tenders_count__gt=0
        )

    clients, filters = filter_clients(all_clients, query_dict)

    sort = query_dict["sort"]
    ordering = []
    if sort and sort != "":
        ordering = [sort] # Invert sort keys, except Name
        if sort not in ["name", "-name", "short", "-short"]:
            if sort[0] == "-" :
                ordering = [sort[1:]]
            else:
                ordering = [f"-{ sort }"]
            # ordering.append("short")

        if sort in ["latest_published", "-latest_published"]:
            ordering.append("-tenders_count")
            ordering.append("-all_tenders_count")


    query_dict["filters"] = filters

    clients = clients.order_by(*ordering)

    context = define_context(request)

    paginator = Paginator(clients, CLIENTS_ITEMS_PER_PAGE)
    page_number = request.GET["page"] if "page" in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    for obj in page_obj:
        obj.estimate_average = (
            round(obj.all_total_estimate / obj.all_tenders_count, 2)
            if obj.all_tenders_count != 0
            else Decimal("0")
        )

    context["page_obj"] = page_obj
    # context["clients"] = clients

    logger_portal.info("Clients List view", extra={"request": request})
    return render(request, "portal/clients-list.html", context)


@login_required(login_url="account_login")
def domain_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(trans("Permission denied"), status=403)

    pro_context = portal_context(request)
    us = pro_context["user_settings"]
    if us:
        CLIENTS_ITEMS_PER_PAGE = int(us.tenders_items_per_page)
        SHOW_CANCELLED = us.tenders_show_cancelled
    CLIENTS_ORDERING_FIELD = "tenders_count"

    def get_req_params(req):
        allowed_keys = [
            "q",
            "page",
            "sort",
        ]

        query_dict = {k: v for k, v in req.GET.items() if k in allowed_keys and v != ""}
        if "sort" not in query_dict:
            query_dict["sort"] = CLIENTS_ORDERING_FIELD

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

    def filter_domains(domains, params):
        ff = 0
        if not params:
            return domains.distinct(), ff

        if "q" in params:
            ff += 1
            q = params["q"]
            domains = domains.filter(name__icontains=q)
        return domains.distinct(), ff

    def define_context(request):
        context = {}
        context["query_string"] = urlencode(query_string)
        context["query_unsorted"] = urlencode(query_unsorted)
        context["query_dict"] = query_dict

        return context

    query_dict, query_string, query_unsorted = get_req_params(request)
    assa = timezone.now()

    if SHOW_CANCELLED:
        silter = Q(tenders__deadline__gte=assa)
    else:
        silter = Q(tenders__deadline__gte=assa, tenders__cancelled=False)

    all_domains = Domain.objects.annotate(
        tenders_count=Count("tenders", filter=silter),
        total_estimate=Sum("tenders__estimate", filter=silter),
    ).filter(tenders_count__gt=0)

    domains, filters = filter_domains(all_domains, query_dict)

    sort = query_dict["sort"]

    if sort and sort != "":
        ordering = [sort]
        if sort == "tenders_count":
            ordering = ["-tenders_count"]
        if sort == "-tenders_count":
            ordering = ["tenders_count"]
        if sort == "total_estimate":
            ordering = ["-total_estimate"]
        if sort == "-total_estimate":
            ordering = ["total_estimate"]
    else:
        ordering = []

    query_dict["filters"] = filters

    domains = domains.order_by(*ordering)

    context = define_context(request)

    paginator = Paginator(domains, CLIENTS_ITEMS_PER_PAGE)
    page_number = request.GET["page"] if "page" in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context["page_obj"] = page_obj
    context["domains"] = domains

    logger_portal.info("Domains List view", extra={"request": request})
    return render(request, "portal/domains-list.html", context)
