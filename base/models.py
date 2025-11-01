
import uuid, traceback, re
from os import path as path
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.indexes import GinIndex

from .texter import normalize_text as nt


class Agrement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'base_agrement'
        ordering = ['name']
        verbose_name = _("License")
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        try:
            self.short = re.split(r'[.-]', self.name, maxsplit=1)[0]
        except Exception as x:
            self.short = None
            traceback.print_exc()
        
        return super().save(*args, **kwargs)


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Name"))
    
    class Meta:
        db_table = 'base_category'
        ordering = ['label']
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
    
    def __str__(self):
        return self.label

    @property
    def icon_bs_class(self):
        try: 
            if self.label[0] == "F": return 'cart3' # 'basket'
            if self.label[0] == "S": return 'gear'
            if self.label[0] == "T": return 'cone-striped'
        except: pass

        return 'question-circle'


class Change(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tender = models.ForeignKey('Tender', on_delete=models.CASCADE, related_name="changes", db_column='tender', blank=True, null=True, verbose_name=_("Tender"))    
    reported = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Date Reported"))
    changes = models.TextField(blank=True, null=True, verbose_name=_("Changes"))
    # changed_field = models.CharField(max_length=128, null=True, blank=True, verbose_name=_("Changed field"))

    class Meta:
        db_table = 'base_change'
        ordering = ['-reported', 'tender']
        verbose_name = _("Change")
    
    def __str__(self):
        return f"{self.tender.chrono} - {self.reported}"


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))
    ministery = models.CharField(max_length=16, blank=True, null=True, verbose_name=_("Sector"))

    keywords = models.TextField(blank=True, null=True, editable=False)

    class Meta:
        db_table = 'base_client'
        ordering = ['ministery', 'name']
        verbose_name = _("Public Client")
        # verbose_name_plural = _("")
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.keywords = nt(self.name)
        try:
            if self.name.find("/") > -1:
                self.ministery = self.name.split("/")[0].strip()
        except Exception as x:
            traceback.print_exc()
        try:
            slash = ' / '
            s = self.name
            last_slash = s.rfind(slash)
            if last_slash != -1:
                dash = s.find(' - ', last_slash + len(slash))
                if dash != -1:
                    self.short = s[last_slash + len(slash):dash]
        except Exception as x:
            traceback.print_exc()

        # try:
        #     if self.name.find("/") > -1:
        #         r = self.name.split("/")[1].strip()
        #         if r.find("-") > -1:
        #             self.short = r.split("-")[0].strip()
        # except Exception as x:
        #     traceback.print_exc()
        
        return super().save(*args, **kwargs)


class Domain(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'base_domain'
        ordering = ['name']
        verbose_name = _("Domain")
        # verbose_name_plural = _("")
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        try:
            if self.name.find("/") > -1:
                self.short = self.name.rsplit("/", 1)[-1].strip()
        except Exception as x:
            self.short = None
            traceback.print_exc()
        
        return super().save(*args, **kwargs)


class Kind(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'base_kind'
        ordering = ['name']
        verbose_name = _("Type")
        # verbose_name_plural = _("")
    
    def __str__(self):
        return self.name


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    when = models.DateTimeField(blank=True, null=True, verbose_name=_("Date"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    lot = models.ForeignKey('Lot', on_delete=models.CASCADE, related_name="meetings", db_column='lot', blank=True, null=True, verbose_name=_("Lot"))

    class Meta:
        db_table = 'base_meeting'
        ordering = ['-when']
        verbose_name = _("Meeting")
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"

    def save(self, *args, **kwargs):
        tender = self.lot.tender
        tender.has_meetings = True
        tender.save()

        super().save(*args, **kwargs)


class Mode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'base_mode'
        ordering = ['name']
        verbose_name = _("Awarding Mode")
        # verbose_name_plural = _("")
    
    def __str__(self):
        return self.name


class Procedure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    restricted = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Restricted"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'base_procedure'
        ordering = ['name']
        verbose_name = _("Procedure")
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # if self.name
        lower_name = self.name.lower()
        restrictions = ['restreint', 'négocié', 'négociée', 'préselection', 'pré-selection']
        self.restricted = any(word.lower() in lower_name for word in restrictions)

        super().save(*args, **kwargs)


class Qualif(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))
    domain = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Domain"))
    classe = models.CharField(max_length=16, blank=True, null=True, verbose_name=_("Class"))

    class Meta:
        db_table = 'base_qualif'
        ordering = ['name']
        verbose_name = _("Qualification")
        # verbose_name_plural = _("")
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        try:
            if self.name.find("/ Classe ") > -1:
                self.classe = self.name.rsplit("/ Classe ", 1)[-1].strip()
        except Exception as x:
            self.classe = None
            traceback.print_exc()
        try:
            if self.name.find("/") > -1:
                self.domain = self.name.split("/", 1)[0].strip()
        except Exception as x:
            self.domain = None
            traceback.print_exc()

        try:
            short = None
            separator = "/"
            text = self.name
            first = text.find(separator)
            if first > 0:
                second = text.find(separator, first + len(separator))
                if second > 0:
                    third = text.find(separator, second + len(separator))
                    if third > 0:
                        start = second + len(separator)
                        short = text[start:third].strip()
                        if short.find(" ") > -1:
                            short = short.split(" ", 1)[0].strip()
                        if short.find("-") > -1:
                            short = short.strip("-")
                        f1 = short.find(".")
                        if f1 > 0:
                            s2 = short.find(".", f1 + len("."))
                            if s2 > 0:
                                short = short[:s2]
            if short:
                self.short = short
        except Exception as x:
            self.short = None
            traceback.print_exc()
        
        return super().save(*args, **kwargs)


class Tender(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chrono = models.CharField(max_length=16, blank=True, null=True, verbose_name=_("Portal Id"))
    title = models.TextField(blank=True, null=True, verbose_name=_("Title"))
    reference = models.CharField(max_length=512, blank=True, null=True, verbose_name=_("Reference"))
    published = models.DateField(blank=True, null=True, verbose_name=_("Date published"))
    deadline = models.DateTimeField(blank=True, null=True, verbose_name=_("Bid deadline"))

    lots_count = models.SmallIntegerField(blank=True, null=True, default=0, verbose_name=_("Lots count"))
    estimate = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Total estimate"))
    bond = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Total bond"))
    plans_price = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0, verbose_name=_("Plans price"))

    reserved = models.BooleanField(blank=True, null=True, verbose_name=_("Reserved to SMB+"))
    variant = models.BooleanField(blank=True, null=True, verbose_name=_("Variants accepted"))
    has_agrements = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Licenses required"))
    has_qualifs = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Qualifications required"))
    has_samples = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Samples required"))
    has_meetings = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("In-site visits scheduled"))
    has_visits = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Meetings scheduled"))

    location = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_("Works execution location"))
    ebid = models.SmallIntegerField(blank=True, null=True, default=9, verbose_name=_("Electronic bid"))  # 1: Required, 0: Not required, Else: NA'
    esign = models.SmallIntegerField(blank=True, null=True, default=9, verbose_name=_("Electronic signature")) # 1: Required, 0: Not required, Else: NA'
    size_read = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Files read size"))
    size_bytes = models.BigIntegerField(blank=True, null=True, verbose_name=_("Files size (bytes)"))
    address_withdrawal = models.TextField(blank=True, null=True, verbose_name=_("Withdrawal address"))
    address_bidding = models.TextField(blank=True, null=True, verbose_name=_("Bidding address"))
    address_opening = models.TextField(blank=True, null=True, verbose_name=_("Awarding address"))
    contact_name = models.CharField(max_length=256, blank=True, null=True, verbose_name=_("Contact name"))
    contact_phone = models.CharField(max_length=256, blank=True, null=True, verbose_name=_("Contact phone"))
    contact_email = models.CharField(max_length=256, blank=True, null=True, verbose_name=_("Contact email"))
    contact_fax = models.CharField(max_length=256, blank=True, null=True, verbose_name=_("Contact fax"))
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Date created"))
    updated = models.DateTimeField(blank=True, null=True, verbose_name=_("Date updated"))
    cancelled = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Cancelled"))
    deleted = models.BooleanField(blank=True, null=True, default=False, verbose_name=_("Deleted"))
    link = models.CharField(max_length=256, blank=True, null=True, verbose_name=_("Official link"))
    acronym = models.CharField(max_length=8, blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, related_name="tenders", db_column='category', blank=True, null=True, verbose_name=_("Category"))
    mode = models.ForeignKey(Mode, on_delete=models.DO_NOTHING, related_name='tenders', db_column='mode', blank=True, null=True, verbose_name=_("Awarding mode"))
    procedure = models.ForeignKey(Procedure, on_delete=models.DO_NOTHING, related_name='tenders', db_column='procedure', blank=True, null=True, verbose_name=_("Procedure"))
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, related_name='tenders', db_column='client', blank=True, null=True, verbose_name=_("Public client"))
    kind = models.ForeignKey(Kind, on_delete=models.DO_NOTHING, related_name='tenders', db_column='kind', blank=True, null=True)
    ###### /!\ If you get the following error when migrating for the first time:
    # django.core.exceptions.FieldDoesNotExist: RelDomainTender has no field named 'tender'
    # Comment out the 'domains' field in 'Tender' class and the whole 'RelDomainTender' class definition.
    # Uncomment them after first migration succeeds and then make migrations and migrate. It should work.
    domains = models.ManyToManyField(Domain, through='RelDomainTender', related_name='tenders', verbose_name=_("Domains of activity"))

    keywords = models.TextField(blank=True, null=True, editable=False)
    cliwords = models.TextField(blank=True, null=True, editable=False)
    refwords = models.TextField(blank=True, null=True, editable=False)
    locwords = models.TextField(blank=True, null=True, editable=False)


    class Meta:
        db_table = 'base_tender'
        ordering = ['-deadline', 'id']
        verbose_name = _("Tender")
        indexes = [
            GinIndex(fields=['keywords'], name='keywords_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['cliwords'], name='cliwords_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['refwords'], name='refwords_idx', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['locwords'], name='locwords_idx', opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return f"{self.chrono} - {self.reference}: {self.title}"
    
    @property
    def expired(self):
        try:
            today_now = timezone.now()
            expired = self.deadline <= today_now
            return expired
        except: return None
    
    @property
    def days_to_go(self):
        try: 
            today_now = timezone.now()
            delta_to_go = self.deadline - today_now
            return delta_to_go.days
        except: return 0

    @property
    def progress_percent(self, full_bar = settings.TENDER_FULL_PROGRESS_DAYS):
        try:
            ratio = int(100 * self.days_to_go / full_bar)
            progress = max(0, min(ratio, 100))
            return progress
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
        if self.has_agrements == True:
            self.has_agrements = any(lot.agrements.count() > 0 for lot in self.lots.all())

        if self.has_qualifs == True:
            self.has_qualifs = any(lot.qualifs.count() > 0 for lot in self.lots.all())

        if self.has_meetings == True:
            self.has_meetings = any(lot.meetings.count() > 0 for lot in self.lots.all())

        if self.has_samples == True:
            self.has_samples = any(lot.samples.count() > 0 for lot in self.lots.all())

        if self.has_visits == True:
            self.has_visits = any(lot.visits.count() > 0 for lot in self.lots.all())

        self.updated = None
        if self.pk is not None:
            self.updated = timezone.now()

        super().save(*args, **kwargs)


class Lot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.SmallIntegerField(blank=True, null=True, verbose_name=_("Number"))
    title = models.TextField(blank=True, null=True, verbose_name=_("Title"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    estimate = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, verbose_name=_("Estimate"))
    bond = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, verbose_name=_("Bond"))
    reserved = models.BooleanField(blank=True, null=True, verbose_name=_("Reserved to SMB+"))
    variant = models.BooleanField(blank=True, null=True, verbose_name=_("Variants accepted"))
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, related_name="lots", db_column='category', blank=True, null=True, verbose_name=_("Category"))

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="lots", db_column='tender', blank=True, null=True)
    agrements = models.ManyToManyField(Agrement, through='RelAgrementLot', related_name='lots')
    qualifs = models.ManyToManyField(Qualif, through='RelQualifLot', related_name='lots')

    
    class Meta:
        db_table = 'base_lot'
        ordering = ['number']
    
    def __str__(self):
        return f"{ self.tender.chrono } - { self.number } - { self.title }"

    def save(self, *args, **kwargs):
        tender = self.tender
        if tender:
            if self.title: 
                if tender.keywords: tender.keywords = nt(self.title)
                else: tender.keywords += ' ' + nt(self.title)
            if self.description:
                if tender.keywords: tender.keywords = nt(self.description)
                else: tender.keywords += ' ' + nt(self.description)
            tender.has_agrements = self.agrements != None
            tender.has_qualifs = self.qualifs != None
            tender.save()

        super().save(*args, **kwargs)


class RelAgrementLot(models.Model):
    pk = models.CompositePrimaryKey('agrement', 'lot')
    agrement = models.ForeignKey('Agrement', on_delete=models.CASCADE, db_column='agrement')
    lot = models.ForeignKey('Lot', on_delete=models.CASCADE, db_column='lot')

    class Meta:
        db_table = 'base_rel_agrement_lot'
        unique_together = ('agrement', 'lot')


class RelDomainTender(models.Model):
    ###### /!\ If you get the following error when migrating for the first time:
    # django.core.exceptions.FieldDoesNotExist: RelDomainTender has no field named 'tender'
    # Comment out the 'domains' field in 'Tender' class and the whole 'RelDomainTender' class definition.
    # Uncomment them after first migration succeeds and then make migrations and migrate. It should work.
    pk = models.CompositePrimaryKey('domain', 'tender')
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, db_column='tender')
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, db_column='domain')

    class Meta:
        db_table = 'base_rel_domain_tender'
        unique_together = ('domain', 'tender')


class RelQualifLot(models.Model):
    pk = models.CompositePrimaryKey('qualif', 'lot')
    qualif = models.ForeignKey(Qualif, on_delete=models.CASCADE, db_column='qualif')
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, db_column='lot')

    class Meta:
        db_table = 'base_rel_qualif_lot'
        unique_together = ('qualif', 'lot')


class Sample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    when = models.DateTimeField(blank=True, null=True, verbose_name=_("Date"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="samples", db_column='lot', blank=True, null=True, verbose_name=_("Lot"))

    class Meta:
        db_table = 'base_sample'
        ordering = ['-when']
        # verbose_name = _("Sample")
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"

    def save(self, *args, **kwargs):
        tender = self.lot.tender
        tender.has_samples = True
        tender.save()

        super().save(*args, **kwargs)


class Visit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    when = models.DateTimeField(blank=True, null=True, verbose_name=_("Date"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    lot = models.ForeignKey('Lot', on_delete=models.CASCADE, related_name="visits", db_column='lot', blank=True, null=True, verbose_name=_("Lot"))

    class Meta:
        db_table = 'base_visit'
        ordering = ['-when']
        # verbose_name = _("Visit")
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"

    def save(self, *args, **kwargs):
        tender = self.lot.tender
        tender.has_visits = True
        tender.save()

        super().save(*args, **kwargs)


class FileToGet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    closed = models.BooleanField(blank=True, null=True, default=False)
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    updated = models.DateTimeField(blank=True, null=True)
    reason = models.CharField(max_length=256, blank=True, null=True, default="Created")
    tender = models.ForeignKey('Tender', on_delete=models.CASCADE, related_name="files_to_get", db_column='tender', blank=True, null=True)
    
    class Meta:
        db_table = 'base_file_to_get'
        ordering = ['-closed', 'created']
        # verbose_name = _("File to get")
        # verbose_name_plural = _("Files to get")

    def save(self, *args, **kwargs):
        if self.pk is not None:
            self.updated = timezone.now()
        super().save(*args, **kwargs)


class Crawler(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started = models.DateTimeField(blank=True, null=True, verbose_name=_("Started"))
    finished = models.DateTimeField(blank=True, null=True, verbose_name=_("Finished"))
    
    import_links = models.BooleanField(blank=True, null=True, default=False)

    links_crawled = models.SmallIntegerField(blank=True, null=True, default=0)
    links_imported = models.SmallIntegerField(blank=True, null=True, default=0)
    links_from_saved = models.SmallIntegerField(blank=True, null=True, default=0)

    tenders_created = models.SmallIntegerField(blank=True, null=True, default=0)
    tenders_updated = models.SmallIntegerField(blank=True, null=True, default=0)
    files_downloaded = models.SmallIntegerField(blank=True, null=True, default=0)
    files_failed = models.SmallIntegerField(blank=True, null=True, default=0)

    saving_errors = models.BooleanField(blank=True, null=True, default=False)

    class Meta:
        db_table = 'base_crawler'
        ordering = ['-finished']
    
    def __str__(self):
        return f"{ self.started } - { self.finished }"
    
    @property
    def duration(self):
        if self.started and self.finished:
            return self.finished - self.started
        return None



