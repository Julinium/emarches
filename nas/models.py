
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

from base.models import Agrement, Change, Qualif, Tender
from bdc.models import PurchaseOrder

from .choices import (FirstArticles, FullBarDays, ItemsPerPage, OrderingField,
                      PurchaseOrderFullBarDays, PurchaseOrderOrderingField)
from .iceberg import get_ice_checkup
from .imaging import squarify_image


class Profile(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    active    = models.BooleanField(null=True, default=True, editable=False)
    image     = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('Avatar'))
    phone     = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Phone'))
    whatsapp  = models.CharField(max_length=255, blank=True, default='', verbose_name=_('Whatsapp'))
    about     = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('About'))
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
    
    def save(self, *args, **kwargs):
        if self.image:
            # Process the image before saving
            self.image = squarify_image(self.image, str(self.id).split('-')[0])
        super().save(*args, **kwargs)


class Company(models.Model):
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='companies', editable=False)
    active    = models.BooleanField(null=True, default=True, editable=False)
    name      = models.CharField(max_length=255, default="MODE 777", verbose_name=_('Name'))
    forme     = models.CharField(max_length=255, blank=True, null=True, default='SARL', verbose_name=_('Juridic form'))
    ice       = models.CharField(max_length=64, blank=True, null=True, default='77777777777777', verbose_name="ICE")
    tp        = models.CharField(max_length=64, blank=True, null=True, default='7777777', verbose_name=_('Tax Pro'))
    rc        = models.CharField(max_length=64, blank=True, null=True, default='7777777', verbose_name=_('Num. RC'))
    cnss      = models.CharField(max_length=64, blank=True, null=True, default='7777777', verbose_name=_('CNSS'))
    address   = models.CharField(max_length=512, blank=True, null=True, verbose_name=_('Street Address'))
    city      = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('City'))
    zip_code  = models.CharField(max_length=8, blank=True, null=True, verbose_name=_('ZIP Code'))
    state     = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Region, State'))
    country   = models.CharField(max_length=64, blank=True, null=True, default=_('Morocco'), verbose_name=_('Country'))
    date_est  = models.DateField(blank=True, null=True, verbose_name=_('Date Established'))
    phone     = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Phone'))
    mobile    = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Mobile'))
    email     = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    whatsapp  = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Whatsapp'))
    faximili  = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Fax'))
    website   = models.CharField(max_length=128, blank=True, null=True, default='www.mode-777.com', verbose_name=_('Website'))
    activity  = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Activity'))
    sector    = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Sector'))
    note      = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_('Descritpion'))
    image     = models.ImageField(upload_to='companies/', null=True, blank=True, verbose_name=_('Logo'))
    agrements = models.ManyToManyField(Agrement, blank=True, related_name='companies', verbose_name=_('Agrements'))
    qualifs   = models.ManyToManyField(Qualif, blank=True, related_name='companies', verbose_name=_('Qualifications'))

    created   = models.DateTimeField(auto_now_add=True, editable=False)
    updated   = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'nas_company'
        ordering = ['name']
        verbose_name_plural = _("Companies")
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_company_per_user'
            )
        ]

    def __str__(self):
        return f'{self.name}'
    
    @property
    def logo(self):
        try:
            logo = self.image.url
        except:
            logo = static('companies/default.svg')
        return logo

    @property
    def iceberg(self):
        ice = self.ice
        if not ice: return False
        cj = get_ice_checkup(ice)
        if not cj: return False
        return cj.get('n2') == cj.get('cs')


    @property
    def iced_company(self):
        from nas.iceberg import get_company
        return get_company(self.ice)

    @property
    def verified(self):
        iced_company = self.iced_company
        if len(iced_company) == 0 : return False

        name = iced_company.get('name')
        if name.replace(' ', '').lower() != self.name.replace(' ', '').lower() : return False

        ice = iced_company.get('ice')
        if ice.replace(' ', '').lower() != self.ice.replace(' ', '').lower() : return False

        rc = str(iced_company.get('rc'))
        if rc.replace(' ', '').lower() != self.rc.replace(' ', '').lower() : return False

        return True

    
    def save(self, *args, **kwargs):
        if self.image:
            self.image = squarify_image(self.image, str(self.id).split('-')[0])
        super().save(*args, **kwargs)


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
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, related_name='favorites', verbose_name=_('Company'))
    tender  = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='favorites', editable=False, verbose_name=_('Tender'))
    folders = models.ManyToManyField(Folder, related_name='favorites', verbose_name=_('Folders'))
    active  = models.BooleanField(null=True, default=True, editable=False)
    when    = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date Added'))
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
        verbose_name = "Tender Download"
        # constraints = [models.UniqueConstraint(fields=['tender', 'user'], name='unique_download_per_user')]

    def __str__(self):
        return f"D-{ self.tender.chrono }-BY-{ self.user.username }"


class TenderView(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='views', editable=False)
    tender     = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='views', editable=False, verbose_name=_('Tender'))
    when       = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date'))

    class Meta:
        db_table = 'nas_tender_view'
        ordering = ['-when']

    def __str__(self):
        return f"V-{ self.tender.chrono }-BY-{ self.user.username }"


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
    active      = models.BooleanField(null=True, default=False)
    name        = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Name'))
    rank        = models.SmallIntegerField(default=0, verbose_name=_('Rank'))
    description = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Description'))
    channel     = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email', verbose_name=_('Channel'))
    monthly     = models.SmallIntegerField(blank=True, null=True, default=4, verbose_name=_('Messages per month'))
    # daily       = models.SmallIntegerField(blank=True, null=True, default=1, verbose_name=_('Messages per day'))

    @property
    def frequency(self):
        m = self.monthly
        freq = m
        # unit = _('Message')
        slot = _('Month')
        if m >= 7 and m <= 30:
            slot = _('Week')
            freq = int(7 * m / 30)
        elif m > 30:
            slot = _('Day')
            freq = int(m / 30)

        # return f'~{freq} {unit} / {slot}'
        return f'~{freq} / {slot}'

    class Meta:
        db_table = 'nas_newsletter'
        ordering = ['rank', 'name']
    
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
    active      = models.BooleanField(null=True, default=False)
    rank        = models.SmallIntegerField(default=0, verbose_name=_('Rank'))
    name        = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Name'))
    event       = models.CharField(max_length=256, blank=True, null=True, verbose_name=_('Event'))
    description = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Description'))
    channel     = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='email', verbose_name=_('Channel'))

    class Meta:
        db_table = 'nas_notification'
        ordering = ['rank', 'name']

    def __str__(self):
        return self.name


class NewsletterSubscription(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active     = models.BooleanField(null=True, default=False)
    user       = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='newsletters', editable=False)
    rank       = models.SmallIntegerField(default=0, verbose_name=_('Rank'), editable=False)
    newsletter = models.ForeignKey(Newsletter, on_delete=models.CASCADE, blank=True, null=True, related_name='subscriptions', editable=False)
    when       = models.DateTimeField(blank=True, null=True, auto_now=True, editable=False, verbose_name=_('Last subscribed'))

    class Meta:
        db_table = 'nas_newsletter_subscription'
        ordering = ['rank', '-when']
    
    def __str__(self):
        return f"{ self.user }@{ self.newsletter }"


class NotificationSubscription(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active       = models.BooleanField(null=True, default=True)
    user         = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, related_name='notifications', editable=False)
    rank         = models.SmallIntegerField(default=0, verbose_name=_('Rank'), editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, blank=True, null=True, related_name='notifications', editable=False)
    when         = models.DateTimeField(blank=True, null=True, auto_now=True, editable=False, verbose_name=_('Last subscribed'))

    class Meta:
        db_table = 'nas_notification_subscription'
        ordering = ['rank', '-when']
    
    def __str__(self):
        return f"{ self.user }@{ self.notification }"


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
    change       = models.ForeignKey(Change, on_delete=models.CASCADE, blank=True, null=True, related_name='sent_notifications', editable=False, verbose_name=_('Change'))
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


class Sticky(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stickies', editable=False)
    # company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, related_name='favorites', verbose_name=_('Company'))
    purchase_order  = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='stickies', editable=False, verbose_name=_('Purchase Order'))
    # folders         = models.ManyToManyField(Folder, related_name='favorites', verbose_name=_('Folders'))
    active          = models.BooleanField(null=True, default=True, editable=False)
    when            = models.DateTimeField(blank=True, null=True, auto_now_add=True, editable=False, verbose_name=_('Date Added'))
    comment         = models.TextField(blank=True, null=True, verbose_name=_('Comment'))

    class Meta:
        db_table = 'nas_stickies'
        ordering = ['-when']
    
    def __str__(self):
        return f"{ self.purchase_order.chrono }@{ self.user.username }"


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


class UserSetting(models.Model):

    id                     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    active                 = models.BooleanField(null=True, default=True, editable=False)
    user                   = models.ForeignKey(User, on_delete=models.CASCADE, editable=False, related_name='settings')
    
    tenders_ordering_field = models.CharField(max_length=16, choices=OrderingField.choices, default=OrderingField.DEADLINE_ASC, verbose_name=_('Default sort'))
    tenders_items_per_page = models.CharField(max_length=16, choices=ItemsPerPage.choices, default=ItemsPerPage.IPP_010, verbose_name=_('Items per page'))
    tenders_full_bar_days  = models.CharField(max_length=16, choices=FullBarDays.choices, default=FullBarDays.FBD_030, verbose_name=_('Full progress bar days'))
    tenders_show_expired   = models.BooleanField(default=False, verbose_name=_("Show today's expired items"))
    tenders_show_cancelled = models.BooleanField(default=False, verbose_name=_("Show cancelled tenders"))

    p_orders_ordering_field = models.CharField(max_length=16, choices=PurchaseOrderOrderingField.choices, default=PurchaseOrderOrderingField.DEADLINE_ASC, verbose_name=_('Default sort'))
    p_orders_items_per_page = models.CharField(max_length=16, choices=ItemsPerPage.choices, default=ItemsPerPage.IPP_010, verbose_name=_('Items per page'))
    p_orders_full_bar_days  = models.CharField(max_length=16, choices=PurchaseOrderFullBarDays.choices, default=PurchaseOrderFullBarDays.FBD_015, verbose_name=_('Full progress bar days'))
    p_orders_show_expired   = models.BooleanField(default=True, verbose_name=_("Show today's expired items"))
    p_orders_first_articles = models.CharField(max_length=16, choices=FirstArticles.choices, default=FirstArticles.ATS_005, verbose_name=_('First articles to show'))

    bidding_check_deadline  = models.BooleanField(default=True, verbose_name=_("Check Tender dealine when editing"))
    bidding_check_amount    = models.BooleanField(default=True, verbose_name=_("Check submitted amount when editing"))
    bidding_check_bond      = models.BooleanField(default=True, verbose_name=_("Check submitted bond when editing"))

    general_wrap_long_text = models.BooleanField(default=False, verbose_name=_("Do not wrap long text"))
    general_items_per_page = models.CharField(max_length=16, choices=ItemsPerPage.choices, default=ItemsPerPage.IPP_020, verbose_name=_('List items per page'))
    
    preferred_language     = models.CharField(max_length=16, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE, verbose_name=_("Preferred interface language"))
    updated   = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        db_table = 'nas_user_setting'

    def __str__(self):
        return f'Settings for {self.user.username}'


class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256, blank=True, null=True, verbose_name=_("Name"))
    serial = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Serial Number"))
    issuer = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Issuer"))
    holder = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Holder"))
    owner  = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Owner"))
    issued = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Validity start"))
    expiry = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name=_("Expiry date"))
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="assets", blank=True, null=True, verbose_name=_("Company"))

    class Meta:
        db_table = 'base_asset'
        ordering = ['name']
        verbose_name = _("Asset")
    
    def __str__(self):
        return self.name




