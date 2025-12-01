from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from .models import Profile, Company, Favorite, Folder, NotificationSubscription, UserSetting
from .iceberg import get_ice_checkup

ALLOW_INVALID_ICE = True

class UserProfileForm(forms.ModelForm):
    # User model fields
    username = forms.CharField(max_length=150, required=True, label=_('Username'))
    first_name = forms.CharField(max_length=150, required=False, label=_('First Name'))
    last_name = forms.CharField(max_length=150, required=False, label=_('Last Name'))
    clear_image = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Profile
        fields = ['username', 'first_name', 'last_name', 'image', 'phone', 'whatsapp', 'about', 'clear_image']
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
            # user.username = self.cleaned_data['username']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()
            # Handle image clearing
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
            
            'tenders_ordering_field', 
            'tenders_items_per_page', 
            'tenders_full_bar_days', 
            'tenders_show_expired', 
            'tenders_show_cancelled',
            # 'preferred_language',

            'p_orders_ordering_field', 
            'p_orders_items_per_page', 
            'p_orders_full_bar_days', 
            'p_orders_show_expired', 
            ]
        # widgets = {
        #     'language': forms.Select(attrs={'class': 'form-control'}),  # Optional styling
        # }


class CompanyForm(forms.ModelForm):

    clear_image = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Company
        fields = [
            'name', 'forme', 'ice', 'tp', 'rc', 'cnss', 'address', 'city', 'zip_code',
            'state', 'country', 'date_est', 'phone', 'mobile', 'email', 'whatsapp', 'faximili',
            'website', 'activity', 'sector', 'note', 'image', 'clear_image']

        widgets = {
            'date_est': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'note': forms.Textarea(attrs={'rows': 8}),
        }
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
    
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
        
        # if len(ice) != 15: return False
        # p1, p2 = ice[0:12], ice[13:14]
        # try:
        #     n1, n2 = int(p1), int(p2)
        #     cs = 97 - ((n1 * 1000) % 97)
        #     return n2 == cs
        # except:
        #     return False


class NotificationSubscriptionForm(forms.Form):
    subscriptions = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Populate choices with all subscription IDs for the user
            subscriptions = user.notifications.all()
            self.fields['subscriptions'].choices = [
                (sub.id, sub.notification.name) for sub in subscriptions
            ]
            # Set initial values based on active subscriptions
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
            # Populate choices with all subscription IDs for the user
            subscriptions = user.newsletters.all()
            self.fields['subscriptions'].choices = [
                (sub.id, sub.newsletter.name) for sub in subscriptions
            ]
            # Set initial values based on active subscriptions
            self.fields['subscriptions'].initial = [
                sub.id for sub in subscriptions if sub.active
            ]


# class FavoriteForm(forms.ModelForm):
#     class Meta:
#         model = Favorite
#         fields = ('company', 'folders', 'comment')
#         widgets = {
#             'company': forms.CheckboxSelectMultiple,
#             'folders': forms.CheckboxSelectMultiple,
#             'comment': forms.Textarea(attrs={'rows': 3}),
#         }
#         # folders = forms.ModelMultipleChoiceField(
#         #     queryset=Folder.objects.filter(), 
#         #     required=False
#         #     )

#     def __init__(self, *args, user, tender, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.instance.user = user
#         self.instance.tender = tender

#         # Restrict choices to user-owned objects (adjust as needed)
#         self.fields['company'].queryset = Company.objects.filter(user=user)
#         self.fields['folders'].queryset = Folder.objects.filter(user=user)

