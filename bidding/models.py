
import os, uuid
from decimal import Decimal
from django.db import models
from datetime import date, datetime, timezone

from django.contrib.auth.models import User
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

from django.core.validators import FileExtensionValidator

from base.models import Lot
# from base.context_processors import portal_context
from nas.models import Company
from nas.imaging import squarify_image

from nas.choices import (
    CivilityChoices, BidStatus, BondStatus, BidResults, ContractStatus, 
    TaskEmergency, TaskStatus, ExpenseStatus, ReceptionStatus, 
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
    members   = models.ManyToManyField(User, through='TeamMember')
    image     = models.ImageField(upload_to='bidding/teams/', null=True, blank=True, verbose_name=_('Avatar'))
    name      = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Name'))
    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False) 

    class Meta:
        db_table = 'bidding_team'

    def __str__(self):
        return self.name
    

    def add_member(self, user, patron=False):
        return TeamMember.objects.create(
            team=self,
            user=user,
            patron=patron,
        )

    @property
    def companies(self):
        return Company.objects.filter(user__in=self.members.all())
    
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


class TeamMember(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(User, on_delete=models.DO_NOTHING, editable=False)
    team      = models.ForeignKey(Team, on_delete=models.DO_NOTHING, editable=False)
    active    = models.BooleanField(null=True, default=True, editable=False)
    patron    = models.BooleanField(null=True, default=False, editable=False)
    joined    = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        db_table = 'bidding_team_member'
        
        constraints = [
            models.UniqueConstraint(
                fields=["team", "user"],
                name="unique_team_member"
            )
        ]


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
    lot             = models.ForeignKey(Lot, on_delete=models.DO_NOTHING, related_name='bids')
    company         = models.ForeignKey(Company, on_delete=models.DO_NOTHING, verbose_name=_('Company'), related_name='bids')

    title           = models.CharField(max_length=512, blank=True, null=True, verbose_name=_('Bid Title'))
    date_submitted  = models.DateTimeField(blank=True, null=True, verbose_name="Date Submitted")
    status          = models.CharField(max_length=16, choices=BidStatus.choices, default=BidStatus.BID_PREPARING, verbose_name=_('Bid Status'))
    details         = models.TextField(blank=True, null=True, verbose_name=_('Details'))

    bid_amount        = models.DecimalField(max_digits=16, decimal_places=2, verbose_name=_("Bid Amount"))

    bond_amount     = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, verbose_name=_("Bond Amount"))
    bond_status     = models.CharField(max_length=16, choices=BondStatus.choices, default=BondStatus.BOND_PREPARING, verbose_name=_('Bond Status'))
    bond_due_date   = models.DateTimeField(blank=True, null=True, verbose_name="Bond Due Date")
    file_bond       = models.FileField(upload_to='bidding/bonds/', validators=EXTENSIONS_VALIDATORS, blank=True, null=True, verbose_name=_("Bond file"))

    file_submitted  = models.FileField(upload_to='bidding/submitted/', validators=EXTENSIONS_VALIDATORS, blank=True, null=True, verbose_name=_("Submission file"))
    file_receipt    = models.FileField(upload_to='bidding/receipts/', validators=EXTENSIONS_VALIDATORS, blank=True, null=True, verbose_name=_("Receipt file"))

    result          = models.CharField(max_length=16, choices=BidResults.choices, default=BidResults.BID_UNKNOWN, verbose_name=_('Result'))

    created         = models.DateTimeField(auto_now_add=True, editable=False)
    updated         = models.DateTimeField(auto_now=True, editable=False)
    creator         = models.ForeignKey(User, on_delete=models.CASCADE, editable=False, related_name='bids')

    class Meta:
        db_table = 'bidding_bid'
        ordering = ['lot', 'date_submitted', 'company', 'bid_amount']

    def __str__(self):
        return self.lot.tender.title

    def caption(self):
        if self.title and self.title != "": return self.title
        return self.lot.title

    @property
    def archivable(self):
        if self.status == BidStatus.BID_FINISHED:
            if self.bond_status == BondStatus.BOND_RETURNED or self.bond_status == BondStatus.BOND_LOST:
                return True
        return False

    @property
    def ratio_str(self):
        if self.lot:
            estimate = self.lot.estimate
            if estimate != 0:
                ratio = round(Decimal("100") * (self.bid_amount - estimate) / estimate, 2)
                if ratio >= 0 : return f"+{ratio}%"
                return f"{ratio}%"
        return None

    @property
    def duplicated(self):
        clowns = Bid.objects.filter(
                lot=self.lot,
                company=self.company,
            )
        return clowns.count() > 1

    @property
    def deletable(self):
        if self.status != BidStatus.BID_CANCELLED: return False
        if self.bond_amount != 0 and self.bond_status == BondStatus.BOND_FILED: return False
        return True

    @property
    def file_bond_name(self):
        if self.file_bond: return os.path.basename(self.file_bond.name)
        return None

    @property
    def file_submitted_name(self):
        if self.file_submitted: return os.path.basename(self.file_submitted.name)
        return None

    @property
    def file_receipt_name(self):
        if self.file_receipt: return os.path.basename(self.file_receipt.name)
        return None

    @property
    def status_tint(self):
        if self.status == BidStatus.BID_PREPARING : return 'warning'
        if self.status == BidStatus.BID_READY     : return 'warning'
        if self.status == BidStatus.BID_SUBMITTED : return 'primary'
        if self.status == BidStatus.BID_FINISHED  : return 'success'
        if self.status == BidStatus.BID_CANCELLED : return 'danger'
        return 'secondary'

    @property
    def result_tint(self):
        if self.result == BidResults.BID_UNKNOWN  : return 'warning'
        if self.result == BidResults.BID_AWARDED  : return 'success'
        if self.result == BidResults.BID_REJECT_A : return 'danger'
        if self.result == BidResults.BID_REJECT_T : return 'danger'
        if self.result == BidResults.BID_LOST     : return 'secondary'
        return 'secondary'

    @property
    def tag(self):
        if self.status == BidStatus.BID_CANCELLED:  return BidStatus.BID_CANCELLED
        if self.status == BidStatus.BID_SUBMITTED or self.status == BidStatus.BID_FINISHED:
            if self.result == BidResults.BID_UNKNOWN: return self.status
            return self.result
        return self.status

    @property
    def tag_display(self):
        if self.tag == self.result:
            return dict(self._meta.get_field("result").flatchoices).get(self.tag)
        return dict(self._meta.get_field("status").flatchoices).get(self.tag)

    @property
    def tag_tint(self):
        if self.tag == BidStatus.BID_READY     : return 'warning'
        if self.tag == BidResults.BID_AWARDED  : return 'success'
        if self.tag == BidResults.BID_REJECT_A : return 'danger'
        if self.tag == BidResults.BID_REJECT_T : return 'danger'
        if self.tag == BidResults.BID_LOST     : return 'secondary'
        return self.status_tint

    @property
    def bond_tint(self):
        if self.bond_status == BondStatus.BOND_PREPARING :   return 'secondary'
        if self.bond_status == BondStatus.BOND_FILED     :   return 'warning'
        if self.bond_status == BondStatus.BOND_RETURNED  :   return 'success'
        if self.bond_status == BondStatus.BOND_LOST      :   return 'danger'
        return 'secondary'

    @property
    def milestones(self):
        milestones = []
        if self.lot.tender.published:
            milestones.append({
                "date": self.lot.tender.published,          
                "past": is_past(self.lot.tender.published), 
                "event": _("Tender published")
                })
        if self.lot.tender.deadline:
            milestones.append({
                "date": self.lot.tender.deadline.date(),    
                "past": is_past(self.lot.tender.deadline), 
                "event": _("Bidding deadline")
                })
        if self.date_submitted:
            milestones.append({
                "date": self.date_submitted.date(), 
                "past": is_past(self.date_submitted), 
                "event": _("Bid Submitted")
                })
        if self.updated:
            milestones.append({
                "date": self.updated.date(),        
                "past": is_past(self.updated), 
                "event": _("Latest Bid update")
                })
        if self.bond_due_date:
            milestones.append({
                "date": self.bond_due_date.date(),
                "past": is_past(self.bond_due_date), 
                "event": _("Bond return date")
                })

        openings = self.lot.tender.openings.all()
        for opening in openings:
            milestones.append({
                "date": opening.date,    
                "past": is_past(opening.date), 
                "event": _("Tender results published")
                })

        change = self.lot.tender.changes.last()
        if change:
            milestones.append({
                "date": change.reported.date(),    
                "past": is_past(change.reported), 
                "event": _("Latest Tender change")
                })

        samples = self.lot.samples
        for sample in samples.all():
            milestones.append({
                "date": sample.when.date(),    
                "past": is_past(sample.when), 
                "event": _("Samples deadline")
                })

        meetings = self.lot.meetings
        for meeting in meetings.all():
            milestones.append({
                "date": meeting.when.date(),    
                "past": is_past(meeting.when), 
                "event": _("Meeting deadline")
                })

        visits = self.lot.visits
        for visit in visits.all():
            milestones.append({
                "date": visit.when.date(),    
                "past": is_past(visit.when), 
                "event": _("Site visit deadline")
                })
        
        for task in self.tasks.all():
            if task.date_due:
                milestones.append({
                    "date": task.date_due.date(),    
                    "past": is_past(task.date_due), 
                    "event": _("Task due") + ": " + task.title
                })
        
        for contract in self.contracts.all():
            if contract.date_signed:
                milestones.append({
                    "date": contract.date_signed.date(),    
                    "past": is_past(contract.date_signed), 
                    "event": _("Contract signed") + ": " + contract.title
                })
        
        for contract in self.contracts.all():
            if contract.date_finish:
                milestones.append({
                    "date": contract.date_finish.date(),    
                    "past": is_past(contract.date_finish), 
                    "event": _("Contract finished") + ": " + contract.title
                })
        
        for expense in self.expenses.all():
            if expense.date_paid:
                milestones.append({
                    "date": expense.date_paid.date(),    
                    "past": is_past(expense.date_paid), 
                    "event": f"{expense.amount_paid} : " + _("Expense paid") + ": " + expense.title
                })
        

        milestones.sort(key=lambda e: e["date"])

        return milestones


class Contract(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference      = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Reference'))
    bid            = models.ForeignKey(Bid, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Bid'), related_name='contracts')
    client         = models.CharField(max_length=255, blank=True, default='?', verbose_name=_('Client'))
    title          = models.CharField(max_length=255, blank=True, default='?', verbose_name=_('Title'))
    details        = models.TextField(blank=True, null=True, verbose_name=_('Details'))
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
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bid       = models.ForeignKey(Bid, on_delete=models.CASCADE, null=True, verbose_name=_('Bid'), related_name='tasks')
    title     = models.CharField(max_length=255, default=_('New Task'), verbose_name=_('Title'))
    date_due  = models.DateTimeField(blank=True, null=True, verbose_name="Due Date")
    reminder  = models.SmallIntegerField(blank=True, null=True, verbose_name="Reminder days")
    contact   = models.ForeignKey(Contact, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contact'), related_name='tasks')
    details   = models.TextField(blank=True, null=True, verbose_name=_('Details'))
    assignee  = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Assigned to'), related_name='assigned_tasks')
    emergency = models.CharField(max_length=16, choices=TaskEmergency.choices, default=TaskEmergency.TASK_NORMAL, verbose_name=_('Emergency'))
    milestone = models.BooleanField(null=True, default=True)
    status    = models.CharField(max_length=16, choices=TaskStatus.choices, default=TaskStatus.TASK_PENDING, verbose_name=_('Status'))

    creator   = models.ForeignKey(User, on_delete=models.CASCADE, editable=False, related_name='tasks')
    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_task'

    def __str__(self):
        return self.title


class Expense(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bid          = models.ForeignKey(Bid, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Bid'), related_name='expenses')
    contract     = models.ForeignKey(Contract, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contract'), related_name='expenses')
    # company      = models.ForeignKey(Company, on_delete=models.DO_NOTHING, verbose_name=_('Company'), related_name='expenses')
    title        = models.CharField(max_length=255, blank=True, default=_('Expense'), verbose_name=_('Object'))
    reference    = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Reference'))
    bill_ref     = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Bill Number'))
    bill_date    = models.DateTimeField(blank=True, null=True, verbose_name="Bill Date")
    date_paid    = models.DateTimeField(blank=True, null=True, verbose_name="Paid Date")
    channel      = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Payment Mean'))
    mean_ref     = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Mean Reference'))

    amount_paid  = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Paid Amount, incl. Taxes"))
    amount_vat   = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Taxes Amount"))
    
    payee        = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Payee'))
    payee_ice    = models.CharField(max_length=15, blank=True, default='', verbose_name=_('Payee ICE'))
    contact      = models.ForeignKey(Contact, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contact'), related_name='expenses')


    details      = models.TextField(blank=True, null=True, verbose_name=_('Details'))
    status       = models.CharField(max_length=16, choices=ExpenseStatus.choices, default=ExpenseStatus.XPS_PENDING, verbose_name=_('Status'))

    file         = models.FileField(upload_to='bidding/expenses/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("File"))

    creator      = models.ForeignKey(User, on_delete=models.DO_NOTHING, editable=False, related_name='expenses')
    created      = models.DateTimeField(auto_now_add=True, editable=False)
    updated      = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_expense'

    def __str__(self):
        return self.title


class Reception(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract     = models.ForeignKey(Contract, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contract'), related_name='receptions')
    title        = models.CharField(max_length=255, blank=True, default=_('Reception'), verbose_name=_('Object'))
    reference    = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Reference'))
    date_sched   = models.DateTimeField(blank=True, null=True, verbose_name="Scheduled Date")
    date_subm    = models.DateTimeField(blank=True, null=True, verbose_name="Submitted Date")

    client       = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Client'))
    client_ice   = models.CharField(max_length=15, blank=True, default='', verbose_name=_('Client ICE'))
    contact      = models.ForeignKey(Contact, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contact'), related_name='receptions')
    location     = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Location'))

    details      = models.TextField(blank=True, null=True, verbose_name=_('Details'))
    status       = models.CharField(max_length=16, choices=ReceptionStatus.choices, default=ReceptionStatus.RCP_PENDING, verbose_name=_('Status'))

    file         = models.FileField(upload_to='bidding/receptions/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("File"))

    creator      = models.ForeignKey(User, on_delete=models.DO_NOTHING, editable=False, related_name='receptions')
    created      = models.DateTimeField(auto_now_add=True, editable=False)
    updated      = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_reception'

    def __str__(self):
        return self.title


class Income(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # bid          = models.ForeignKey(Bid,       on_delete=models.DO_NOTHING, null=True, verbose_name=_('Bid'),       related_name='incomes')
    contract     = models.ForeignKey(Contract,  on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contract'),  related_name='incomes')
    # company      = models.ForeignKey(Company,   on_delete=models.DO_NOTHING,            verbose_name=_('Company'),   related_name='incomes')
    # reception    = models.ForeignKey(Reception, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Reception'), related_name='incomes')

    title        = models.CharField(max_length=255, blank=True, default=_('Expense'), verbose_name=_('Object'))
    reference    = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Reference'))
    bill_ref     = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Bill Number'))
    bill_date    = models.DateTimeField(blank=True, null=True, verbose_name="Bill Date")
    date_paid    = models.DateTimeField(blank=True, null=True, verbose_name="Paid Date")
    channel      = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Payment Mean'))
    channel_ref  = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Mean Reference'))

    amount_paid  = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Paid Amount, incl. Taxes"))
    amount_vat   = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Taxes Amount"))

    client       = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Client'))
    client_ice   = models.CharField(max_length=15, blank=True, default='', verbose_name=_('Client ICE'))
    contact      = models.ForeignKey(Contact, on_delete=models.DO_NOTHING, null=True, verbose_name=_('Contact'), related_name='incomes')

    details      = models.TextField(blank=True, null=True, verbose_name=_('Details'))
    status       = models.CharField(max_length=16, choices=ExpenseStatus.choices, default=ExpenseStatus.XPS_PENDING, verbose_name=_('Status'))

    file         = models.FileField(upload_to='bidding/incomes/', validators=EXTENSIONS_VALIDATORS, null=True, verbose_name=_("File"))

    creator      = models.ForeignKey(User, on_delete=models.DO_NOTHING, editable=False, related_name='incomes')
    created      = models.DateTimeField(auto_now_add=True, editable=False)
    updated      = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'bidding_income'

    def __str__(self):
        return self.title



def is_past(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            now = datetime.now()
        else:
            now = datetime.now(timezone.utc).astimezone(value.tzinfo)
        return value < now

    if isinstance(value, date):
        return value < date.today()
    
    return False
