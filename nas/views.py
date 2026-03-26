import os
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import serializers
from django.core.paginator import Paginator
from datetime import datetime
from django.db.models import Count, Sum, Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_control, never_cache
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)

from base.models import Agrement, Qualif
from base.context_processors import portal_context
from bidding.secu import (
        get_colleagues,
        get_or_create_team,
        is_active_team_admin,
        is_active_team_member,
        is_team_admin,
        is_team_member,
        update_membership,
    )
from nas.choices import BidStatus, BidResults, ExpenseStatus
from nas.forms import (
        CompanyForm, NewsletterSubscriptionForm,
        NotificationSubscriptionForm, UserProfileForm,
        UserSettingsForm, 
        ExpirableForm
        # ManageriatForm, SignatureKeyForm, 
    )
from nas.models import (
        Company, Newsletter, NewsletterSubscription,
        Notification, NotificationSubscription, Profile, UserSetting, 
        Expirable
        # Manageriat, SignatureKey,
    )
from nas.subbing import (subscribeUserToNewsletters, subscribeUserToNotifications)

logger_portal = logging.getLogger("portal")
COMPANIES_ITEMS_PER_PAGE = 10


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def profile_view(request):
    logger_portal.debug("Redirect to nas_at_username", extra={"request": request})
    return redirect('nas_at_username', request.user.username)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def username_view(request, username):

    uqer = request.user
    if not uqer or not uqer.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    try:
        user = (
            User.objects
            .select_related(
                'profile',
            ).prefetch_related(# 'groups', # 'user_permissions',
                # 'companies',            # Company
                'newsletters',          # NewsletterSubscription
                'notifications',        # NotificationSubscription
            )
            .get(username=uqer.username)
        )
    except:
        logger_portal.error("E404: Username not found", extra={"request": request})
        return HttpResponse("Not found", status=404)


    context = {'user': user,}
    logger_portal.info("User profile view", extra={"request": request})
    return render(request, 'nas/profile-view.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def profile_edit(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    try:
        profile = user.profile
        logger_portal.debug("Found user profile", extra={"request": request})
    except:
        logger_portal.debug("User profile not found", extra={"request": request})
        try:
            profile = Profile(user=user)
            profile.save()
            logger_portal.debug("Created user profile", extra={"request": request})
        except:
            logger_portal.error("E500: Error creating user profile", extra={"request": request})
            return HttpResponse("Server Error", status=500)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            logger_portal.info("User profile saved successfully", extra={"request": request})
            return redirect('nas_profile_view')
        else:
            logger_portal.warning("User profile form invalid", extra={"request": request})
            show_form_errors(form, request)
    else:
        logger_portal.info("User profile form view", extra={"request": request})
        form = UserProfileForm(instance=profile)

    return render(request, 'nas/profile-edit.html', {'form': form})


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def enableAllNotifications(request):
    if request.method == "POST":
        user = request.user
        notifs = user.notifications.all()

        try:
            notifs.update(active=True)
            # data = serializers.serialize('json', notifs, fields=('id', 'active', 'notification'))
            return HttpResponse(status=200)
        except Exception as e:
            return HttpResponse(content=json.dumps({'error': str(e)}), content_type='application/json', status=500)

    else:
        return HttpResponse(content=json.dumps({'error': "Method Not Allowed"}), content_type='application/json', status=405)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def enableAllNewsletters(request):
    if request.method == "POST":
        user = request.user
        newsls = user.newsletters.all()

        try:
            newsls.update(active=True)
            # data = serializers.serialize('json', newsls, fields=('id', 'active', 'newsletter'))
            return HttpResponse(status=200)
        except Exception as e:
            return HttpResponse(content=json.dumps({'error': str(e)}), content_type='application/json', status=500)

    else:
        return HttpResponse(content=json.dumps({'error': "Method Not Allowed"}), content_type='application/json', status=405)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tuneNotifications(request):
    if request.method == 'POST':
        form = NotificationSubscriptionForm(request.POST, user=request.user)
        if form.is_valid():
            # Get all subscriptions for the user
            subscriptions = NotificationSubscription.objects.filter(user=request.user)
            # Update active status based on form input
            selected_subscriptions = form.cleaned_data['subscriptions']
            for subscription in subscriptions:
                subscription.active = str(subscription.id) in selected_subscriptions
                subscription.save()
            
            redir = request.POST.get('next', request.META.get('HTTP_REFERER', None))
            if redir and not url_has_allowed_host_and_scheme(
                redir, allowed_hosts={request.get_host()},
                require_https=request.is_secure()):
                redir = None

            return redirect(redir)

    else:
        form = NotificationSubscriptionForm(user=request.user)
    
    subscriptions = NotificationSubscription.objects.filter(user=request.user).select_related('notification')

    return render(request, 'nas/profile/notifications-form.html', {
        'form': form,
        'subscriptions': subscriptions
    })


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def tuneNewsletters(request):
    if request.method == 'POST':
        form = NewsletterSubscriptionForm(request.POST, user=request.user)
        if form.is_valid():
            # Get all subscriptions for the user
            subscriptions = NewsletterSubscription.objects.filter(user=request.user)
            # Update active status based on form input
            selected_subscriptions = form.cleaned_data['subscriptions']
            for subscription in subscriptions:
                subscription.active = str(subscription.id) in selected_subscriptions
                subscription.save()
            return redirect('nas_profile_view')
    else:
        form = NewsletterSubscriptionForm(user=request.user)
    
    subscriptions = NewsletterSubscription.objects.filter(user=request.user).select_related('newsletter')

    return render(request, 'nas/profile/newsletters-form.html', {
        'form': form,
        'subscriptions': subscriptions
    })


# @login_required(login_url="account_login")
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
# def onboard(request):
#     context = {
#         'user': request.user,
#         'profile': request.user.profile,
#     }
#     return render(request, 'nas/onboard.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def companies_list(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    team = get_or_create_team(user, request)
    request.team = team

    if not team:
        logger_portal.warning("E403: Team not found", extra={"request": request})
        return HttpResponse(_("Team not found or not allowed"), status=403)

    if not is_active_team_member(user, team):
        logger_portal.warning("E403: User is not an active team member", extra={"request": request})
        return HttpResponse(_("You are not an active team member"), status=403)
    
    wassa = datetime.now()

    colleagues = get_colleagues(user)
    submitted_bids = Q(bids__status=BidStatus.BID_SUBMITTED)
    finished_bids  = Q(bids__status=BidStatus.BID_FINISHED)
    awarded_bids   = Q(bids__result=BidResults.BID_AWARDED)
    confirmed_exp  = Q(bids__expenses__status=ExpenseStatus.XPS_CONFIRMED)
    paid_exp       = Q(bids__expenses__status=ExpenseStatus.XPS_PAID)
    # started_expir  = Q(expirables__validity_start__lte = wassa)
    # unended_expir  = Q(expirables__validity_end__gte = wassa)
    current_expirs = Q(validity_start__lte = wassa, validity_end__gte = wassa)

    team_companies = Company.objects.filter(
            user__in=colleagues,
        ).annotate(
            is_mine      = Q(user=user),
            bids_sum     = Sum('bids__bid_amount', filter=(submitted_bids | finished_bids)), 
            awards_sum   = Sum('bids__bid_amount', filter=(submitted_bids | finished_bids) & awarded_bids), 
            expenses_sum = Sum('bids__expenses__amount_paid', filter=(confirmed_exp | paid_exp)), 
            # current_expirables = started_expir | unended_expir,
            # current_expirables = current_expirs,
        # ).prefetch_related(
        #     "expirables", 

        ).prefetch_related(
            Prefetch(
                "expirables",
                queryset=Expirable.objects.filter(current_expirs),
                to_attr="current_expirables"
            )

        # ).distinct(
        ).order_by("-is_mine", "user__username", "name")

    pro_context = portal_context(request)
    us = pro_context["user_settings"]

    if us:
        COMPANIES_ITEMS_PER_PAGE = int(us.general_items_per_page)
    
    paginator = Paginator(team_companies, COMPANIES_ITEMS_PER_PAGE)
    page_number = request.GET["page"] if "page" in request.GET else 1
    if not str(page_number).isdigit():
        page_number = 1
    else:
        if int(page_number) > paginator.num_pages:
            page_number = paginator.num_pages
    page_obj = paginator.page(page_number)

    context = {"page_obj": page_obj}
    logger_portal.info("Companies list view", extra={"request": request})

    print(
        '\n\n\n=================\n', 
        len(team_companies.explain(analyze=True)), 
        '\n===================\n\n\n'
        )

    return render(request, 'nas/companies/companies-list.html', context)


@method_decorator(login_required, name='dispatch')
class CompanyListView(ListView):
    model = Company
    template_name = 'nas/companies/company_list.html'
    context_object_name = 'companies'
    paginate_by = COMPANIES_ITEMS_PER_PAGE

    def get_queryset(self):
        user = self.request.user
        return Company.objects.filter(user=self.request.user, active=True)


@method_decorator(login_required, name='dispatch')
class CompanyDetailView(DetailView):
    model = Company
    template_name = 'nas/companies/company_detail.html'
    context_object_name = 'company'

    def get_queryset(self):

        assa = datetime.now().date()
        expirable_is_current     = Q(
                expirables__validity_start__isnull = False,
                expirables__validity_end__isnull = False,
                expirables__validity_start__date__lte = assa,
                expirables__validity_end__date__gt = assa,
            )

        return Company.objects.select_related(
                'user__profile'
            ).prefetch_related(
                'agrements', 'qualifs'
            ).filter(
                user=self.request.user, active=True
            ).annotate(
                expirables_count = Count('expirables', filter=expirable_is_current, distinct=True), 
            )

@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def expirable_edit(request, pk=None, ck=None):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    # team = get_or_create_team(user, request)
    # request.team = team

    if ck is None:
        logger_portal.warning("E405: Bad request parameters", extra={"request": request})
        return HttpResponse(_("Bad request or not allowed"), status=405)

    company = None
    try:
        company = Company.objects.get(pk=ck)
    except:
        logger_portal.error("E404: Exception getting Company", extra={"request": request})
        return HttpResponse(_("Not found"), status=404)

    if company is None:
        logger_portal.warning("E404: Company not found", extra={"request": request})
        return HttpResponse(_("Not found"), status=404)

    if company.user != user:
        logger_portal.warning("E403: User does not own the company", extra={"request": request})
        return HttpResponse(_("You do not own this company"), status=403)

    expirable = None

    if pk:
        try: 
            expirable = Expirable.objects.get(pk=pk)
        except:
            logger_portal.error("E404: Expirable not found", extra={"request": request})
            return HttpResponse(_("Not found"), status=404)


    redir = request.GET.get("redirect", None)
    if redir and not url_has_allowed_host_and_scheme(
        redir, allowed_hosts={request.get_host()}, 
        require_https=request.is_secure()
        ):
        redir = None

    if request.method == "POST":
        form = ExpirableForm(
            request.POST,
            request.FILES,
            instance=expirable,
            company=company,
            # bid=bid,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.company = company
            # obj.creator = user
            obj.save()
            # form.save()

            logger_portal.info("Expirable details saved", extra={"request": request})

            if redir:
                return redirect(redir)

            return redirect("nas_company_detail", company.id)
        else:
            logger_portal.warning("Submitted invalid bid form", extra={"request": request})
            for field in form:
                if field.errors:
                    for error in field.errors:
                        messages.error(request, f"{field.label}: {error}")
    else:
        form = ExpirableForm(
            instance=expirable,
            company=company,
            # bid=bid,
        )
        if expirable is None:
            form.fields["validity_start"].initial = datetime.now()
            # form.fields["date_paid"].initial = datetime.now()

            logger_portal.info("Expirable create form view", extra={"request": request})
        else:
            logger_portal.info("Expirable update form view", extra={"request": request})

    context = {
            "form": form,
            "object": expirable,
            "company": company,
            "redir": redir,
        }

    return render(request, "nas/expirable-form.html", context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def company_file(request, pk=None, ft=None):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenicated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    if not ft:
        logger_portal.warning("E404: Null file type parameter", extra={"request": request})
        return HttpResponse(_("Not found"), status=404)

    company = None
    if pk:
        company = get_object_or_404(Company, pk=pk)
    if not company:
        logger_portal.warning("E403: Company reading error", extra={"request": request})        
        return HttpResponse(_("Permission denied"), status=403)

    team = get_or_create_team(user, request)
    request.team = team


    if not team:
        logger_portal.warning("E403: Team not found", extra={"request": request})
        return HttpResponse(_("Permission denied") + ": " + _(" Team not found"), status=403)

    if not is_active_team_member(user, team):
        logger_portal.warning("E403: User not an active team member", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)
    
    if not is_team_member(company.user, team):
        logger_portal.warning("E403: Company owner not a team member", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    if ft == "file":
        file_path = company.file.url
    else:
        logger_portal.warning("E404: Wrong company file type", extra={"request": request})
        return HttpResponse(_("Not found"), status=404)

    file_name = os.path.basename(file_path)
    if not file_name:
        logger_portal.error("E404: Company file not found", extra={"request": request})
        return HttpResponse(_("File not found"), status=404)

    response = HttpResponse()
    response["Content-Type"] = "application/octet-stream"
    response["X-Accel-Redirect"] = f"/companies/{ ft }/{ file_name }"
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    logger_portal.info("Company file download authorized", extra={"request": request})
    return response


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def expirable_file(request, pk=None, ft=None):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenicated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    if not ft:
        logger_portal.warning("E404: Null file type parameter", extra={"request": request})
        return HttpResponse(_("Not found"), status=404)

    expirable = None
    if pk:
        expirable = get_object_or_404(Expirable, pk=pk)
    if not expirable:
        logger_portal.warning("E403: Expirable reading error", extra={"request": request})        
        return HttpResponse(_("Permission denied"), status=403)

    if expirable.company.user != user:
        logger_portal.warning("E403: User does not own the company", extra={"request": request})
        return HttpResponse(_("You do not own this company"), status=403)


    if ft == "file":
        file_path = expirable.file.url
    else:
        logger_portal.warning("E404: Wrong Expirable file type", extra={"request": request})
        return HttpResponse(_("Not found"), status=404)

    file_name = os.path.basename(file_path)
    if not file_name:
        logger_portal.error("E404: Expirable file not found", extra={"request": request})
        return HttpResponse(_("File not found"), status=404)

    response = HttpResponse()
    response["Content-Type"] = "application/octet-stream"
    response["X-Accel-Redirect"] = f"/expirables/{ ft }/{ file_name }"
    response["Content-Disposition"] = f'attachment; filename="{file_name}"'
    logger_portal.info("Expirable file download authorized", extra={"request": request})
    return response


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def expirable_delete(request, pk=None):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    if request.method == "POST":
        if pk:
            expirable = get_object_or_404(Expirable, pk=pk)

        company = expirable.company
        if not company:
            logger_portal.warning("E403: Related company not found", extra={"request": request})
            return HttpResponse(_("Related company not found or not allowed"), status=403)

        if company.user != user:
            logger_portal.warning("E403: User does not own the company", extra={"request": request})
            return HttpResponse(_("Permission denied"), status=403)

        redir = redirect("nas_company_detail", company.id)
        referer = request.META.get("HTTP_REFERER", None)
        if referer:
            if url_has_allowed_host_and_scheme(
                referer,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                redir = redirect(referer)

        try:
            expirable.delete()
            messages.success(request, _("Expirable deleted successfully"))
            logger_portal.info("Expirable deleted successfully", extra={"request": request})
            return redir

        except:
            logger_portal.exception(f"E405: Exception deleting Expirable", extra={"request": request})
            return HttpResponse(_("Expirable delete unsuccessful"), status=405)

    logger_portal.warning(f"E405: Bad request method", extra={"request": request})
    return HttpResponse(_("Bad request"), status=405)












@method_decorator(login_required, name='dispatch')
class CompanyCreateView(CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'nas/companies/company_form.html'
    success_url = reverse_lazy('nas_company_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Pass request.user to the form
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)
    
    def form_invalid(self, form):
        show_form_errors(form, self.request)
        return super().form_invalid(form)


@method_decorator(login_required, name='dispatch')
class CompanyUpdateView(UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'nas/companies/company_form.html'
    success_url = reverse_lazy('nas_company_list')

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user, active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Pass request.user to the form
        return kwargs

    def form_invalid(self, form):
        show_form_errors(form, self.request)
        return super().form_invalid(form)


@method_decorator(login_required, name='dispatch')
class CompanyDeleteView(DeleteView):
    model = Company
    template_name = 'nas/companies/company_confirm_delete.html'
    success_url = reverse_lazy('nas_company_list')

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def manage_company_qualifs(request, pk):
    company = get_object_or_404(Company, id=pk)
    all_qualifs = Qualif.objects.all()

    if request.method == "POST":
        selected_qualif_ids = request.POST.getlist('qualifs')
        company.qualifs.set(selected_qualif_ids)
        messages.success(request, _("Qualifs updated successfully."))
        
        return redirect('nas_company_detail', pk=company.id)
    context = {'company': company, 'all_qualifs': all_qualifs,}
    return render(request, 'nas/companies/qualifs_form.html', context)


@login_required
def manage_company_agrements(request, pk):
    company = get_object_or_404(Company, id=pk)
    all_agrements = Agrement.objects.all()

    if request.method == "POST":
        selected_agrement_ids = request.POST.getlist('agrements')
        company.agrements.set(selected_agrement_ids)
        messages.success(request, _("Agreements updated successfully."))
        
        return redirect('nas_company_detail', pk=company.id)
    context = {'company': company, 'all_agrements': all_agrements,}
    return render(request, 'nas/companies/agrements_form.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def accept_iced_company(request, pk):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    try:
        company = Company.objects.get(id=pk)
    except:
        company = None

    if company is None:
        logger_portal.error("E404: Company not found", extra={"request": request})
        return HttpResponse("Not found", status=404)

    if company.user != user:
        logger_portal.error("E403: User does not own company", extra={"request": request})
        return HttpResponse("Permission denied", status=403)

    if company.iced_company:
        if request.method == "POST":
            try:
                bemol = False
                rc = company.iced_company.get('rc', None)                
                if rc: 
                    company.rc = rc
                else: 
                    bemol = True 

                if not bemol:
                    name = company.iced_company.get('name', None)
                    if name:
                        company.name = name
                    else: 
                        bemol = True

                if not bemol:
                    city = company.iced_company.get('city', None)
                    if city: company.city = city
                    activity = company.iced_company.get('activity', None)
                    if activity: company.activity = activity
                    established = company.iced_company.get('established', None)
                    if established: company.date_est = established
                    forme = company.iced_company.get('type', None)
                    if forme: company.forme = forme

                    company.save()
                    messages.success(request, _("Data saved successfully"))
                else:
                    logger_portal.warning("Errors occurred while saving company data", extra={"request": request})
                    messages.error(request, _("Errors occurred while saving company data"))
            except:
                logger_portal.error("Exception handling verification data", extra={"request": request})
                messages.error(request, _("Verification process failed"))
        else:
            logger_portal.error("E405: Bad request method", extra={"request": request})
            return HttpResponse("Bad request", status=405)
    else:
        logger_portal.error("Could not get verification", extra={"request": request})
        messages.error(request, _("Verification process failed"))
        
    return redirect('nas_company_detail', pk=company.id)



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def user_settings(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    user_settings = UserSetting.objects.filter(user = user).first()

    if request.method == 'POST':
        if user_settings:
            if user_settings.tenders_ordering_field == 'published':
                user_settings.tenders_ordering_field == '-published'
            elif user_settings.tenders_ordering_field == '-published':
                user_settings.tenders_ordering_field == 'published'

        form = UserSettingsForm(request.POST, request.FILES, instance=user_settings)

        if form.is_valid():
            form.save()
            logger_portal.info("User settings saved successfully", extra={"request": request})
            messages.success(request, "Settings saved successfully.")

            redir = request.POST.get('next', request.META.get('HTTP_REFERER', None))
            if redir and not url_has_allowed_host_and_scheme(
                redir, allowed_hosts={request.get_host()},
                require_https=request.is_secure()):
                logger_portal.warning("Redirect not allowed, sending home instead", extra={"request": request})
                redir = "base_home"
            
            return redirect(redir)

            # next_url = request.POST.get('next', None)
            # if next_url: return redirect(next_url)

        else:
            logger_portal.warning("User settings form invalid", extra={"request": request})
            show_form_errors(form, request)
    else:
        logger_portal.info("User settings form view", extra={"request": request})
        form = UserSettingsForm(instance=user_settings)

    return render(request, 'nas/user-settings-edit.html', {'form': form})



@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_settings_reset(request):

    user = request.user
    if not user or not user.is_authenticated:
        logger_portal.warning("E403: User not authenticated", extra={"request": request})
        return HttpResponse(_("Permission denied"), status=403)

    count, _ = UserSetting.objects.filter(user = user).delete()

    if count > 0:
        logger_portal.info("User setting reset to default", extra={"request": request})
        messages.success(request, "Settings reset successfully.")
    else:
        logger_portal.warning("User setting not reset", extra={"request": request})
        messages.error(request, "Something went wrong while resetting Settings.")

    next_url = request.POST.get('next', None)
    if next_url: return redirect(next_url)
    
    next_url = request.GET.get('next', None)
    if next_url: return redirect(next_url)

    return redirect('/')



def show_form_errors(form, request):
    error_messages = []
    imagine = False
    for field, errors in form.errors.items():
        if not imagine:
            if field == 'image':
                imagine = True
        if field != 'image':
            for error in errors:
                error_messages.append(f"{field}: {error}")
    if error_messages != []:
        messages.error(request, '\n. '.join(error_messages))

    if imagine:
        messages.error(request, _("Please select an image file less than 5MB, of type PNG, JPG/JPEG, WEBP, AVIF, or GIF."))
        # messages.warning(request, _("SVG files are not allowed."))

