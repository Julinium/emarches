# import uuid
# from django.db import models
# from datetime import datetime, timedelta
# # from django.conf import settings
# from django.utils.translation import gettext_lazy as _

# from bidding.models import Team, Company


# class Feature(models.Model):
#     # A feature is a question that should be answered either with yes/no or a number. Not text
#     # Example: instaed of Support = Phone, use Support by phone = Yes
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     code = models.CharField(max_length=100, unique=True)
#     name = models.CharField(max_length=255)
#     category = models.CharField(max_length=32, null=True)
#     caption = models.CharField(max_length=512, null=True)
#     is_binary = models.BooleanField(default=True)
#     is_monthly = models.BooleanField(default=True)

#     is_active = models.BooleanField(default=True)

#     def __str__(self):
#         return self.name


# class Plan(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     code = models.CharField(max_length=100, unique=True)
#     name = models.CharField(max_length=255)
#     caption = models.CharField(max_length=512)
#     price_monthly = models.DecimalField(max_digits=5, decimal_places=0)
#     price_yearly = models.DecimalField(max_digits=5, decimal_places=0)
#     price_monthly_usd = models.DecimalField(max_digits=5, decimal_places=0)
#     price_yearly_usd = models.DecimalField(max_digits=5, decimal_places=0)
#     price_monthly_eur = models.DecimalField(max_digits=5, decimal_places=0)
#     price_yearly_eur = models.DecimalField(max_digits=5, decimal_places=0)
#     is_active = models.BooleanField(default=True)
#     features = models.ManyToManyField(Feature, through='PlanFeature')

#     def __str__(self):
#         return self.name


# class PlanFeature(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
#     feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
#     capability = models.IntegerField(default=0)

#     def __str__(self):
#         return f"{self.plan.code}-{self.feature.code}"


# class Order(models.Model):
#     STATUS_CHOICES = [
#         ("draft", _("Draft")),
#         ("pending", _("Pending Payment")),
#         ("confirmed", _("Confirmed")),
#         ("cancelled", _("Cancelled")),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     numero = models.CharField(max_length=64, verbose_name=_("Number")) #TODO: Set before saving new instances (@pre-save signal)
#     date_placed  = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Date"))
#     team = models.ForeignKey(Team, on_delete=models.PROTECT)
#     company = models.ForeignKey(Company, on_delete=models.PROTECT)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name=_("Status"))
#     total_amount_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Total amount, before teaxes"))
#     total_amount_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Total amount, after teaxes"))
#     total_taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Total taxes"))
#     # currency = models.CharField(max_length=10)
#     # ADDRESSES
#     delivery_address = models.TextField(null=True, verbose_name=_("Delivery address"))
#     billing_email = models.EmailField()

#     created  = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name="Date created")
#     updated  = models.DateTimeField(blank=True, null=True, verbose_name="Date updated")

#     def __str__(self):
#         return f"ORD#{self.numero}@{self.total_amount_ttc}"


# class OrderItem(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
#     item_reference = models.CharField(max_length=128, verbose_name=_("Reference"))
#     item_name = models.CharField(max_length=256, verbose_name=_("Item"))
#     item_details = models.CharField(max_length=512, verbose_name=_("Details"))
#     quantity = models.IntegerField(default=1, verbose_name=_("Quantity"))
#     units = models.CharField(default="U", null=True, verbose_name=_("Unit"))
#     unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Unit price"))
#     total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Line total"))
#     taxes_percent = models.DecimalField(max_digits=10, decimal_places=2, default=20, verbose_name=_("Taxes %"))
#     total_taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Taxes amount"))
#     unit_price_ttc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Unit price after taxes"))
#     total_price_ttc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Line total after taxes"))


# class Subscription(models.Model):
#     STATUS_CHOICES = [
#         ("trialing",    _("Trialing")),
#         ("active",      _("Active")),
#         ("suspended",   _("Suspended")),
#         ("cancelled",   _("Cancelled")),
#         ("paused",      _("Paused")),
#         ("expired",     _("Expired")),
#     ]

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     team = models.ForeignKey(Team, on_delete=models.PROTECT)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES)

#     start_date = models.DateTimeField()
#     ended_date = models.DateTimeField(null=True, blank=True)

#     trial_end = models.DateTimeField(null=True, blank=True)
#     cancel_at_period_end = models.BooleanField(default=False)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Contract {self.team.name}"


# class Cycle(models.Model):

#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT)
#     order = models.ForeignKey(Order, on_delete=models.PROTECT)
#     plan = models.ForeignKey(Plan, on_delete=models.PROTECT)

#     period_start = models.DateTimeField()
#     period_end = models.DateTimeField()
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.plan.code}:{self.period_start.date}-{self.period_end.date}{self.subscription.team.name}"

#     class Meta:
#         @property
#         def is_running(self, milmi=None):
#             if self.period_end is None: 
#                 return False
#             if milm is None:
#                 milmi = datetime.now()
#             if self.period_end < milmi:
#                 return False
#             if self.period_start is None:
#                 return False
#             if self.period_start > milmi:
#                 return False

#             return True
#         @property
#         def remaining_days(self, milmi=None):
#             if milm is None:
#                 milmi = datetime.now()
            
#             rd = self.period_end - milmi
#             return rd.days















# class SubscriptionCycle(models.Model):
#     STATUS_CHOICES = [
#         ("pending", "Pending"),
#         ("invoiced", "Invoiced"),
#         ("paid", "Paid"),
#         ("failed", "Failed"),
#     ]
#     subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
#     start_date = models.DateTimeField()
#     end_date = models.DateTimeField()
#     invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES)


# class SubscriptionChange(models.Model):
#     subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
#     old_plan = models.ForeignKey(Plan, null=True, on_delete=models.SET_NULL, related_name="+")
#     new_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="+")
#     proration_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
#     created_at = models.DateTimeField(auto_now_add=True)


# class Refund(models.Model):
#     payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     reason = models.CharField(max_length=255, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)



# class Invoice(models.Model):
#     STATUS_CHOICES = [
#         ("draft", "Draft"),
#         ("open", "Open"),
#         ("paid", "Paid"),
#         ("partially_paid", "Partially Paid"),
#         ("overdue", "Overdue"),
#         ("cancelled", "Cancelled"),
#         ("refunded", "Refunded"),
#     ]

#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.SET_NULL)

#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

#     total_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

#     currency = models.CharField(max_length=10)

#     issued_at = models.DateTimeField()
#     due_date = models.DateTimeField()

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Invoice #{self.id}"


# class Payment(models.Model):
#     METHOD_CHOICES = [
#         ("cash", _("Cash")),
#         ("bank", _("Bank Transfer")),
#         ("wire", _("Wire Transfer")),
#         ("check", _("Check")),
#     ]

#     STATUS_CHOICES = [
#         ("pending", _("Pending")),
#         ("confirmed", _("Confirmed")),
#         ("failed", _("Failed")),
#         ("cancelled", _("Cancelled")),
#     ]

#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

#     method = models.CharField(max_length=20, choices=METHOD_CHOICES)
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

#     amount = models.DecimalField(max_digits=10, decimal_places=2)
#     currency = models.CharField(max_length=10)

#     reference = models.CharField(max_length=255, blank=True)

#     paid_at = models.DateTimeField(null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Payment #{self.id}"


# class PaymentAllocation(models.Model):
#     payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
#     invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)

#     amount = models.DecimalField(max_digits=10, decimal_places=2)

#     class Meta:
#         unique_together = ("payment", "invoice")
