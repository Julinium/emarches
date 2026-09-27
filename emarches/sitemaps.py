# sitemaps.py
from django.contrib.sitemaps import Sitemap
from base.models import Concurrent, Tender

class ConcurrentSitemap(Sitemap):
    limit = 5000
    changefreq = "weekly" # How often content updates
    priority = 0.8        # Priority relative to other pages (0.0 - 1.0)

    def items(self):
        return Concurrent.objects.all().order_by('name')

    # def lastmod(self, obj):
    #     d = obj.deposits.first()
    #     return d.date if d and d.date else None

class TenderSitemap(Sitemap):
    limit = 5000
    changefreq = "weekly" # How often content updates
    priority = 0.8        # Priority relative to other pages (0.0 - 1.0)

    def items(self):
        return Tender.objects.all().order_by('-published')

    def lastmod(self, obj):
        return obj.published