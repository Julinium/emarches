from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
# from django.contrib.auth.models import User

from bidding.models import Bid
from base.models import Lot
from nas.models import Company


class LotChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.number}: {obj.estimate} ({obj.bond})"

class CompanyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.ice})"

class BidForm(forms.ModelForm):

    lot = LotChoiceField(queryset=Lot.objects.none())
    company = CompanyChoiceField(queryset=Lot.objects.none())

    class Meta:
        model = Bid
        fields = [
            'lot',
            'company',
            'date_submitted',
            'status',
            'details',
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
            lots = Lot.objects.filter(tender=tender)
            lot_field = self.fields["lot"]
            lot_field.queryset = lots
            
            if lots.count() == 1:
                lot_field.initial = lots.first()
                lot_field.widget = forms.HiddenInput()
        else:
            self.fields["lot"].queryset = Lot.objects.none()

        if user:
            comps = user.companies
            company_field = self.fields["company"]
            company_field.queryset = comps
            if comps.count() == 1:
                company_field.initial = comps.first()
                company_field.widget = forms.HiddenInput()
        else:
            company_field.queryset = Company.objects.none()

            
    
