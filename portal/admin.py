from django.contrib import admin
from base.models import Crawler

@admin.register(Crawler)
class CrawlerAdmin(admin.ModelAdmin):
    list_display = ('finished', 'import_links', 'saving_errors')
    list_filter = ('finished', 'saving_errors')