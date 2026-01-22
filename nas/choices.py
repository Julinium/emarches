from django.db import models
from django.utils.translation import gettext_lazy as _

class CivilityChoices(models.TextChoices):
    CIV_MR  = '10R',   _("Mr.")
    CIV_MLE = '20L',   _("Mle")
    CIV_MME = '30M',   _("Mme")
    CIV_DR  = '40D',   _("Dr.")
    CIV_PR  = '50P',   _("Pr.")

class BidStatus(models.TextChoices):
    BID_PREPARING = '10U',   _("Draft")
    BID_READY     = '20R',   _("Ready")
    BID_SUBMITTED = '30S',   _("Submitted")
    BID_FINISHED  = '40F',   _("Finished")
    BID_CANCELLED = '50X',   _("Cancelled")

class BondStatus(models.TextChoices):
    BOND_PREPARING = '10U',   _("Draft")
    BOND_FILED     = '20F',   _("Filed")
    BOND_CLAIMED   = '25C',   _("Claimed")
    BOND_RETURNED  = '30R',   _("Returned")
    BOND_LOST      = '40L',   _("Lost")

class BidResults(models.TextChoices):
    BID_UNKNOWN   = '10X',   _("Unknown")
    BID_AWARDED   = '20A',   _("Awarded")
    BID_REJECT_A  = '30D',   _("Admin Reject")
    BID_REJECT_T  = '40T',   _("Tech Reject")
    BID_LOST      = '50U',   _("Unselected")

class ContractStatus(models.TextChoices):
    CONTRACT_PREPARING  = '10P',   _("Draft")
    CONTRACT_SIGNED     = '20S',   _("Signed")
    CONTRACT_EXECUTION  = '30E',   _("Executing")
    CONTRACT_FINISHED   = '40U',   _("Finished")
    CONTRACT_CLOSED     = '50C',   _("Closed")
    CONTRACT_CANCELLED  = '60X',   _("Cancelled")

class TaskEmergency(models.TextChoices):
    TASK_TERTIARY  = '10T',   _("Tertiary")
    TASK_SECONDARY = '20S',   _("Secondary")
    TASK_NORMAL    = '30N',   _("Normal")
    TASK_URGENT    = '40U',   _("Urgent")
    TASK_CRITICAL  = '50C',   _("Critical")

class TaskStatus(models.TextChoices):
    TASK_PENDING   = '10P',   _("Pending")
    TASK_STARTED   = '20S',   _("Started")
    TASK_STALLED   = '30S',   _("Stalled")
    TASK_FINISHED  = '40E',   _("Finished")
    TASK_CANCELLED = '50X',   _("Cancelled")

class ExpenseStatus(models.TextChoices):
    XPS_PENDING   = '10P',   _("Pending")
    XPS_PAID      = '20D',   _("Paid")
    XPS_CONFIRMED = '30C',   _("Confirmed")
    XPS_CANCELLED = '40X',   _("Cancelled")

class ReceptionStatus(models.TextChoices):
    RCP_PENDING   = '10P',   _("Pending")
    RCP_SUBMITTED = '20S',   _("Submitted")
    RCP_ACCEPTED  = '30A',   _("Accepted")
    RCP_CANCELLED = '40X',   _("Cancelled")


class ItemsPerPage(models.TextChoices):
    IPP_005 = '5',   "5"
    IPP_010 = '10',  "10"
    IPP_020 = '20',  "20"
    IPP_025 = '25',  "25"
    IPP_030 = '30',  "30"
    IPP_050 = '50',  "50"
    IPP_100 = '100', "100"

class OrderingField(models.TextChoices):
    DEADLINE_ASC  = 'deadline',   _('Deadline') + ' ↗'
    DEADLINE_DES  = '-deadline',  _('Deadline') + ' ↘'
    ESTIMATE_ASC  = 'estimate',   _('Estimate') + ' ↗'
    ESTIMATE_DES  = '-estimate',  _('Estimate') + ' ↘'
    BOND_ASC      = 'bond',       _('Guarantee') + ' ↗'
    BOND_DES      = '-bond',      _('Guarantee') + ' ↘'
    PUBLISHED_ASC = 'published',  _('Published') + ' ↗'
    PUBLISHED_DES = '-published', _('Published') + ' ↘'

class PurchaseOrderOrderingField(models.TextChoices):
    DEADLINE_ASC    = 'deadline',     _('Deadline') + ' ↗'
    DEADLINE_DES    = '-deadline',    _('Deadline') + ' ↘'
    PUBLISHED_ASC   = 'published',    _('Published') + ' ↗'
    PUBLISHED_DES   = '-published',   _('Published') + ' ↘'
    DELIBERATED_ASC = 'deliberated',  _('Deliberated') + ' ↗'
    DELIBERATED_DES = '-deliberated', _('Deliberated') + ' ↘'
    WIN_AMOUNT_ASC  = 'winner_amount', _('Winner amount') + ' ↗'
    WIN_AMOUNT_DES  = '-winner_amount',_('Winner amount') + ' ↘'

class PurchaseOrderFullBarDays(models.TextChoices):
    FBD_005 = '5',   "5"
    FBD_007 = '7',   "7"
    FBD_015 = '15',  "15"
    FBD_020 = '20',  "20"
    FBD_030 = '30',  "30"
    FBD_060 = '60',  "60"
    FBD_090 = '90',  "90"

class FullBarDays(models.TextChoices):
    FBD_007 = '7',   "7"
    FBD_010 = '10',  "10"
    FBD_015 = '15',  "15"
    FBD_020 = '20',  "20"
    FBD_030 = '30',  "30"
    FBD_045 = '45',  "45"
    FBD_060 = '60',  "60"
    FBD_090 = '90',  "90"
    FBD_180 = '180', "180"
    FBD_365 = '365', "365"

class FirstArticles(models.TextChoices):
    ATS_002 = '2',   "2"
    ATS_005 = '5',   "5"
    ATS_010 = '10',  "10"
    ATS_015 = '15',  "15"
    ATS_025 = '25',  "25"
    ATS_050 = '50',  "50"
    ATS_100 = '100', "100"


