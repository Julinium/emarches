
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404, redirect
# from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from django.contrib.auth.models import User

from nas.models import Profile, Company, Notification, NotificationSubscription
from nas.forms import UserProfileForm, CompanyForm


COMPANIES_ITEMS_PER_PAGE = 10


@login_required
def profile_view(request):
    return redirect('nas_at_username', request.user.username)


@login_required
def username_view(request, username):
    try:
        user_arg = User.objects.get(username=username)
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
    companies = user.companies

    noti_subs = user.notifications.all()

    ######################
    # for notif in noti_subs:
    #     notif.rank = notif.notification.rank
    #     notif.save()
    ######################
    

    context = {
        'user': user,
        'profile': user.profile,
        'companies': companies,
        'notifications': noti_subs
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
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{error}")
    else:
        form = UserProfileForm(instance=profile)
    # messages.success(request, "Your personal data is kept private.")
    # messages.success(request, "Only your username and avatar may be seen by other users.")
    return render(request, 'nas/profile-edit.html', {'form': form})


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
        return Company.objects.filter(user=self.request.user, active=True)


@method_decorator(login_required, name='dispatch')
class CompanyCreateView(CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'nas/companies/company_form.html'
    success_url = reverse_lazy('nas_company_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class CompanyUpdateView(UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'nas/companies/company_form.html'
    success_url = reverse_lazy('nas_company_list')

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user, active=True)

    def form_invalid(self, form):
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field}: {error}")
        messages.error(self.request, f"Form submission failed: {', '.join(error_messages)}")
        return super().form_invalid(form)


@method_decorator(login_required, name='dispatch')
class CompanyDeleteView(DeleteView):
    model = Company
    template_name = 'nas/companies/company_confirm_delete.html'
    success_url = reverse_lazy('nas_company_list')

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user)
