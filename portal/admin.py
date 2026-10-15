from django.contrib import admin

from bdc.models import PurchaseOrder
from nas.models import Download, TenderView


@admin.register(TenderView)
class TenderViewAdmin(admin.ModelAdmin):
    list_display = ('get_tender_title', 'get_tender_id', 'get_username', 'when',)
    list_filter = ('when',)
    list_display_links = None

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        model._meta.verbose_name = "Tender View"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_tender_title(self, obj):
        return obj.tender.title

    def get_tender_id(self, obj):
        return obj.tender.id

    def get_username(self, obj):
        return obj.user.username

    get_tender_id.short_description = 'Tender ID'
    get_tender_title.short_description = 'Tender title'
    get_username.short_description = 'User'


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ('get_tender_title', 'get_tender_id', 'get_username', 'size_bytes', 'when',)
    list_filter = ('when',)
    list_display_links = None

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        model._meta.verbose_name = "Tender Download"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_tender_title(self, obj):
        return obj.tender.title

    def get_tender_id(self, obj):
        return obj.tender.id

    def get_username(self, obj):
        return obj.user.username

    get_tender_id.short_description = 'Tender ID'
    get_tender_title.short_description = 'Tender title'
    get_username.short_description = 'User'


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [f.name for f in PurchaseOrder._meta.fields]
    list_display = ['title', 'reference', 'deadline', 'published', 'client', 'category', 'deliberated']

    # def get_queryset(self, request):
    #     qs = super().get_queryset(request)
    #     return qs.filter(deliberated=None)

