from django.contrib import admin
from .models import Company

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'activity', 'user', 'active', 'created')
    list_filter = ('active', 'city', 'sector')
    search_fields = ('name', 'ice', 'activity', 'city')