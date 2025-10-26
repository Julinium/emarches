from django.contrib import admin
from base.models import Crawler

@admin.register(Crawler)
class CrawlerAdmin(admin.ModelAdmin):
    list_display = (
        'finished', 'formatted_duration', 'import_links', 'saving_errors', 
        'tenders_created', 'tenders_updated', 'files_downloaded')
    # list_filter = ('finished', 'saving_errors')
    # list_display = ('id', 'other_field')

    def formatted_duration(self, obj):
        return str(obj.duration).split('.')[0]
        # return obj.duration_field.strftime('%Y-%m-%d %H:%M')  # Customize format here
    formatted_duration.short_description = 'Duration'  # Column header in admin
