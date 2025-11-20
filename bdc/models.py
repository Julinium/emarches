from django.db import models
from django.utils import timezone

from base.models import Category, Client

# Create your models here.

class PurchaseOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chrono = models.CharField(max_length=16, blank=True, null=True, verbose_name=_("Portal Id"))
    title = models.TextField(blank=True, null=True, verbose_name=_("Title"))
    reference = models.CharField(max_length=512, blank=True, null=True, verbose_name=_("Reference"))
    published = models.DateField(blank=True, null=True, verbose_name=_("Date published"))
    deadline = models.DateTimeField(blank=True, null=True, verbose_name=_("Bid deadline"))
    location = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_("Works execution location"))
    # size_read = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Files read size"))
    # size_bytes = models.BigIntegerField(blank=True, null=True, verbose_name=_("Files size (bytes)"))
    
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Date created"))
    updated = models.DateTimeField(blank=True, null=True, verbose_name=_("Date updated"))
    unsuccessful = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Unsuccessful"))
    link = models.CharField(max_length=256, blank=True, null=True, verbose_name=_("Official link"))
    
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, related_name="tenders", db_column='category', blank=True, null=True, verbose_name=_("Category"))
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, related_name='tenders', db_column='client', blank=True, null=True, verbose_name=_("Public client"))
    nature = models.TextField(blank=True, null=True, verbose_name=_("Nature of prestations"))
    
    bids_count = models.SmallIntegerField(blank=True, null=True, default=0, verbose_name=_("Bids count"))
    winner_amount = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Winner Amount Inc. taxes"))
    winner_entity = models.CharField(max_length=512, blank=True, null=True, verbose_name=_("Winner entity"))
    deliberated = models.DateTimeField(blank=True, null=True, verbose_name=_("Results published"))

    keywords = models.TextField(blank=True, null=True, editable=False)
    cliwords = models.TextField(blank=True, null=True, editable=False)
    refwords = models.TextField(blank=True, null=True, editable=False)
    locwords = models.TextField(blank=True, null=True, editable=False)


    class Meta:
        db_table = 'base_purchase_order'
        ordering = ['-deadline', 'id']
        verbose_name = _("Purchase Order")

    def __str__(self):
        return f"{self.chrono} - {self.reference}: {self.title}"
    
    @property
    def expired(self):
        try:
            rabat_now = timezone.localtime(timezone.now(), timezone=pytz.timezone('Africa/Casablanca'))
            return self.deadline <= rabat_now
        except: return None
    
    @property
    def days_to_go(self):
        try:
            rabat_now = timezone.localtime(timezone.now(), timezone=pytz.timezone('Africa/Casablanca'))
            delta_to_go = self.deadline.date() - rabat_now.date()
            return delta_to_go.days
        except: return 0

    @property
    def days_span(self):
        try:
            delta_span = self.deadline.date() - self.published
            return 1 + delta_span.days
        except: return 0

    def save(self, *args, **kwargs):
        self.keywords = nt(f"{ self.title } { self.chrono }")
        self.cliwords = nt(self.client.name)
        self.refwords = nt(self.reference)
        self.locwords = nt(self.location)

        self.updated = None
        if self.pk is not None:
            self.updated = timezone.now()

        super().save(*args, **kwargs)


class Article(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="articles", blank=True, null=True, verbose_name=_("Purchase Order"))
    number = models.CharField(max_length=16, blank=True, null=True, verbose_name=_("Number"))
    rank = models.SmallIntegerField(blank=True, null=True, default=1, verbose_name=_("Rank"))
    title = models.TextField(blank=True, null=True, verbose_name=_("Title"))
    specifications = models.TextField(blank=True, null=True, verbose_name=_("Specifications"))
    warranties = models.TextField(blank=True, null=True, verbose_name=_("Warranties"))

    uom = models.CharField(max_length=512, blank=True, null=True, default='U', verbose_name=_("Unit of Measure"))
    quantity = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Quantity"))
    vat_percent = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=20, verbose_name=_("VAT %"))


    class Meta:
        db_table = 'base_article'
        ordering = ['rank']
        verbose_name = _("Article")
    
    def __str__(self):
        return f"{ self.quantity } x { self.uom } - { self.title }"

    # def save(self, *args, **kwargs):
    #     tender = self.lot.tender
    #     tender.has_samples = True
    #     tender.save()

    #     super().save(*args, **kwargs)
