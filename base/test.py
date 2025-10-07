
# class Domain(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=2048, blank=True, null=True)

#     class Meta:
#         db_table = 'domain'
#         ordering = ['name']


# class Tender(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     chrono = models.CharField(max_length=16, blank=True, null=True)
#     title = models.TextField(blank=True, null=True)
#     estimate = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, default=0)
#     location = models.CharField(max_length=1024, blank=True, null=True)
#     created = models.DateTimeField(blank=True, null=True, auto_now_add=True)
#     updated = models.DateTimeField(blank=True, null=True)
#     link = models.CharField(max_length=256, blank=True, null=True)
#     acronym = models.CharField(max_length=8, blank=True, null=True)

#     category = models.ForeignKey(Category, on_delete=models.DO_NOTHING, related_name="tenders", db_column='category', blank=True, null=True)
#     mode = models.ForeignKey(Mode, on_delete=models.DO_NOTHING, related_name='tenders', db_column='mode', blank=True, null=True)
#     procedure = models.ForeignKey(Procedure, on_delete=models.DO_NOTHING, related_name='tenders', db_column='procedure', blank=True, null=True)
#     client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, related_name='tenders', db_column='client', blank=True, null=True)
#     kind = models.ForeignKey(Kind, on_delete=models.DO_NOTHING, related_name='tenders', db_column='kind', blank=True, null=True)
#     domains = models.ManyToManyField(Domain, through='RelDomainTender', related_name='tenders')

#     class Meta:
#         db_table = 'tender'


# class RelDomainTender(models.Model):
#     pk = models.CompositePrimaryKey('domain', 'tender')
#     tender = models.ForeignKey('Tender', on_delete=models.CASCADE, db_column='tender')
#     domain = models.ForeignKey('Domain', on_delete=models.CASCADE, db_column='domain')

#     class Meta:
#         db_table = 'rel_domain_tender'
#         unique_together = ('domain', 'tender')
