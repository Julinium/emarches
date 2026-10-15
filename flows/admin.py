
from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from parler.admin import TranslatableAdmin

from nas.models import Company
from bidding.models import Team, TeamMember

from .models import (
    Category,
    Feature,
    Plan,
    Allowance,
    Order,
    OrderItem,
    Subscription,
    Cycle,
    Payment,
    Refund,
    SubscriptionChange,
    Currency,
)

User = get_user_model()


# ---------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------

@admin.register(Currency)
class CurrencyAdmin(TranslatableAdmin):
    list_display = (
        "label",
        "display_name",
        "symbol",
        "value_in_dhs",
        "symbol_first",
        "active",
    )
    list_display_links = ("label",)
    list_editable = ("active",)
    list_filter = ("active", "symbol_first")
    search_fields = ("label", "translations__name", "symbol")
    ordering = ("translations__name", "label",)
    readonly_fields = ("id",)

    def display_name(self, obj):
        return obj.safe_translation_getter(
            "name",
            any_language=True,
            default="—",
        )

    display_name.short_description = _("Name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.translated("en").distinct()


# ---------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------

class CompanyAdminForm(forms.ModelForm):
    # The model declares user as editable=False, but administrators
    # need to select the owner when creating a company.
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        label=_("Owner"),
    )

    class Meta:
        model = Company
        fields = "__all__"


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    form = CompanyAdminForm

    list_display = (
        "name",
        "user",
        "forme",
        "ice",
        "rc",
        "email",
        "active",
        "created",
    )
    list_display_links = ("name",)
    list_filter = ("active", "forme", "created")
    search_fields = (
        "name",
        "user__username",
        "user__email",
        "ice",
        "rc",
        "email",
        "activity",
    )
    ordering = ("name",)
    readonly_fields = ("id", "created", "updated", "active")
    filter_horizontal = ("agrements", "qualifs")

    fieldsets = (
        (None, {
            "fields": ("id", "user", "name", "active")
        }),
        (_("Legal information"), {
            "fields": ("forme", "ice", "rc", "activity")
        }),
        (_("Contact"), {
            "fields": ("address", "email", "website")
        }),
        (_("Additional information"), {
            "fields": ("note", "image", "file", "agrements", "qualifs")
        }),
        (_("Timestamps"), {
            "fields": ("created", "updated"),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------

class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 1

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "creator", "active", "created", "updated")
    list_display_links = ("name",)
    list_editable = ("active",)
    list_filter = ("active", "created")
    search_fields = (
        "name",
        "creator__username",
        "creator__email",
        "members__username",
        "members__email",
    )
    ordering = ("name",)
    readonly_fields = ("id", "creator", "created", "updated")
    # filter_horizontal = ("members",)
    inlines = [TeamMemberInline]


# ---------------------------------------------------------------------
# Categories and features
# ---------------------------------------------------------------------

@admin.register(Category)
class CategoryAdmin(TranslatableAdmin):
    list_display = ("display_name", "code", "rank", "active")
    list_display_links = ("display_name",)
    list_editable = ("rank", "active")
    list_filter = ("active",)
    search_fields = ("translations__name", "code")
    ordering = ("rank", "translations__name")
    readonly_fields = ("id",)

    def display_name(self, obj):
        return obj.safe_translation_getter(
            "name",
            any_language=True,
            default="—",
        )

    display_name.short_description = _("Name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.translated("en").distinct()
    

@admin.register(Feature)
class FeatureAdmin(TranslatableAdmin):
    list_display = ("display_name", "code", "category", "is_binary", "active")
    list_display_links = ("display_name",)
    list_editable = ("active",)
    list_filter = ("active", "is_binary", "category")
    search_fields = ("translations__name", "code", "description", "category__translations__name")
    ordering = ("category__rank", "rank", "translations__name")
    readonly_fields = ("id",)
    autocomplete_fields = ("category",)

    def display_name(self, obj):
        return obj.safe_translation_getter(
            "name",
            any_language=True,
            default="—",
        )

    display_name.short_description = _("Name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.translated("en").distinct()

# ---------------------------------------------------------------------
# Plans and allowances
# ---------------------------------------------------------------------

class AllowanceInline(admin.TabularInline):
    model = Allowance
    extra = 1
    autocomplete_fields = ("feature",)
    fields = ("feature", "capability")
    ordering = ("feature__translations__name",)


@admin.register(Plan)
class PlanAdmin(TranslatableAdmin):
    list_display = (
        "display_name",
        "code",
        "monthly_price",
        "rank",
        "active",
        "allowance_count",
    )
    list_display_links = ("display_name",)
    list_editable = ("monthly_price", "rank", "active")
    list_filter = ("active",)
    search_fields = ("translations__name", "code", "description")
    ordering = ["rank"]
    readonly_fields = ("id",)
    inlines = (AllowanceInline,)

    @admin.display(description=_("Features"))
    def allowance_count(self, obj):
        return obj.allowance_set.count()

    def display_name(self, obj):
        return obj.safe_translation_getter(
            "name",
            any_language=True,
            default="—",
        )

    display_name.short_description = _("Name")

    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     return qs.translated("en").distinct()


@admin.register(Allowance)
class AllowanceAdmin(admin.ModelAdmin):
    list_display = ("plan", "feature", "capability")
    list_display_links = ("plan", "feature")
    list_editable = ("capability",)
    list_filter = ("plan", "feature__category")
    search_fields = (
        "plan__translations__name",
        "plan__code",
        "feature__translations__name",
        "feature__code",
    )
    ordering = ("plan__rank", "feature__translations__name")
    readonly_fields = ("id",)
    autocomplete_fields = ("plan", "feature")


# ---------------------------------------------------------------------
# Orders and order items
# ---------------------------------------------------------------------

class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        team_id = (
            self.data.get("team")
            or self.initial.get("team")
            or getattr(self.instance, "team_id", None)
        )

        companies = Company.objects.none()

        if team_id:
            companies = Company.objects.filter(
                user__teams__id=team_id
            ).distinct()

        self.fields["company"].queryset = companies


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    show_change_link = True
    fields = (
        "item_reference",
        "item_name",
        "item_details",
        "quantity",
        "units",
        "unit_price",
        "total_price",
        "taxes_percent",
        "taxes_amount",
        "unit_price_ttc",
        "total_price_ttc",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    autocomplete_fields = ("team", "company")

    list_display = (
        "numero",
        "date_placed",
        "team",
        "company",
        "status",
        "total_amount_ht",
        "total_taxes",
        "total_amount_ttc",
    )
    list_display_links = ("numero",)
    list_filter = ("status", "date_placed")
    search_fields = (
        "numero",
        "team__name",
        "company__name",
        "billing_email",
    )
    ordering = ("-date_placed",)
    date_hierarchy = "date_placed"
    readonly_fields = (
        "id",
        "numero",
        "date_placed",
        "created",
        "updated",
        "total_amount_ht",
        "total_taxes",
        "total_amount_ttc",
    )
    autocomplete_fields = ("team", "company")
    inlines = (OrderItemInline,)

    fieldsets = (
        (None, {
            "fields": (
                "id", "numero", "status", "date_placed",
                "team", "company",
            )
        }),
        (_("Billing"), {
            "fields": ("billing_email", "billing_address")
        }),
        (_("Delivery"), {
            "fields": ("delivery_address",)
        }),
        (_("Totals"), {
            "fields": (
                "total_amount_ht",
                "total_taxes",
                "total_amount_ttc",
            )
        }),
        (_("Timestamps"), {
            "fields": ("created", "updated"),
            "classes": ("collapse",),
        }),
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_reference",
        "item_name",
        "order",
        "quantity",
        "unit_price",
        "total_price",
        "total_price_ttc",
    )
    list_display_links = ("item_reference", "item_name")
    search_fields = (
        "item_reference",
        "item_name",
        "order__numero",
        "order__team__name",
    )
    ordering = ("item_reference", "item_name")
    readonly_fields = ("id",)
    autocomplete_fields = ("order",)


# ---------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "team",
        "plan",
        "status",
        "commitment",
        "subscribed_date",
        "ended_date",
        "auto_renew",
    )
    list_display_links = ("numero",)
    list_filter = ("status", "commitment", "auto_renew", "plan")
    search_fields = (
        "numero",
        "team__name",
        "plan__name",
        "plan__code",
    )
    ordering = ("-subscribed_date",)
    date_hierarchy = "subscribed_date"
    readonly_fields = ("id", "numero", "subscribed_date", "created_at")
    autocomplete_fields = ("team", "plan")

    fieldsets = (
        (None, {
            "fields": (
                "id", "numero", "team", "plan",
                "status", "commitment",
            )
        }),
        (_("Subscription period"), {
            "fields": (
                "subscribed_date", "ended_date",
                "trial_start", "trial_end", "auto_renew",
            )
        }),
        (_("Timestamps"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------
# Subscription cycles
# ---------------------------------------------------------------------

@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "order",
        "date_start",
        "date_end",
        "created_at",
    )
    list_filter = ("date_start", "date_end")
    search_fields = (
        "subscription__numero",
        "subscription__team__name",
        "order__numero",
    )
    ordering = ("-date_end",)
    date_hierarchy = "date_start"
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("subscription", "order")


# ---------------------------------------------------------------------
# Payments and refunds
# ---------------------------------------------------------------------

class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    show_change_link = True
    fields = (
        "amount", "reason", "reference",
        "made_by", "confirmed_by", "confirmed_at",
        "created_at",
    )
    readonly_fields = ("created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "order",
        "team_name",
        "amount",
        "currency",
        "status",
        "method",
        "paid_at",
        "confirmed_at",
    )
    list_display_links = ("numero",)
    list_filter = ("status", "method", "currency", "paid_at")
    search_fields = (
        "numero",
        "order__numero",
        "order__team__name",
        "reference",
        "made_by",
        "confirmed_by",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "numero", "created_at")
    autocomplete_fields = ("order", "currency")
    inlines = (RefundInline,)

    fieldsets = (
        (None, {
            "fields": (
                "id", "numero", "order", "method",
                "status", "amount", "currency", "currency_rate",
            )
        }),
        (_("References"), {
            "fields": ("reference", "description", "made_by")
        }),
        (_("Confirmation"), {
            "fields": ("confirmed_by", "confirmed_at", "paid_at")
        }),
        (_("Timestamps"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description=_("Team"), ordering="order__team__name")
    def team_name(self, obj):
        return obj.order.team.name


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        "payment",
        "amount",
        "reason",
        "reference",
        "confirmed_by",
        "confirmed_at",
        "created_at",
    )
    list_filter = ("confirmed_at", "created_at")
    search_fields = (
        "payment__numero",
        "payment__order__numero",
        "payment__order__team__name",
        "reference",
        "reason",
        "made_by",
        "confirmed_by",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("payment",)

    fieldsets = (
        (None, {
            "fields": ("id", "payment", "amount", "reason", "reference")
        }),
        (_("Processing"), {
            "fields": (
                "made_by", "confirmed_by",
                "confirmed_at", "description",
            )
        }),
        (_("Timestamps"), {
            "fields": ("created_at",),
            "classes": ("collapse",),
        }),
    )


# ---------------------------------------------------------------------
# Subscription plan changes
# ---------------------------------------------------------------------

@admin.register(SubscriptionChange)
class SubscriptionChangeAdmin(admin.ModelAdmin):
    list_display = (
        "subscription",
        "old_plan",
        "new_plan",
        "date_ordered",
        "date_effective",
        "created_at",
    )
    list_filter = ("date_ordered", "date_effective")
    search_fields = (
        "subscription__numero",
        "subscription__team__name",
        "old_plan__name",
        "new_plan__name",
        "reason",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("subscription", "old_plan", "new_plan")
