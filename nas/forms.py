from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from .models import Profile, Company

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
        # request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        # self.request = request
        # Populate User fields if instance exists
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
        # if image:
        #     if not image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        #         pass
        #         # TODO: Log
        #     if image.size > 5 * 1024 * 1024:
        #         pass
        #         # TODO: Log
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


class CompanyForm(forms.ModelForm):
    clear_image = forms.BooleanField(required=False, widget=forms.HiddenInput)
    class Meta:
        model = Company
        # exclude = ('id', 'user', 'active', 'created', 'updated',)
        fields = [
            'name', 'forme', 'ice', 'tp', 'rc', 'cnss', 'address', 'city', 'zip_code',
            'state', 'country', 'date_est', 'phone', 'mobile', 'email', 'whatsapp', 'faximili',
            'website', 'activity', 'sector', 'note', 'image', 'clear_image']

        widgets = {
            'date_est': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'note': forms.Textarea(attrs={'rows': 5}),
        }

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        clear_image = cleaned_data.get('clear_image')

        if clear_image:
            cleaned_data['image'] = None
        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image')
        # if image:
        #     if not image.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif')):
        #         pass
        #         # TODO: Log
        #     if image.size > 5 * 1024 * 1024:
        #         pass
        #         # TODO: Log
        return image

    def save(self, commit=True):
        # if self.is_valid():
        #     print("VVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV")
        # else:
        #     print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        company = super().save(commit=False)
        if commit:
            if self.cleaned_data.get('clear_image'):
                company.image = None
            company.save()
        return company
