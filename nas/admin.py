from django.contrib import admin
from .models import Company, Folder, Notification, Newsletter, NotificationSubscription, NewsletterSubscription


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'ice', 'user', 'city', 'active', 'created')
    list_filter = ('active', 'city', 'sector')
    search_fields = ('name', 'ice', 'ice', 'city')

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'image', 'color', 'comment')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'event', 'channel')
    list_filter = ('channel', 'active')
    search_fields = ('name', 'event', 'description')


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('notification', 'user', 'active', 'when')
    list_filter = ('active',)
    # search_fields = ('user','notification')


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'monthly', 'channel')
    list_filter = ('channel', 'active')
    search_fields = ('name', 'description')


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('newsletter', 'user', 'active', 'when')
    list_filter = ('active',)
    # search_fields = ('user', 'newsletter')

