from django.contrib import admin
from base.models import Crawler

@admin.register(Crawler)
class CrawlerAdmin(admin.ModelAdmin):
    list_display = (
        'finished', 'formatted_duration', 'import_links', 'links_digest', 
        'tenders_digest', 'saving_errors', 'files_downloaded')
    # list_filter = ('finished', 'saving_errors')
    # list_display = ('id', 'other_field')

    def formatted_duration(self, obj):
        return str(obj.duration).split('.')[0]

    def links_digest(self, obj):
        return f"{ obj.links_crawled }/{ obj.links_imported }/{ obj.links_from_saved }"

    def tenders_digest(self, obj):
        return f"{ obj.tenders_created }/{ obj.tenders_updated }"

    formatted_duration.short_description = 'Duration'  # Column header in admin
    links_digest.short_description = 'Links C/I/S'  # Column header in admin
    tenders_digest.short_description = 'Tenders C/U'  # Column header in admin