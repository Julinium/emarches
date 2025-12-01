from django.db import models
from django.utils.translation import gettext_lazy as _

class ItemsPerPage(models.TextChoices):
    IPP_005 = '5',   "5"
    IPP_010 = '10',  "10"
    IPP_020 = '20',  "20"
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
    