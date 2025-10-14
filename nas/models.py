
from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static

from base.models import Agrement, Tender, Qualif


class Profile(models.Model):
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user     = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    active   = models.BooleanField(null=True, default=True, editable=False)
    image    = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('Avatar'))
    phone    = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Telephone'))
    whatsapp = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Whatsapp'))
    about    = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('A Propos'))
    onborded = models.BooleanField(null=True, default=False, editable=False)
    created  = models.DateTimeField(auto_now_add=True, editable=False)
    updated  = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'nas_profile'

    def __str__(self):
        return f'{self.user.username}'
    
    @property
    def avatar(self):
        try:
            avatar = self.image.url
        except:
            avatar = static('avatars/default.png')
        return avatar

    @property
    def companies(self):
        return self.user.companies


class Company(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies', editable=False)
    active    = models.BooleanField(null=True, default=True, editable=False)
    name      = models.CharField(max_length=255, blank=True, verbose_name=_('Name'))
    forme     = models.CharField(max_length=255, blank=True, default='SARL', verbose_name=_('Juridic form'))
    ice       = models.CharField(max_length=64, blank=True, default='77777777777777', verbose_name="ICE")
    tp        = models.CharField(max_length=64, blank=True, default='7777777', verbose_name=_('Tax Pro'))
    rc        = models.CharField(max_length=64, blank=True, default='7777777', verbose_name=_('Num. RC'))
    cnss      = models.CharField(max_length=64, blank=True, default='7777777', verbose_name=_('CNSS'))
    date_est  = models.DateField(blank=True, null=True, verbose_name=_('Date Established'))
    address   = models.CharField(max_length=512, blank=True, verbose_name=_('Street Address'))
    city      = models.CharField(max_length=64, blank=True, verbose_name=_('City'))
    zip_code  = models.CharField(max_length=8, blank=True, verbose_name=_('ZIP Code'))
    state     = models.CharField(max_length=64, blank=True, verbose_name=_('Region, State'))
    country   = models.CharField(max_length=64, blank=True, default=_('Morocco'), verbose_name=_('Country'))
    phone     = models.CharField(max_length=255, blank=True, verbose_name=_('Phone'))
    email     = models.CharField(max_length=255, blank=True, verbose_name=_('Email'))
    whatsapp  = models.CharField(max_length=255, blank=True, verbose_name=_('Whatsapp'))
    faximili  = models.CharField(max_length=255, blank=True, verbose_name=_('Fax'))
    website   = models.CharField(max_length=128, blank=True, verbose_name=_('Website'))
    activity  = models.CharField(max_length=128, blank=True, verbose_name=_('Activity'))
    sector    = models.CharField(max_length=128, blank=True, verbose_name=_('Sector'))
    note      = models.CharField(max_length=1024, blank=True, verbose_name=_('Descritpion'))
    image     = models.ImageField(upload_to='companies/', null=True, blank=True, verbose_name=_('Image'))
    agrements = models.ManyToManyField(Agrement, on_delete=models.DO_NOTHING, related_name='companies', verbose_name=_('Agrements'))
    qualifs   = models.ManyToManyField(Qualif, on_delete=models.DO_NOTHING, related_name='companies', verbose_name=_('Qualifications'))

    created  = models.DateTimeField(auto_now_add=True, editable=False)
    updated  = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'nas_company'
        ordering = ['name']

    def __str__(self):
        return f'{self.name}'
    
    @property
    def logo(self):
        try:
            logo = self.image.url
        except:
            logo = static('companies/default.png')
        return logo


class Favorite(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='favorites')
    tender  = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='favorites')
    folders = models.ManyToManyField(Folder, on_delete=models.DO_NOTHING, related_name='favorites')
    active  = models.BooleanField(null=True, default=True)
    when    = models.DateTimeField(blank=True, null=True)
    tags    = models.CharField(max_length=128, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'nas_favorite'
        ordering = ['-when']
    
    def __str__(self):
        return f"{ self.tender.chrono }@{ self.user.username }"

class Folder(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders')
    name    = models.CharField(max_length=64, blank=True, null=True)
    image   = models.ImageField(upload_to='folders/', null=True, blank=True)
    color   = models.CharField(max_length=8, blank=True, null=True, default='#fd7e14')
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'nas_folder'
        ordering = ['name']
    
    def __str__(self):
        return self.name

    @property
    def icon(self):
        try:
            icon = self.image.url
        except:
            icon = static('folders/default.png')
        return icon


class Download(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    tender     = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='downloads')
    when       = models.DateTimeField(blank=True, null=True)
    size_read  = models.CharField(max_length=128, blank=True, null=True)
    size_bytes = models.BigIntegerField(blank=True, null=True)

    class Meta:
        db_table = 'nas_tender_download'
        ordering = ['-when']

    def __str__(self):
        return f"{ self.tender.chrono }@{ self.user.username }"


class Letter(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user    = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='letters')
    when    = models.DateTimeField(blank=True, null=True)
    ua      = models.CharField(max_length=512, blank=True, null=True)
    ip      = models.CharField(max_length=64, blank=True, null=True)
    email   = models.CharField(max_length=128, blank=True, null=True)
    phone   = models.CharField(max_length=64, blank=True, null=True)
    title   = models.CharField(max_length=256, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    method  = models.CharField(max_length=8, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    actions = models.TextField(blank=True, null=True)
    solved  = models.BooleanField(blank=True, null=True, default=False)

    class Meta:
        db_table = 'nas_letter'
        ordering = ['solved', '-when']
    
    def __str__(self):
        return self.title