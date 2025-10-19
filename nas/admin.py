from django.contrib import admin
from .models import Company, Notification

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'activity', 'user', 'active', 'created')
    list_filter = ('active', 'city', 'sector')
    search_fields = ('name', 'ice', 'activity', 'city')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'event', 'channel')
    list_filter = ('channel', 'active')
    search_fields = ('name', 'event', 'description')

