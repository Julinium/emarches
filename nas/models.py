
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

from base.models import Agrement, Tender, Qualif


class Profile(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    active    = models.BooleanField(null=True, default=True, editable=False)
    image     = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('Avatar'))
    phone     = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Telephone'))
    whatsapp  = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Whatsapp'))
    about     = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('A Propos'))
    onboarded = models.BooleanField(null=True, default=False, editable=False)
    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False)

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
    email     = models.EmailField(blank=True, verbose_name=_('Email'))
    whatsapp  = models.CharField(max_length=255, blank=True, verbose_name=_('Whatsapp'))
    faximili  = models.CharField(max_length=255, blank=True, verbose_name=_('Fax'))
    website   = models.CharField(max_length=128, blank=True, verbose_name=_('Website'))
    activity  = models.CharField(max_length=128, blank=True, verbose_name=_('Activity'))
    sector    = models.CharField(max_length=128, blank=True, verbose_name=_('Sector'))
    note      = models.CharField(max_length=1024, blank=True, verbose_name=_('Descritpion'))
    image     = models.ImageField(upload_to='companies/', null=True, blank=True, verbose_name=_('Image'))
    agrements = models.ManyToManyField(Agrement, related_name='companies', verbose_name=_('Agrements'))
    qualifs   = models.ManyToManyField(Qualif, related_name='companies', verbose_name=_('Qualifications'))

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


class Folder(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='folders', editable=False)
    name    = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Name'))
    image   = models.ImageField(upload_to='folders/', null=True, blank=True, verbose_name=_('Image'))
    color   = models.CharField(max_length=8, blank=True, null=True, default='#fd7e14', verbose_name=_('Color'))
    comment = models.TextField(blank=True, null=True, verbose_name=_('Comment'))

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


class Favorite(models.Model):
    id      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites', editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='favorites', verbose_name=_('Company'))
    tender  = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='favorites', editable=False, verbose_name=_('Tender'))
    folders = models.ManyToManyField(Folder, related_name='favorites', verbose_name=_('Folders'))
    active  = models.BooleanField(null=True, default=True, editable=False)
    when    = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date Added'))
    tags    = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Tags'))
    comment = models.TextField(blank=True, null=True, verbose_name=_('Comment'))

    class Meta:
        db_table = 'nas_favorite'
        ordering = ['-when']
    
    def __str__(self):
        return f"{ self.tender.chrono }@{ self.user.username }"


class Download(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads', editable=False)
    tender     = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='downloads', editable=False, verbose_name=_('Tender'))
    when       = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date Started'))
    size_read  = models.CharField(max_length=128, blank=True, null=True, editable=False, verbose_name=_('Displayed Size'))
    size_bytes = models.BigIntegerField(blank=True, null=True, editable=False, verbose_name=_('Size in Bytes'))

    class Meta:
        db_table = 'nas_tender_download'
        ordering = ['-when']

    def __str__(self):
        return f"{ self.tender.chrono }@{ self.user.username }"


class Letter(models.Model):
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user     = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='letters', editable=False)
    when     = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date sent'))
    ua       = models.CharField(max_length=512, blank=True, null=True, editable=False, verbose_name=_('User Agent'))
    ip       = models.CharField(max_length=64, blank=True, null=True, editable=False, verbose_name=_('IP Address'))
    email    = models.EmailField(blank=True, null=True, editable=False, verbose_name=_('Email'))
    phone    = models.CharField(max_length=64, blank=True, null=True, editable=False, verbose_name=_('Phone'))
    title    = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Object'))
    message  = models.TextField(blank=True, null=True, editable=False, verbose_name=_('Your Message'))
    method   = models.CharField(max_length=8, blank=True, null=True, editable=False, verbose_name=_('Contact Method'))
    response = models.TextField(blank=True, null=True, editable=False, verbose_name=_('Response'))
    comment  = models.TextField(blank=True, null=True, verbose_name=_('Comment'))
    actions  = models.TextField(blank=True, null=True, verbose_name=_('Actions'))
    solved   = models.BooleanField(blank=True, null=True, default=False, verbose_name=_('Solved'))

    class Meta:
        db_table = 'nas_letter'
        ordering = ['solved', '-when']
    
    def __str__(self):
        return self.title


class Newsletter(models.Model):
    CHANNEL_CHOICES = [
        ('email', _('Email')),
        ('phone', _('Phone')),
        ('sms', _('SMS')),
        ('whatsapp', _('Whatsapp')),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active      = models.BooleanField(null=True, default=True)
    name        = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Name'))
    description = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Description'))
    channel     = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email', verbose_name=_('Channel'))
    monthly     = models.SmallIntegerField(blank=True, null=True, default=4, verbose_name=_('Messages per month'))

    @property
    def frequency(self):
        m = self.monthly
        freq = m
        unit = _('Message')
        slot = _('Month')
        if m >= 7 and m <= 30:
            slot = _('Week')
            freq = int(7 * m / 30)
        elif m > 30:
            slot = _('Day')
            freq = int(m / 30)

        return f'~{freq} {unit} / {slot}'

    class Meta:
        db_table = 'nas_newsletter'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Notification(models.Model):
    CHANNEL_CHOICES = [
        ('email', _('Email')),
        ('phone', _('Phone')),
        ('sms', _('SMS')),
        ('whatsapp', _('Whatsapp')),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active      = models.BooleanField(null=True, default=True)
    name        = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Name'))
    event       = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Event'))
    description = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Description'))
    channel     = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email', verbose_name=_('Channel'))

    class Meta:
        db_table = 'nas_notification'
        ordering = ['name']

    def __str__(self):
        return self.name


class NewsletterSubscription(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active     = models.BooleanField(null=True, default=True)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='newsletters', editable=False)
    newsletter = models.ForeignKey(Newsletter, on_delete=models.CASCADE, blank=True, null=True, related_name='subscriptions', editable=False)
    when       = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Last subscribed'))

    class Meta:
        db_table = 'nas_newsletter_subscription'
        ordering = ['-when']


class NotificationSubscription(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active       = models.BooleanField(null=True, default=True)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='notifications', editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, blank=True, null=True, related_name='notifications', editable=False)
    when         = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Last subscribed'))

    class Meta:
        db_table = 'nas_notification_subscription'
        ordering = ['-when']


class LetterSent(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='sent_letters', editable=False, verbose_name=_('User'))
    newsletter   = models.ForeignKey(Newsletter, on_delete=models.CASCADE, blank=True, null=True, related_name='sent_letters', editable=False, verbose_name=_('Newsletter'))
    when         = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date sent'))
    sender       = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Sender'))
    destination  = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Destination'))
    title        = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Object'))
    message      = models.TextField(blank=True, null=True, editable=False, verbose_name=_('Message'))
    retries      = models.SmallIntegerField(default=0, verbose_name=_('Retries'))
    max_retries  = models.SmallIntegerField(default=5, verbose_name=_('Max retries'))
    success      = models.BooleanField(null=True, default=False, verbose_name=_('Success'))

    class Meta:
        db_table = 'nas_letter_sent'
        ordering = ['success', '-when']

    def __str__(self):
        return f'{self.title}_{self.user}_{self.when}'


class NotificationSent(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='sent_notifications', editable=False, verbose_name=_('User'))
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, blank=True, null=True, related_name='sent_notifications', editable=False, verbose_name=_('Notification'))
    when         = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date sent'))
    sender       = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Sender'))
    destination  = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Destination'))
    title        = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Object'))
    message      = models.TextField(blank=True, null=True, editable=False, verbose_name=_('Message'))
    retries      = models.SmallIntegerField(default=0, verbose_name=_('Retries'))
    max_retries  = models.SmallIntegerField(default=5, verbose_name=_('Max retries'))
    success      = models.BooleanField(null=True, default=False, verbose_name=_('Success'))

    class Meta:
        db_table = 'nas_notification_sent'
        ordering = ['success', '-when']

    def __str__(self):
        return f'{self.title}_{self.user}_{self.when}'

    

class Comment(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', editable=False, verbose_name=_('User'))
    tender     = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='comments', editable=False, verbose_name=_('Tender'))
    when       = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date'))
    title      = models.CharField(max_length=256, blank=True, null=True, editable=False, verbose_name=_('Title'))
    content    = models.TextField(blank=True, null=True, editable=False, verbose_name=_('Content'))

    class Meta:
        db_table = 'nas_comment'
        ordering = ['-when']

    @property
    def likes(self):
        return self.reactions.filter(reaction='like').count()

    @property
    def dislikes(self):
        return self.reactions.filter(reaction='dislike').count()

    @property
    def score(self):
        return self.likes - self.dislikes

    def __str__(self):
        return f"{ self.user.username }-on-{ self.tender.chrono }"



class Reaction(models.Model):
    LIKE_CHOICES = [
        ('like', _('Like')),
        ('dislike', _('Dislike')),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reactions', editable=False, verbose_name=_('User'))
    comment    = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions', editable=False, verbose_name=_('Comment'))
    when       = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date'))
    reaction   = models.CharField(max_length=10, choices=LIKE_CHOICES, default='like', verbose_name=_('Reaction'))

    class Meta:
        db_table = 'nas_reaction'
        ordering = ['-when']

    def __str__(self):
        return f"{ self.user.username }-{ self.reaction }-{ self.comment }"
