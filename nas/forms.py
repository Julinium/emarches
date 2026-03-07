from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from bidding.widgets import FilenameOnlyClearableFileInput

from .iceberg import get_ice_checkup
from .models import (Company, Favorite, Folder, NotificationSubscription,
                     Profile, UserSetting, Manageriat, SignatureKey, Expirable)

ALLOW_INVALID_ICE = True


class UserProfileForm(forms.ModelForm):

    username = forms.CharField(max_length=150, required=True, label=_('Username'))
    first_name = forms.CharField(max_length=150, required=False, label=_('First Name'))
    last_name = forms.CharField(max_length=150, required=False, label=_('Last Name'))
    clear_image = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Profile
        fields = [
            'username', 'first_name', 'last_name', 'image',
            'phone', 'whatsapp', 'about', 'clear_image'
            ]
        labels = {
            'image': _('Avatar'),
            'phone': _('Phone'),
            'whatsapp': _('Whatsapp'),
            'about': _('About'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        clear_image = cleaned_data.get('clear_image')

        if clear_image:
            cleaned_data['image'] = None
        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image')
        return image

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()
            if self.cleaned_data.get('clear_image'):
                profile.image = None
            profile.save()
        return profile


class UserSettingsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = UserSetting
        fields = [
            'general_wrap_long_text',
            'general_items_per_page',
            'general_show_invitations',
            
            'tenders_ordering_field', 
            'tenders_items_per_page', 
            'tenders_full_bar_days', 
            'tenders_show_expired', 
            'tenders_show_cancelled',

            'bidding_check_deadline', 
            'bidding_check_amount', 
            'bidding_check_bond', 

            'p_orders_ordering_field', 
            'p_orders_items_per_page', 
            'p_orders_full_bar_days', 
            'p_orders_show_expired', 
            'p_orders_first_articles',
            ]


class CompanyForm(forms.ModelForm):

    clear_image = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Company
        fields = [
            'name', 'forme', 'ice', 'rc', 'address', 'email', 'website', 
            'activity', 'file', 'note', 'image', 'clear_image']

        widgets = {
            'date_est': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'note': forms.Textarea(attrs={'rows': 3}),
            "file"     : FilenameOnlyClearableFileInput,
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
    
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.label_suffix = ""


    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        ice = cleaned_data.get('ice')
        image = cleaned_data.get('image')
        clear_image = cleaned_data.get('clear_image')

        if clear_image:
            cleaned_data['image'] = None

        if name and self.user:
            existing_company = Company.objects.filter(user=self.user, name=name).exclude(
                pk=self.instance.pk if self.instance else None).exists()
            if existing_company:
                raise ValidationError({
                    'name': _('The name is already taken.')
                })
                
        if not ALLOW_INVALID_ICE:
            if not self.ice_checkup_valid():
                raise ValidationError({
                    'ice': _('The ICE is not valid.')
                })

        return cleaned_data

    def save(self, commit=True):
        company = super().save(commit=False)
        if commit:
            if self.cleaned_data.get('clear_image'):
                company.image = None
            company.save()
        return company

    def clean_image(self):
        image = self.cleaned_data.get('image')
        return image
    
    def ice_checkup_valid(self):
        ice = self.cleaned_data.get('ice')
        if not ice: return False
        cj = get_ice_checkup(ice)
        if not cj: return False
        return cj.get('n2') == cj.get('cs')


class ManageriatForm(forms.ModelForm):

    class Meta:
        model = Manageriat
        fields = [
            'company', 'name', 'identity',
            'validity_start', 'validity_end', 'file',
            ]

        widgets = {
            'validity_start': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'validity_end': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'note': forms.Textarea(attrs={'rows': 8}),
        }

    # def __init__(self, *args, user=None, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.user = user


class SignatureKeyForm(forms.ModelForm):

    class Meta:
        model = SignatureKey
        fields = [
            'company', 'name', "serial", "issuer", "holder", "owner",
            'validity_start', 'validity_end', "file", "note",
            ]

        widgets = {
            'validity_start': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'validity_end': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'note': forms.Textarea(attrs={'rows': 8}),
        }


class ExpirableForm(forms.ModelForm):

    class Meta:
        model = Expirable
        fields = [
            'company', 'name', "subject", "issuer", "holder",
            'validity_start', 'validity_end', "file", "note",
            ]

        widgets = {
            'validity_start': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'validity_end': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'note': forms.Textarea(attrs={'rows': 8}),
        }


class NotificationSubscriptionForm(forms.Form):
    subscriptions = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            subscriptions = user.notifications.all()
            self.fields['subscriptions'].choices = [
                (sub.id, sub.notification.name) for sub in subscriptions
            ]
            self.fields['subscriptions'].initial = [
                sub.id for sub in subscriptions if sub.active
            ]


class NewsletterSubscriptionForm(forms.Form):
    subscriptions = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            subscriptions = user.newsletters.all()
            self.fields['subscriptions'].choices = [
                (sub.id, sub.newsletter.name) for sub in subscriptions
            ]
            self.fields['subscriptions'].initial = [
                sub.id for sub in subscriptions if sub.active
            ]



