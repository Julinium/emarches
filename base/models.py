
import uuid, traceback, re
from os import path as path
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Agrement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'base_agrement'
        ordering = ['name']
        verbose_name = _("")
    
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
            if self.label[0] == "F": return 'basket'
            if self.label[0] == "S": return 'gear'
            if self.label[0] == "T": return 'cone-striped'
        except: pass

        return 'question-circle'


class Change(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tender = models.ForeignKey('Tender', on_delete=models.CASCADE, related_name="changes", db_column='tender', blank=True, null=True, verbose_name=_("Tender"))    
    reported = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Date Reported"))
    changes = models.TextField(blank=True, null=True, verbose_name=_("Changes"))

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

    class Meta:
        db_table = 'base_client'
        ordering = ['ministery', 'name']
        verbose_name = _("Client")
        # verbose_name_plural = _("")
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
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
        verbose_name = _("Kind")
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
        # verbose_name_plural = _("")
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"


class Mode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Acronym"))
    name = models.CharField(max_length=2048, blank=True, null=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'base_mode'
        ordering = ['name']
        verbose_name = _("Mode")
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

    # has_agrements = None
    # has_qualifs = None
    # first_sample = None
    # first_meeting = None
    # first_visit = None

    class Meta:
        db_table = 'base_tender'
        verbose_name = _("Tender")

    def __str__(self):
        return f"{self.chrono} - {self.reference}: {self.title}"
    
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


    def save(self, *args, **kwargs):
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
        verbose_name = _("Lot")
    
    def __str__(self):
        return f"{ self.tender.chrono } - { self.number } - { self.title }"


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
        verbose_name = _("Sample")
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"


class Visit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    when = models.DateTimeField(blank=True, null=True, verbose_name=_("Date"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    lot = models.ForeignKey('Lot', on_delete=models.CASCADE, related_name="visits", db_column='lot', blank=True, null=True, verbose_name=_("Lot"))

    class Meta:
        db_table = 'base_visit'
        ordering = ['-when']
        verbose_name = _("Visit")
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"


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

    def save(self, *args, **kwargs):
        if self.pk is not None:
            self.updated = timezone.now()
        super().save(*args, **kwargs)

