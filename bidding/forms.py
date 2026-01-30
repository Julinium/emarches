import os, re

from django import forms
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal

from django.contrib.auth.models import User
from base.models import Lot
from nas.models import Company
from bidding.models import Bid, Task, Contact
from bidding.widgets import FilenameOnlyClearableFileInput


CHECK_BIDDING_DEADLINE = True
CHECK_AMOUNT_MARGINS = True
MARGIN_PERCENT_OVER = 20
MARGIN_PERCENT_UNDER = 25


class LotChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return _("Lot") + " " + str(obj.number) + ' : ' + str(obj.estimate) + ' : ' + obj.title

class CompanyChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} ({obj.ice})"

class BidForm(forms.ModelForm):

    company = CompanyChoiceField(queryset=Lot.objects.none())

    class Meta:
        model = Bid
        fields = [
            'title',
            'company',
            'date_submitted',
            'bid_amount',
            'status',
            'bond_amount',
            'bond_status',
            'bond_due_date',
            'result',
            'file_bond',
            'file_submitted',
            'file_receipt',
            'details',
            ]

        widgets = {
            'date_submitted': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'bond_due_date' : forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'details'       : forms.Textarea(attrs={'rows': '3'}),
            "file_bond"     : FilenameOnlyClearableFileInput,
            "file_submitted": FilenameOnlyClearableFileInput,
            "file_receipt"  : FilenameOnlyClearableFileInput,
        }

    def __init__(self, *args, lot=None, user=None, usets=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator = user
        self.usets = usets
        self.lot = lot

        if user:
            fleet = user.teams.first().companies
            company_field = self.fields["company"]
            company_field.queryset = fleet
            if fleet.count() == 1:
                company_field.initial = fleet.first()
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
                lot = self.lot
                deadline = lot.tender.deadline
                published = lot.tender.published
                if deadline is not None:
                    if date_submitted is not None:
                        if date_submitted.date() > deadline.date():
                            raise forms.ValidationError(_("Allowed Submission date range:") + f" {published} - {deadline.date()}")
                if published is not None:
                    if date_submitted is not None:
                        if date_submitted.date() < published:
                            raise forms.ValidationError(_("Allowed Submission date range:") + f" {published} - {deadline.date()}")

        return date_submitted

    def clean_bid_amount(self):
        bid_amount = self.cleaned_data.get("bid_amount")
        us = self.usets
        if us:
            if us.bidding_check_amount != False:
                lot = self.lot
                estimate = lot.estimate

                if lot.category.label != "Travaux": margin_bottom = 20
                else: margin_bottom = MARGIN_PERCENT_UNDER

                if estimate is not None:
                    if bid_amount is not None:
                        limit_top = round(Decimal(1 + MARGIN_PERCENT_OVER / 100) * estimate, 2)
                        if bid_amount > limit_top:
                            raise forms.ValidationError(_("Submitted amount must fall under allowed top margin:") + f" E+{MARGIN_PERCENT_OVER}%: {limit_top}")
                        limit_bottom = round(Decimal(1 - margin_bottom / 100) * estimate, 2)
                        if bid_amount < limit_bottom :
                            raise forms.ValidationError(_("Submitted amount must fall over allowed bottom margin:") + f" E-{MARGIN_PERCENT_UNDER}%: {limit_bottom}")

        return bid_amount

    def clean_bond_amount(self):
        bond_amount = self.cleaned_data.get("bond_amount")
        us = self.usets
        if us:
            if us.bidding_check_amount != False:
                bond = self.lot.bond

                if bond is not None:
                    if bond_amount is not None:
                        if bond_amount != bond:
                            raise forms.ValidationError(_("Submitted bond amount is must be same as published bond"))

        return bond_amount

    def clean_file_bond(self):
        uploaded_file = self.cleaned_data['file_bond']
        if uploaded_file:
            original_name = uploaded_file.name

            name = os.path.basename(original_name)
            safe_name = re.sub(r'[^\w\-.]', '_', name)
            safe_name = safe_name.strip(".")
            safe_name = safe_name.replace("__", "_")
            # if len(safe_name) < 8:
            #     safe_name = f"eMarches.com-{safe_name}"

            if not safe_name:
                raise forms.ValidationError("Invalid file name.")
            if len(safe_name) > 64:
                raise forms.ValidationError("File name too long.")

            uploaded_file.name = safe_name

        return uploaded_file

    def clean_file_submitted(self):
        uploaded_file = self.cleaned_data['file_submitted']
        if uploaded_file:
            original_name = uploaded_file.name

            name = os.path.basename(original_name)
            safe_name = re.sub(r'[^\w\-.]', '_', name)
            safe_name = safe_name.strip(".")
            safe_name = safe_name.replace("__", "_")
            if len(safe_name) < 8:
                safe_name = f"eMarches.com-{safe_name}"
            
            if not safe_name:
                raise forms.ValidationError("Invalid file name.")
            if len(safe_name) > 64:
                raise forms.ValidationError("File name too long.")

            uploaded_file.name = safe_name

        return uploaded_file
    
    def clean_file_receipt(self):
        uploaded_file = self.cleaned_data['file_receipt']
        if uploaded_file:
            original_name = uploaded_file.name

            name = os.path.basename(original_name)
            safe_name = re.sub(r'[^\w\-.]', '_', name)
            safe_name = safe_name.strip(".")
            safe_name = safe_name.replace("__", "_")
            if len(safe_name) < 8:
                safe_name = f"eMarches.com-{safe_name}"
            
            if not safe_name:
                raise forms.ValidationError("Invalid file name.")
            if len(safe_name) > 64:
                raise forms.ValidationError("File name too long.")

            uploaded_file.name = safe_name

        return uploaded_file
    


class TaskForm(forms.ModelForm):

    class Meta:
        model = Task
        fields = [
            "title"     ,
            "date_due"  ,
            "emergency" ,
            "status"    ,
            "assignee"  ,
            "contact"   ,
            "details"   ,
        ]

        widgets = {
            'date_due': forms.DateInput(attrs={'type': 'date', 'class': 'date-input'}),
            'details'       : forms.Textarea(attrs={'rows': '3'}),
        }

    def __init__(self, *args, bid=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator = user
        self.bid = bid

        if user:
            colleagues = user.teams.first().members.all()
            assignee_field = self.fields["assignee"]
            assignee_field.queryset = colleagues
            if colleagues.count() == 1:
                assignee_field.initial = colleagues.first()

            contacts = Contact.objects.filter(creator__in=colleagues)
            contact_field = self.fields["contact"]
            contact_field.queryset = contacts
            if contacts.count() == 1:
                contact_field.initial = contacts.first()
        else:
            assignee_field.queryset = User.objects.none()
            contact_field.queryset = Contact.objects.none()

        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
            field.label_suffix = ""


