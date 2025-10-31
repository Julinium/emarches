from django.db import models
from django.utils.translation import gettext_lazy as _

class ItemsPerPage(models.IntegerChoices):
    IPP_005 = 5,   "5"
    IPP_010 = 10,  "10"
    IPP_020 = 20,  "20"
    IPP_025 = 25,  "25"
    IPP_050 = 50,  "50"
    IPP_100 = 100, "100"
    # IPP_250 = 250, "250"
    # IPP_500 = 500, "500"

class OrderingField(models.TextChoices):
        DEADLINE_ASC  = 'deadline',   _('Deadline: Nearest first')
        DEADLINE_DES  = '-deadline',  _('Deadline: Farthest first')
        ESTIMATE_ASC  = 'estimate',   _('Estimate: Smallest first')
        ESTIMATE_DES  = '-estimate',  _('Estimate: Largest first')
        BOND_ASC      = 'bond',       _('Guarantee: Smallest first')
        BOND_DES      = '-bond',      _('Guarantee: Largest first')
        PUBLISHED_ASC = 'published',  _('Published: Oldest first')
        PUBLISHED_DES = '-published', _('Published: Newest first')

class FullBarDays(models.IntegerChoices):
    # 30 / 7, 10, 15, 20, 45, 60, 90, 180, 360
    FBD_007 = 7,   "7"
    FBD_010 = 10,  "10"
    FBD_015 = 15,  "15"
    FBD_020 = 20,  "20"
    FBD_030 = 30,  "30"
    FBD_045 = 45,  "45"
    FBD_060 = 60,  "60"
    FBD_090 = 90,  "90"
    FBD_180 = 180, "180"
    FBD_365 = 365, "365"
    