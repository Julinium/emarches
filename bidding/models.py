
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

from django.core.validators import FileExtensionValidator

# from django.conf import settings

from base.models import Lot, Tender
from nas.models import Company
from nas.imaging import squarify_image
# from .iceberg import get_ice_checkup
from nas.choices import (
    CivilityChoices, BidStatus, BidResults, ContractStatus
    )

EXTENSIONS_VALIDATORS = [
    FileExtensionValidator(
        allowed_extensions=[
            'zip', 'rar', 'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'xls', 'xlsx', 'odt', 'odp', 'odx', 'txt'
            ]
        )
    ]

class Team(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    creator   = models.ForeignKey(User, on_delete=models.DO_NOTHING, editable=False, related_name='teams')
    active    = models.BooleanField(null=True, default=True)
    image     = models.ImageField(upload_to='bidding/teams/', null=True, blank=True, verbose_name=_('Avatar'))
    name      = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Name'))
    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_team'

    def __str__(self):
        return self.name
    
    @property
    def avatar(self):
        try:
            avatar = self.image.url
        except:
            avatar = static('bidding/teams/default.png')
        return avatar
    
    def save(self, *args, **kwargs):
        if self.image:
            self.image = squarify_image(self.image, str(self.id).split('-')[0])
        super().save(*args, **kwargs)


class Contact(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    civility  = models.CharField(max_length=16, choices=CivilityChoices.choices, default=CivilityChoices.CIV_MR, verbose_name=_('Civility'))
    active    = models.BooleanField(null=True, default=True)
    name      = models.CharField(max_length=255, verbose_name=_('Name'))
    phone     = models.CharField(max_length=255, blank=True, verbose_name=_('Phone'))
    mobile    = models.CharField(max_length=255, blank=True, verbose_name=_('Mobile'))
    email     = models.EmailField(blank=True, verbose_name=_('Email'))
    whatsapp  = models.CharField(max_length=255, blank=True, verbose_name=_('Whatsapp'))
    faximili  = models.CharField(max_length=255, blank=True, verbose_name=_('Fax'))
    website   = models.CharField(max_length=128, blank=True, verbose_name=_('Website'))
    address   = models.CharField(max_length=512, blank=True, verbose_name=_('Street Address'))
    city      = models.CharField(max_length=64, blank=True, verbose_name=_('City'))
    country   = models.CharField(max_length=64, blank=True, default=_('Morocco'), verbose_name=_('Country'))
    company   = models.CharField(max_length=128, blank=True, verbose_name=_('Company'))
    position  = models.CharField(max_length=128, blank=True, verbose_name=_('Position'))
    notes     = models.CharField(max_length=1024, blank=True, verbose_name=_('Notes'))

    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_contact'
        ordering = ['name']

    def __str__(self):
        return f'{self.civility} {self.name}'


class Bid(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lot             = models.ForeignKey(Lot, on_delete=models.DO_NOTHING, editable=False, related_name='bids')
    team            = models.ForeignKey(Team, on_delete=models.CASCADE, editable=False, related_name='bids')
    company         = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name=_('Company'), related_name='bids')

    date_submitted  = models.DateTimeField(blank=True, null=True, verbose_name="Date Submitted")
    status          = models.CharField(max_length=16, choices=BidStatus.choices, default=BidStatus.BID_PREPARING, verbose_name=_('Status'))

    amount_s        = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Amount Submitted"))
    amount_c        = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Amount Corrected"))
    bond            = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Bond"))
    file_bond       = models.FileField(upload_to='bidding/bonds/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("Bond file"))
    file_submitted  = models.FileField(upload_to='bidding/submitted/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("Submission file"))
    file_receipt    = models.FileField(upload_to='bidding/receipts/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("Receipt file"))
    file_other      = models.FileField(upload_to='bidding/others/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("Other file"))

    result          = models.CharField(max_length=16, choices=BidResults.choices, default=BidResults.BID_UNKNOWN, verbose_name=_('Result'))

    created         = models.DateTimeField(auto_now_add=True, editable=False)
    updated         = models.DateTimeField(auto_now=True, editable=False)
    creator         = models.ForeignKey(User, on_delete=models.CASCADE, editable=False, related_name='bids')
    

    class Meta:
        db_table = 'bidding_bid'

    def __str__(self):
        return self.lot.tender.title

    def save(self, *args, **kwargs):
        if self.id:
            self.image = squarify_image(self.image, str(self.id).split('-')[0])
        super().save(*args, **kwargs)


class Contract(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference      = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Reference'))
    bid            = models.ForeignKey(Bid, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Bid'), related_name='contracts')
    client         = models.CharField(max_length=255, blank=True, default='?', verbose_name=_('Client'))
    title          = models.CharField(max_length=255, blank=True, default='?', verbose_name=_('Title'))
    date_signed    = models.DateTimeField(blank=True, null=True, verbose_name="Date Signed")
    date_finish    = models.DateTimeField(blank=True, null=True, verbose_name="Finish Date")
    amount         = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Amount"))
    guarantee      = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Guarantee"))
    guarantee_date = models.DateTimeField(blank=True, null=True, verbose_name="Guarantee release date")
    file_guarantee = models.FileField(upload_to='bidding/guaranties/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("Guarantee file"))
    file_terms     = models.FileField(upload_to='bidding/contracts/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("Terms file"))
    status         = models.CharField(max_length=16, choices=ContractStatus.choices, default=ContractStatus.CONTRACT_PREPARING, verbose_name=_('Status'))

    creator   = models.ForeignKey(User, on_delete=models.DO_NOTHING, editable=False, related_name='contracts')
    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_contract'

    def __str__(self):
        return self.reference


class Task(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bid            = models.ForeignKey(Bid, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Bid'), related_name='tasks')
    contract       = models.ForeignKey(Contract, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contract'), related_name='tasks')
    title          = models.CharField(max_length=255, blank=True, default=_('Task'), verbose_name=_('Title'))
    date_due       = models.DateTimeField(blank=True, null=True, verbose_name="Due Date")
    contact        = models.ForeignKey(Contact, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contact'), related_name='tasks')
    deatils        = models.TextField(blank=True, null=True, verbose_name=_('Details'))
    assignee       = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name=_('Assigned to'), related_name='tasks')
    emergency      = models.CharField(max_length=16, choices=TaskEmergency.choices, default=TaskEmergency.TASK_NORMAL, verbose_name=_('Emergency'))
    milestone      = models.BooleanField(null=True, default=True)
    status         = models.CharField(max_length=16, choices=ContractStatus.choices, default=ContractStatus.TASK_PENDING, verbose_name=_('Status'))

    creator   = models.ForeignKey(User, on_delete=models.DO_NOTHING, editable=False, related_name='tasks')
    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_task'

    def __str__(self):
        return self.title


EXPENSE
    • Date
    • Object
    • Amount
    • Payee
    • Source/Mean
    • Reference
    • File
    • → Company ?
    • → Contact ?
    • → Contract ?
    • → Bid ?

RECEPTION
    • → Contract
    • Date Scheduled
    • Date ended
    • Progress (%)
    • Manager
    • → Contact
    • Location
    • Result (Success, Fail, Retake, …)
    • Files

PAYMENT
    • Date
    • Object
    • Amount
    • Payee
    • Source/Mean
    • Reference
    • File
    • → Contract ?
    • → Bid ?


ACCOUNT ?

