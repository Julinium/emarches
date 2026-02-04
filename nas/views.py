
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import serializers
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
from nas.forms import (CompanyForm, NewsletterSubscriptionForm,
                       NotificationSubscriptionForm, UserProfileForm,
                       UserSettingsForm)
from nas.models import (Company, Newsletter, NewsletterSubscription,
                        Notification, NotificationSubscription, Profile,
                        UserSetting)
from nas.subbing import (subscribeUserToNewsletters,
                         subscribeUserToNotifications)

COMPANIES_ITEMS_PER_PAGE = 10


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def profile_view(request):
    return redirect('nas_at_username', request.user.username)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def username_view(request, username):
    user = (
        User.objects
        .select_related(
            'profile',
        ).prefetch_related(# 'groups', # 'user_permissions',
            'companies',            # Company
            'newsletters',          # NewsletterSubscription
            'notifications',        # NotificationSubscription
        )
        .get(username=request.user.username)
    )

    context = {
        'user': user,
    }
    return render(request, 'nas/profile-view.html', context)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def profile_edit(request):
    user = request.user
    try:
        profile = user.profile
    except:
        profile = Profile(user=user)
        profile.save()

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('nas_profile_view')
        else:
            show_form_errors(form, request)
    else:
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


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def onboard(request):
    context = {
        'user': request.user,
        'profile': request.user.profile,
    }
    return render(request, 'nas/onboard.html', context)


@method_decorator(login_required, name='dispatch')
class CompanyListView(ListView):
    model = Company
    template_name = 'nas/companies/company_list.html'
    context_object_name = 'companies'
    paginate_by = COMPANIES_ITEMS_PER_PAGE

    def get_queryset(self):
        user = self.request.user
        team = user.teams.first()
        colleagues = team.members.filter(active = True)
        return Company.objects.filter(user__in=colleagues, active=True)
        # return Company.objects.filter(user=self.request.user, active=True)


@method_decorator(login_required, name='dispatch')
class CompanyDetailView(DetailView):
    model = Company
    template_name = 'nas/companies/company_detail.html'
    context_object_name = 'company'

    def get_queryset(self):
        return Company.objects.select_related(
                'user__profile'
            ).prefetch_related(
                'agrements', 'qualifs'
            ).filter(user=self.request.user, active=True)


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
    company = get_object_or_404(Company, id=pk)
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
                    messages.error(request, _("Errors occurred while saving data"))
            except Exception as xc:
                messages.error(request, str(xc))
                messages.error(request, _("Verification process failed") + ": Exception raised")
    else:
        messages.error(request, _("Verification process failed") + ": Got empty or no Iced")
        
    return redirect('nas_company_detail', pk=company.id)


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required
def user_settings(request):
    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse('Not allowed', status_code=403)

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
            messages.success(request, "Settings saved successfully.")

            redir = request.POST.get('next', request.META.get('HTTP_REFERER', None))
            if redir and not url_has_allowed_host_and_scheme(
                redir, allowed_hosts={request.get_host()},
                require_https=request.is_secure()):
                redir = None

            return redirect(redir)

            # next_url = request.POST.get('next', None)
            # if next_url: return redirect(next_url)

        else:
            show_form_errors(form, request)
    else:
        form = UserSettingsForm(instance=user_settings)

    return render(request, 'nas/user-settings-edit.html', {'form': form})


@login_required(login_url="account_login")
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def user_settings_reset(request):
    user = request.user
    if not user or not user.is_authenticated:
        return HttpResponse('Not allowed', status_code=403)

    count, _ = UserSetting.objects.filter(user = user).delete()

    if count > 0:
        messages.success(request, "Settings reset successfully.")
    else:
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
        messages.warning(request, _("SVG files are not allowed for security reasons."))

