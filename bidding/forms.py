from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
# from django.contrib.auth.models import User

from .models import Bid
from base.models import Lot

class BidForm(forms.ModelForm):

    # clear_image = forms.BooleanField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Bid
        fields = [
            'lot',
            'company',
            'date_submitted',
            'status',
            'deatils',
            'amount_s',
            'amount_c',
            'bond',
            'file_bond',
            'bond_returned',
            'file_submitted',
            'file_receipt',
            'file_other',
            'result',
            # 'created',
            # 'updated',
            # 'creator',
            ]

        widgets = {
            'date_submitted': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'deatils': forms.Textarea(attrs={'rows': 8}),
        }
    
    # def __init__(self, *args, user=None, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.user = user

    def __init__(self, *args, tender=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator = user

        if tender:
            self.fields["lot"].queryset = Lot.objects.filter(
                tender=tender
            )
        else:
            self.fields["lot"].queryset = Lot.objects.none()
    
    # def clean(self):
    #     cleaned_data = super().clean()
    #     name = cleaned_data.get('name')
    #     ice = cleaned_data.get('ice')
    #     image = cleaned_data.get('image')
    #     clear_image = cleaned_data.get('clear_image')

    #     if clear_image:
    #         cleaned_data['image'] = None

    #     if name and self.user:
    #         existing_company = Company.objects.filter(user=self.user, name=name).exclude(
    #             pk=self.instance.pk if self.instance else None).exists()
    #         if existing_company:
    #             raise ValidationError({
    #                 'name': _('The name is already taken.')
    #             })
                
    #     if not ALLOW_INVALID_ICE:
    #         if not self.ice_checkup_valid():
    #             raise ValidationError({
    #                 'ice': _('The ICE is not valid.')
    #             })

    #     return cleaned_data

    # def save(self, commit=True):
    #     company = super().save(commit=False)
    #     if commit:
    #         if self.cleaned_data.get('clear_image'):
    #             company.image = None
    #         company.save()
    #     return company

    # def clean_image(self):
    #     image = self.cleaned_data.get('image')
    #     return image
    
    # def ice_checkup_valid(self):
    #     ice = self.cleaned_data.get('ice')
    #     if not ice: return False
    #     cj = get_ice_checkup(ice)
    #     if not cj: return False
    #     return cj.get('n2') == cj.get('cs')
        

