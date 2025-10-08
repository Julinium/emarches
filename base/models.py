
import uuid, traceback, re

from os import path as path
from django.db import models
from django.utils import timezone


class Agrement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True)
    name = models.CharField(max_length=2048, blank=True, null=True)

    class Meta:
        db_table = 'agrement'
        ordering = ['name']
    
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
    label = models.CharField(max_length=128, blank=True, null=True)

    class Meta:
        db_table = 'category'
        ordering = ['label']
    
    def __str__(self):
        return self.label


class Change(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tender = models.ForeignKey('Tender', on_delete=models.CASCADE, related_name="changes", db_column='tender', blank=True, null=True)    
    reported = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    changes = models.CharField(max_length=4096, blank=True, null=True)

    class Meta:
        db_table = 'change'
        ordering = ['-reported', 'tender']
    
    def __str__(self):
        return f"{self.tender.chrono} - {self.reported}"


class Client(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True)
    name = models.CharField(max_length=2048, blank=True, null=True)
    ministery = models.CharField(max_length=16, blank=True, null=True)

    class Meta:
        db_table = 'client'
        ordering = ['ministery', 'name']
    
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


# class Contact(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     when = models.DateTimeField(blank=True, null=True)
#     ua = models.CharField(max_length=512, blank=True, null=True)
#     ip = models.CharField(max_length=64, blank=True, null=True)
#     email = models.CharField(max_length=128, blank=True, null=True)
#     phone = models.CharField(max_length=64, blank=True, null=True)
#     title = models.CharField(max_length=256, blank=True, null=True)
#     message = models.TextField(blank=True, null=True)
#     method = models.CharField(max_length=8, blank=True, null=True)
#     newsletter = models.BooleanField(blank=True, null=True)
#     promos = models.BooleanField(blank=True, null=True)
#     comment = models.TextField(blank=True, null=True)
#     actions = models.TextField(blank=True, null=True)
#     solved = models.BooleanField(blank=True, null=True)
#     utilizer = models.ForeignKey('Utilizer', on_delete=models.DO_NOTHING, related_name="contacts", db_column='utilizer', blank=True, null=True)

#     class Meta:
#         db_table = 'contact'
#         ordering = ['-when']
    
#     def __str__(self):
#         return self.title


class Domain(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=2048, blank=True, null=True)
    name = models.CharField(max_length=2048, blank=True, null=True)

    class Meta:
        db_table = 'domain'
        ordering = ['name']
    
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


# class Download(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     when = models.DateTimeField(blank=True, null=True)
#     bytes_media = models.BigIntegerField(blank=True, null=True)
#     ua = models.CharField(max_length=512, blank=True, null=True)
#     ip = models.CharField(max_length=64, blank=True, null=True)
#     tender = models.ForeignKey('Tender', on_delete=models.DO_NOTHING, related_name="downloads", db_column='tender', blank=True, null=True)
#     utilizer = models.ForeignKey('Utilizer', on_delete=models.DO_NOTHING, related_name="downloads", db_column='utilizer', blank=True, null=True)

#     class Meta:
#         db_table = 'download'
#         ordering = ['-when']
    
#     def __str__(self):
#         return f"{ self.tender.chrono } - { self.utilizer.username }"


# class Favo(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     when = models.DateTimeField(blank=True, null=True)
#     comment = models.TextField(blank=True, null=True)
#     ua = models.CharField(max_length=512, blank=True, null=True)
#     ip = models.CharField(max_length=64, blank=True, null=True)
#     utilizer = models.ForeignKey('Utilizer', on_delete=models.DO_NOTHING, related_name="favos", db_column='utilizer', blank=True, null=True)
#     tender = models.ForeignKey('Tender', on_delete=models.CASCADE, related_name="favos", db_column='tender', blank=True, null=True)

#     class Meta:
#         db_table = 'favo'
#         ordering = ['-when']
    
#     def __str__(self):
#         return f"{ self.tender.chrono } { self.utilizer.username }"


class Kind(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True)
    name = models.CharField(max_length=1024, blank=True, null=True)

    class Meta:
        db_table = 'kind'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    when = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    lot = models.ForeignKey('Lot', on_delete=models.CASCADE, related_name="meetings", db_column='lot', blank=True, null=True)

    class Meta:
        db_table = 'meeting'
        ordering = ['-when']
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"


class Mode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True)
    name = models.CharField(max_length=2048, blank=True, null=True)

    class Meta:
        db_table = 'mode'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Procedure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True)
    name = models.CharField(max_length=2048, blank=True, null=True)

    class Meta:
        db_table = 'procedure'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Qualif(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    short = models.CharField(max_length=128, blank=True, null=True)
    name = models.CharField(max_length=2048, blank=True, null=True)
    domain = models.CharField(max_length=128, blank=True, null=True)
    classe = models.CharField(max_length=16, blank=True, null=True)

    class Meta:
        db_table = 'qualif'
        ordering = ['name']
    
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
    chrono = models.CharField(max_length=16, blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    reference = models.CharField(max_length=512, blank=True, null=True)
    published = models.DateField(blank=True, null=True)
    deadline = models.DateTimeField(blank=True, null=True)

    lots_count = models.SmallIntegerField(blank=True, null=True, default=0)
    estimate = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0)
    bond = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0)
    plans_price = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0)
    reserved = models.BooleanField(blank=True, null=True)
    variant = models.BooleanField(blank=True, null=True)

    location = models.CharField(max_length=1024, blank=True, null=True)
    ebid = models.SmallIntegerField(blank=True, null=True, default=9)  # 1: Required, 0: Not required, Else: NA'
    esign = models.SmallIntegerField(blank=True, null=True, default=9) # 1: Required, 0: Not required, Else: NA'
    size_read = models.CharField(max_length=128, blank=True, null=True)
    size_bytes = models.BigIntegerField(blank=True, null=True)
    address_withdrawal = models.TextField(blank=True, null=True)
    address_bidding = models.TextField(blank=True, null=True)
    address_opening = models.TextField(blank=True, null=True)
    contact_name = models.CharField(max_length=256, blank=True, null=True)
    contact_phone = models.CharField(max_length=256, blank=True, null=True)
    contact_email = models.CharField(max_length=256, blank=True, null=True)
    contact_fax = models.CharField(max_length=256, blank=True, null=True)
    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
    updated = models.DateTimeField(blank=True, null=True)
    cancelled = models.BooleanField(blank=True, null=True, default=False)
    deleted = models.BooleanField(blank=True, null=True, default=False)
    link = models.CharField(max_length=256, blank=True, null=True)
    acronym = models.CharField(max_length=8, blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, related_name="tenders", db_column='category', blank=True, null=True)
    mode = models.ForeignKey(Mode, on_delete=models.DO_NOTHING, related_name='tenders', db_column='mode', blank=True, null=True)
    procedure = models.ForeignKey(Procedure, on_delete=models.DO_NOTHING, related_name='tenders', db_column='procedure', blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, related_name='tenders', db_column='client', blank=True, null=True)
    kind = models.ForeignKey(Kind, on_delete=models.DO_NOTHING, related_name='tenders', db_column='kind', blank=True, null=True)
    ###### /!\ If you get the following error when migrating for the first time:
    # django.core.exceptions.FieldDoesNotExist: RelDomainTender has no field named 'tender'
    # Comment out the 'domains' field in 'Tender' class and the whole 'RelDomainTender' class definition.
    # Uncomment them after first migration succeeds and then make migrations and migrate. It should work.
    domains = models.ManyToManyField(Domain, through='RelDomainTender', related_name='tenders')

    class Meta:
        db_table = 'tender'

    def __str__(self):
        return f"{self.chrono} - {self.reference}: {self.title}"

    def save(self, *args, **kwargs):
        self.updated = None
        if self.pk is not None:
            self.updated = timezone.now()

        super().save(*args, **kwargs)


class Lot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.SmallIntegerField(blank=True, null=True)
    title = models.TextField()
    description = models.TextField(blank=True, null=True)
    
    estimate = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    bond = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    reserved = models.BooleanField(blank=True, null=True)
    variant = models.BooleanField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, related_name="lots", db_column='category', blank=True, null=True)
    
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="lots", db_column='tender', blank=True, null=True)
    agrements = models.ManyToManyField(Agrement, through='RelAgrementLot', related_name='lots')
    qualifs = models.ManyToManyField(Qualif, through='RelQualifLot', related_name='lots')

    class Meta:
        db_table = 'lot'
        ordering = ['number']
    
    def __str__(self):
        return f"{ self.tender.chrono } - { self.number } - { self.title }"


class RelAgrementLot(models.Model):
    pk = models.CompositePrimaryKey('agrement', 'lot')
    agrement = models.ForeignKey('Agrement', on_delete=models.CASCADE, db_column='agrement')
    lot = models.ForeignKey('Lot', on_delete=models.CASCADE, db_column='lot')

    class Meta:
        db_table = 'rel_agrement_lot'
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
        db_table = 'rel_domain_tender'
        unique_together = ('domain', 'tender')


class RelQualifLot(models.Model):
    pk = models.CompositePrimaryKey('qualif', 'lot')
    qualif = models.ForeignKey(Qualif, on_delete=models.CASCADE, db_column='qualif')
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, db_column='lot')

    class Meta:
        db_table = 'rel_qualif_lot'
        unique_together = ('qualif', 'lot')


class Sample(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    when = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    lot = models.ForeignKey(Lot, on_delete=models.CASCADE, related_name="samples", db_column='lot', blank=True, null=True)

    class Meta:
        db_table = 'sample'
        ordering = ['-when']
    
    def __str__(self):
        return f"{ self.lot.tender.chrono } - { self.when }"


# class Utilizer(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     username = models.CharField(max_length=64)
#     email = models.CharField(blank=True, null=True)

#     class Meta:
#         db_table = 'utilizer'
#         ordering = ['username']
    
#     def __str__(self):
#         return self.username


class Visit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    when = models.DateTimeField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    lot = models.ForeignKey('Lot', on_delete=models.CASCADE, related_name="visits", db_column='lot', blank=True, null=True)

    class Meta:
        db_table = 'visit'
        ordering = ['-when']
    
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
        db_table = 'file_to_get'
        ordering = ['-closed', 'created']

    def save(self, *args, **kwargs):
        if self.pk is not None:
            self.updated = timezone.now()
        super().save(*args, **kwargs)

