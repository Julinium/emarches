from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from bidding.models import Team


class Plan(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    caption = models.CharField(max_length=512)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    trial_days = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Payment"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    billing_email = models.EmailField()

    created  = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name="Date created")
    updated  = models.DateTimeField(blank=True, null=True, verbose_name="Date updated")

    def __str__(self):
        return f"Order #{self.id}"


# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
#     plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
#     quantity = models.IntegerField(default=1)
#     unit_price = models.DecimalField(max_digits=10, decimal_places=2)
#     total_price = models.DecimalField(max_digits=10, decimal_places=2)


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


# class Subscription(models.Model):
#     STATUS_CHOICES = [
#         ("trialing", "Trialing"),
#         ("active", "Active"),
#         ("past_due", "Past Due"),
#         ("paused", "Paused"),
#         ("cancelled", "Cancelled"),
#         ("expired", "Expired"),
#     ]

#     customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
#     plan = models.ForeignKey(Plan, on_delete=models.PROTECT)

#     status = models.CharField(max_length=20, choices=STATUS_CHOICES)

#     start_date = models.DateTimeField()
#     current_period_start = models.DateTimeField()
#     current_period_end = models.DateTimeField()

#     trial_end = models.DateTimeField(null=True, blank=True)

#     cancel_at_period_end = models.BooleanField(default=False)

#     ended_at = models.DateTimeField(null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Subscription #{self.id}"


# class SubscriptionEvent(models.Model):
#     TYPE_CHOICES = [
#         ("created", "Created"),
#         ("trial_started", "Trial Started"),
#         ("trial_ended", "Trial Ended"),
#         ("renewed", "Renewed"),
#         ("upgraded", "Upgraded"),
#         ("downgraded", "Downgraded"),
#         ("cancelled", "Cancelled"),
#         ("reactivated", "Reactivated"),
#     ]

#     subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
#     type = models.CharField(max_length=30, choices=TYPE_CHOICES)
#     metadata = models.JSONField(blank=True, null=True)

#     created_at = models.DateTimeField(auto_now_add=True)


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

