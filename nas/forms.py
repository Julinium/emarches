from django import forms
from django.contrib.auth.models import User
from .models import Profile
from django.utils.translation import gettext_lazy as _

class UserProfileForm(forms.ModelForm):
    # User model fields
    username = forms.CharField(max_length=150, required=True, label=_('Username'))
    email = forms.EmailField(required=True, label=_('Email'))
    first_name = forms.CharField(max_length=150, required=False, label=_('First Name'))
    last_name = forms.CharField(max_length=150, required=False, label=_('Last Name'))

    class Meta:
        model = Profile
        fields = ['username', 'email', 'first_name', 'last_name', 'image', 'phone', 'whatsapp', 'about']
        labels = {
            'image': _('Avatar'),
            'phone': _('Telephone'),
            'whatsapp': _('Whatsapp'),
            'about': _('A Propos'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate User fields if instance exists
        if self.instance and self.instance.pk and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def save(self, commit=True):
        # Save Profile instance
        profile = super().save(commit=False)
        if commit:
            # Update or create associated User instance
            user = profile.user
            user.username = self.cleaned_data['username']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()
            profile.save()
        return profile