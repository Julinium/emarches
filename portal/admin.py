from django.contrib import admin
from base.models import Crawler
from nas.models import TenderView, Download

@admin.register(Crawler)
class CrawlerAdmin(admin.ModelAdmin):
    list_display = (
        'finished', 'formatted_duration', 'import_links', 'links_digest', 
        'tenders_digest', 'saving_errors', 'files_digest')
    list_filter = ('finished', 'saving_errors')
    # actions = None
    # list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def formatted_duration(self, obj):
        return str(obj.duration).split('.')[0]

    def links_digest(self, obj):
        return f"{ obj.links_crawled }⚫{ obj.links_imported }⚫{ obj.links_from_saved }"

    def tenders_digest(self, obj):
        return f"{ obj.tenders_created }⚫{ obj.tenders_updated }"

    def files_digest(self, obj):
        return f"{ obj.files_downloaded }⚫{ obj.files_failed }"

    formatted_duration.short_description = 'Duration'
    links_digest.short_description = 'Links: C⚫I⚫S'
    tenders_digest.short_description = 'Tenders: C⚫U'
    files_digest.short_description = 'Files: D⚫F'


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