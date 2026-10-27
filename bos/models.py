from django.db import models
from django.contrib.postgres.search import SearchVectorField

class Bulletin(models.Model):
    bo_num = models.CharField(max_length=50, unique=True)
    bo_date = models.DateField(null=True, blank=True)
    bo_url = models.URLField(max_length=500)
    extracted_text = models.TextField(blank=True, null=True, help_text="Cached text extracted from PDF")
    updated_at = models.DateTimeField(auto_now=True)
    
    search_vector = SearchVectorField(null=True)

    def __str__(self):
        return f"BO {self.bo_num} - {self.bo_date}"


class SearchLog(models.Model):
    url = models.CharField(max_length=2000)
    method = models.CharField(max_length=10)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    query_params = models.TextField(blank=True)
    search_query = models.TextField(blank=True)
    date_fm = models.CharField(max_length=16)
    date_to = models.CharField(max_length=16)
    results_count = models.IntegerField(default=0)
    truncated = models.BooleanField(default=False)
    exact_check = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.method} {self.url} ({self.ip_address})"

class DownloadLog(models.Model):
    numero = models.CharField(max_length=64, default="0000")
    url = models.CharField(max_length=2000)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.url} ({self.ip_address})"

    