import uuid
from django.db import models
# from datetime import datetime, timedelta
# # from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields

from bidding.models import Team, Company


class Category(TranslatableModel):
    id     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    code   = models.CharField(max_length=100, unique=True)
    rank   = models.IntegerField(default=0)

    translations = TranslatedFields(
        name = models.CharField(max_length=255),
    )

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['rank', 'translations__name']


class Feature(TranslatableModel):
    """
    A feature is a question that should be answered with a number, not text
    Example: instaed of "Support = Phone", use "Support by phone = 1"
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="features", blank=True, null=True)
    code = models.CharField(max_length=100, unique=True)
    rank = models.IntegerField(default=10)
    is_binary = models.BooleanField(default=True)

    translations = TranslatedFields(
        name = models.CharField(max_length=255),
        description = models.CharField(max_length=512, null=True)
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['rank','category', 'translations__name']


class Plan(TranslatableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    code = models.CharField(max_length=100, unique=True)
    rank = models.IntegerField(default=0)
    monthly_price = models.DecimalField(max_digits=8, decimal_places=0, default=0, verbose_name="Monthly price")
    year_months = models.IntegerField(default=12, verbose_name="Year months")
    features = models.ManyToManyField(Feature, through='Allowance')

    translations = TranslatedFields(
        name = models.CharField(max_length=255),
        description = models.CharField(max_length=512, null=True)
    )

    @property
    def yearly_price(self):
        y = self.year_months if self.year_months else 12
        return round(y * self.monthly_price / 12, 2)

    @property
    def free_months(self):
        return 12 - self.year_months

    @property
    def yearly_discount_amount(self):
        return - self.free_months * self.yearly_price

    @property
    def yearly_discount_rate(self):
        return - round(self.free_months / 12, 2)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['rank', 'translations__name']


class Allowance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    capability = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.plan.code}x{self.feature.code}={self.capability}"

    class Meta:
        ordering = ['plan']
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "feature"],
                name="unique_plan_feature_allowance",
            ),
        ]


class Order(models.Model):
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("confirmed", _("Confirmed")),
        ("pending", _("Pending Payment")),
        ("complete", _("Complete")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=64, editable=False, verbose_name=_("Number"))
    date_placed  = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Date"))
    team = models.ForeignKey(Team, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", verbose_name=_("Status"))
    delivery_address = models.TextField(null=True, verbose_name=_("Delivery address"))
    billing_address = models.TextField(null=True, verbose_name=_("Billing address"))
    billing_email = models.EmailField()

    created  = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name="Date created")
    updated  = models.DateTimeField(blank=True, null=True, verbose_name="Date updated")

    def __str__(self):
        return f"{self.numero}"

    class Meta:
        ordering = ['-date_placed']

    @property
    def total_amount_ht(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_taxes(self):
        return sum(item.taxes_amount for item in self.items.all())

    @property
    def total_amount_ttc(self):
        return self.total_amount_ht + self.total_taxes
    
    def save(self, *args, **kwargs):
        # Only generate an order number if it hasn't been assigned yet
        current_year = 0

        if not self.numero:
            current_year = timezone.now().year % 100

        with transaction.atomic():
            # Lock the sequence row for this specific year to prevent race conditions
            sequence, created = YearlySequence.objects.select_for_update().get_or_create(
                name="order", year=current_year, defaults={"next_value": 1}
            )

            seq_num = sequence.next_value
            sequence.next_value += 1
            sequence.save()
            sequence_date = self.date_placed if self.date_placed else timezone.now()
            elapsed_days = sequence_date.timetuple().tm_yday
            # elapsed_days = self.date_placed.timetuple().tm_yday if self.date_placed else 1

            # Format the number: ORD-26217-0001
            self.numero = f"ORD-{current_year:02d}{elapsed_days:03d}-{seq_num:04d}"

        super().save(*args, **kwargs)


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item_reference = models.CharField(max_length=128, verbose_name=_("Reference"))
    item_name = models.CharField(max_length=256, verbose_name=_("Item"))
    item_details = models.CharField(max_length=512, verbose_name=_("Details"))
    quantity = models.IntegerField(default=1, verbose_name=_("Quantity"))
    units = models.CharField(default="U", null=True, verbose_name=_("Unit"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Unit price"))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Line total"))
    taxes_percent = models.DecimalField(max_digits=10, decimal_places=2, default=20, verbose_name=_("Taxes %"))
    taxes_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Taxes amount"))
    unit_price_ttc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Unit price after taxes"))
    total_price_ttc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Line total after taxes"))
    
    class Meta:
        ordering = ['item_reference', 'item_name']


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("trial",       _("Trial")),
        ("active",      _("Active")),
        ("suspended",   _("Suspended")),
        ("cancelled",   _("Cancelled")),
        ("paused",      _("Paused")),
        ("expired",     _("Expired")),
    ]

    COMMIT_CHOICES = [
        (1, "1M"), 
        (12, "12M"), 
        (24, "24M"), 
        (60, "60M"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=64, editable=False, verbose_name=_("Number"))
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    subscribed_date = models.DateTimeField(auto_now_add=True)
    commitment = models.IntegerField(choices=COMMIT_CHOICES, default=0)
    ended_date = models.DateTimeField(null=True, blank=True)

    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.numero}-{self.team.name}"

    class Meta:
        ordering = ['-subscribed_date']
    
    def save(self, *args, **kwargs):
        # Only generate an order number if it hasn't been assigned yet
        current_year = 0

        if not self.numero:
            current_year = timezone.now().year % 100

        with transaction.atomic():
            # Lock the sequence row for this specific year to prevent race conditions
            sequence, created = YearlySequence.objects.select_for_update().get_or_create(
                name="subscription", year=current_year, defaults={"next_value": 1}
            )

            seq_num = sequence.next_value
            sequence.next_value += 1
            sequence.save()
            sequence_date = self.subscribed_date if self.subscribed_date else timezone.now()
            elapsed_days = sequence_date.timetuple().tm_yday
            # elapsed_days = self.subscribed_date.timetuple().tm_yday if self.subscribed_date else 1

            # Format the number: SUB-26001-0001
            self.numero = f"SUB-{current_year:02d}{elapsed_days:03d}-{seq_num:04d}"

        super().save(*args, **kwargs)


class Cycle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    date_start = models.DateTimeField()
    date_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.date_start.strftime("%y%m%d")}-{self.date_end.strftime("%y%m%d")}][{self.subscription.team.name}]@[{self.subscription.plan.code}]"

    class Meta:
        ordering = ['-date_end']

    # @property
    # def is_running(self, milmi=None):
    #     if self.date_end is None: 
    #         return False
    #     if milmi is None:
    #         milmi = datetime.now()
    #     if self.date_end < milmi:
    #         return False
    #     if self.date_start is None:
    #         return False
    #     if self.date_start > milmi:
    #         return False

    #     return True

    # @property
    # def remaining_days(self, milmi=None):
    #     if milmi is None:
    #         milmi = datetime.now()

    #     rd = self.date_end - milmi
    #     return rd.days


class Currency(TranslatableModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active = models.BooleanField(default=True)
    symbol = models.CharField(max_length=5, default="$")
    label = models.CharField(max_length=8, default="USD")
    # name = models.CharField(max_length=64, default=_("US Dollar"))
    value_in_dhs = models.DecimalField(max_digits=6, decimal_places=2, default=10)
    symbol_first = models.BooleanField(default=False)

    translations = TranslatedFields(
        name = models.CharField(max_length=64, default=_("US Dollar"))
    )

    # def __str__(self):
    #     return self.translations.name

    class Meta:
        ordering = ['translations__name']


class Payment(models.Model):
    METHOD_CHOICES = [
        ("cash", _("Cash")),
        ("bank", _("Bank Transfer")),
        ("wire", _("Wire Transfer")),
        ("check", _("Check")),
        ("other", _("Other")),
    ]

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("confirmed", _("Confirmed")),
        ("failed", _("Failed")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=64, editable=False, verbose_name=_("Number"))
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, null=True)
    currency_rate = models.IntegerField(default=1)
    reference = models.CharField(max_length=255, blank=True)
    made_by = models.CharField(max_length=255, blank=True)
    confirmed_by = models.CharField(max_length=255, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.numero}#{self.amount}#{self.order.team.name}"
    
    def save(self, *args, **kwargs):
        # Only generate an order number if it hasn't been assigned yet
        current_year = 0

        if not self.numero:
            current_year = timezone.now().year % 100

        with transaction.atomic():
            # Lock the sequence row for this specific year to prevent race conditions
            sequence, created = YearlySequence.objects.select_for_update().get_or_create(
                name="payment", year=current_year, defaults={"next_value": 1}
            )

            seq_num = sequence.next_value
            sequence.next_value += 1
            sequence.save()
            sequence_date = self.paid_at if self.paid_at else timezone.now()
            elapsed_days = sequence_date.timetuple().tm_yday
            # elapsed_days = self.paid_at.timetuple().tm_yday if self.paid_at else 1

            # Format the number: PAY-26001-0001
            self.numero = f"PAY-{current_year:02d}{elapsed_days:03d}-{seq_num:04d}"

        super().save(*args, **kwargs)


class Refund(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=255, blank=True)
    made_by = models.CharField(max_length=255, blank=True)
    confirmed_by = models.CharField(max_length=255, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SubscriptionChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    old_plan = models.ForeignKey(Plan, null=True, on_delete=models.CASCADE, related_name="changes_from")
    new_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="changes_to")
    reason = models.CharField(max_length=255, blank=True)
    date_ordered = models.DateTimeField(null=True)
    date_effective = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)




class YearlySequence(models.Model):
    name = models.CharField(max_length=50)  # e.g., 'order' or 'payment'
    year = models.IntegerField()
    next_value = models.IntegerField(default=1)

    class Meta:
        unique_together = ("name", "year")

    def __str__(self):
        return f"{self.name} ({self.year}): {self.next_value}"