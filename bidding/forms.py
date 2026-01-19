from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal

from base.models import Lot
from nas.models import Company
from bidding.models import Bid
from bidding.widgets import FilenameOnlyClearableFileInput

# from base.context_processors import portal_context


CHECK_BIDDING_DEADLINE = True
CHECK_AMOUNT_MARGINS = True
MARGIN_PERCENT_OVER = 20
MARGIN_PERCENT_UNDER = 25



class LotChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return _("Lot ") + str(obj.number) + ' : ' + str(obj.estimate) + ' : ' + obj.title

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
            'amount_s',
            'bond_amount',
            'bond_status',
            'file_bond',
            'file_submitted',
            'file_receipt',
            'status',
            'amount_c',
            'result',
            'details',
            ]

        widgets = {
            'date_submitted': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'details'       : forms.Textarea(attrs={'rows': '3'}),
            "file_bond"     : FilenameOnlyClearableFileInput,
            "file_submitted": FilenameOnlyClearableFileInput,
            "file_receipt"  : FilenameOnlyClearableFileInput,
        }

    def __init__(self, *args, tender=None, user=None, usets=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator = user
        self.usets = usets

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
                # company_field.widget = forms.HiddenInput()
        else:
            company_field.queryset = Company.objects.none()

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.label_suffix = ""

    def clean_date_submitted(self):
        date_submitted = self.cleaned_data.get("date_submitted")
        us = self.usets
        if us:
            if us.bidding_check_deadline != False:
            # if CHECK_BIDDING_DEADLINE:
                lot = self.cleaned_data.get("lot")
                deadline = lot.tender.deadline
                if deadline is not None:
                    if date_submitted is not None:
                        if date_submitted.date() > deadline.date():
                            raise forms.ValidationError(_("Submission date must be earlier than Tender deadline:") + f" {deadline.date()}")
                published = lot.tender.published
                if published is not None:
                    if date_submitted is not None:
                        if date_submitted.date() < published:
                            raise forms.ValidationError(_("Submission date must be later than Tender published date:") + f" {published}")

        return date_submitted

    def clean_amount_s(self):
        amount_s = self.cleaned_data.get("amount_s")
        us = self.usets
        if us:
            if us.bidding_check_amount != False:
            # if CHECK_AMOUNT_MARGINS:
                lot = self.cleaned_data.get("lot")
                estimate = lot.estimate

                if lot.category.label != "Travaux": margin_bottom = 20
                else: margin_bottom = MARGIN_PERCENT_UNDER

                if estimate is not None:
                    if amount_s is not None:
                        limit_top = round(Decimal(1 + MARGIN_PERCENT_OVER / 100) * estimate, 2)
                        if amount_s > limit_top:
                            raise forms.ValidationError(_("Submitted amount must fall under allowed top margin:") + f" E+{MARGIN_PERCENT_OVER}%: {limit_top}")
                        limit_bottom = round(Decimal(1 - margin_bottom / 100) * estimate, 2)
                        if amount_s < limit_bottom :
                            raise forms.ValidationError(_("Submitted amount must fall over allowed bottom margin:") + f" E-{MARGIN_PERCENT_UNDER}%: {limit_bottom}")

        return amount_s


    
