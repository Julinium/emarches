
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404, redirect

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.core import serializers
import json

from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from django.contrib.auth.models import User

from base.models import Agrement, Qualif
from nas.models import Profile, Company, Notification, NotificationSubscription, Newsletter, NewsletterSubscription
from nas.forms import UserProfileForm, CompanyForm, NotificationSubscriptionForm, NewsletterSubscriptionForm
from nas.subbing import subscribeUserToNotifications, subscribeUserToNewsletters


COMPANIES_ITEMS_PER_PAGE = 10


@login_required
def profile_view(request):
    return redirect('nas_at_username', request.user.username)


@login_required
def username_view(request, username):
    try:
        user_arg = User.objects.select_related('profile').prefetch_related(
            'newsletters', 'notifications', 'companies').get(username=username)
    except User.DoesNotExist:
        user_arg = None
        # Return 403, not 404, to prevent checking if a certain username exists.
        return HttpResponse("Not allowed", status=403)

    user = request.user

    if user_arg != user:
        return HttpResponse("Not allowed", status=403)

    try:
        profile = user.profile
    except:
        profile = Profile(user=user)
        profile.save()

    # companies = user.companies
    subscribeUserToNotifications(user)
    subscribeUserToNewsletters(user)
    noti_subs = user.notifications.all()
    newl_subs = user.newsletters.all()

    nofif_disabled = noti_subs.filter(active=False).first() != None
    newsl_disabled = newl_subs.filter(active=False).first() != None


    context = {
        'user': user,
        'profile': user.profile,
        # 'companies': companies,
        # 'notifications': noti_subs,
        'notif_disabled': nofif_disabled,
        # 'newsletters': newl_subs,
        'newsl_disabled': newsl_disabled
    }
    # messages.success(request, "Your personal data is kept private.")
    # messages.success(request, "Only your username and avatar may be seen by other users.")
    return render(request, 'nas/profile-view.html', context)


@login_required
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
            # for field, errors in form.errors.items():
            #     for error in errors:
            #         messages.error(request, f"{field}: {error}")
    else:
        form = UserProfileForm(instance=profile)
    # messages.success(request, "Your personal data is kept private.")
    # messages.success(request, "Only your username and avatar may be seen by other users.")
    return render(request, 'nas/profile-edit.html', {'form': form})


@login_required
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


@login_required
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


@login_required
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
            return redirect('nas_profile_view')
    else:
        form = NotificationSubscriptionForm(user=request.user)
    
    subscriptions = NotificationSubscription.objects.filter(user=request.user).select_related('notification')

    return render(request, 'nas/profile/notifications-form.html', {
        'form': form,
        'subscriptions': subscriptions
    })


@login_required
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


@login_required
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
        return Company.objects.filter(user=self.request.user, active=True)


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


@login_required
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


@login_required
def accept_iced_company(request, pk):
    company = get_object_or_404(Company, id=pk)
    # all_qualifs = Qualif.objects.all()
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

