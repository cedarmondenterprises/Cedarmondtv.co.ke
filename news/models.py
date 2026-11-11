import math
import uuid
from django.conf import settings
from django.utils.html import strip_tags
from django_prose_editor.fields import ProseEditorField
from simple_history.models import HistoricalRecords
from .editor import EXTENSIONS, sanitize_html
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

def image_size(value):
    if value.size > 8 * 1024 * 1024:
        raise ValidationError('Images must be 8 MB or smaller.')

class Category(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    position = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['position','name']
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse('category',args=[self.slug])

class Tag(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse('tag',args=[self.slug])

class Author(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    bio = models.TextField(blank=True)
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse('author',args=[self.slug])

class ArticleQuerySet(models.QuerySet):
    def live(self):
        return self.filter(status='published',published_at__lte=timezone.now()).select_related('category','author','media_asset')

class Article(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(unique=True,max_length=240)
    summary = models.TextField(max_length=400)
    body = ProseEditorField(extensions=EXTENSIONS,sanitize=True)
    history = HistoricalRecords()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='articles')
    thumbnail = models.ImageField(upload_to='thumbnails/%Y/%m/',blank=True,editable=False)
    media_asset = models.ForeignKey('MediaAsset',on_delete=models.SET_NULL,null=True,blank=True,related_name='articles')
    deadline = models.DateTimeField(null=True,blank=True,db_index=True)
    assignment_notes = models.TextField(blank=True,max_length=3000,help_text='Private instructions for the reporter; never shown publicly.')
    category = models.ForeignKey(Category,on_delete=models.PROTECT)
    author = models.ForeignKey(Author,on_delete=models.PROTECT)
    tags = models.ManyToManyField(Tag,blank=True)
    image = models.ImageField(upload_to='articles/%Y/%m/',blank=True,validators=[image_size,FileExtensionValidator(['jpg','jpeg','png','webp'])])
    image_alt = models.CharField(max_length=200,blank=True,help_text='Describe what is visible in the photo. Required when an image is attached.')
    image_credit = models.CharField(max_length=200,blank=True)
    status = models.CharField(max_length=12,choices=[('draft','Draft'),('review','In review'),('published','Published')],default='draft')
    published_at = models.DateTimeField(default=timezone.now,db_index=True,help_text='Future dates become visible automatically when reached.')
    updated_at = models.DateTimeField(auto_now=True)
    featured = models.BooleanField(default=False)
    breaking = models.BooleanField(default=False)
    editors_pick = models.BooleanField(default=False)
    seo_title = models.CharField(max_length=70,blank=True)
    seo_description = models.CharField(max_length=160,blank=True)
    objects = ArticleQuerySet.as_manager()
    class Meta:
        ordering = ['-published_at']
        indexes = [models.Index(fields=['status','published_at'])]
        permissions = [('publish_article','Can publish articles')]
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('article',args=[self.slug])
    @property
    def reading_minutes(self): return max(1,math.ceil(len(strip_tags(self.body).split())/220))
    @property
    def rendered_body(self): return sanitize_html(self.body)
    @property
    def display_image(self): return self.image or (self.media_asset.image if self.media_asset_id else None)
    @property
    def display_thumbnail(self): return self.thumbnail if self.image else (self.media_asset.thumbnail if self.media_asset_id else None)
    @property
    def display_alt(self): return self.image_alt if self.image else (self.media_asset.alt_text if self.media_asset_id else '')
    @property
    def display_credit(self): return self.image_credit if self.image else (self.media_asset.credit if self.media_asset_id else '')
    @transaction.atomic
    def save(self,*args,**kwargs):
        # Serialize URL changes and reserve every current/past slug permanently.
        previous = type(self).objects.select_for_update().filter(pk=self.pk).values_list('slug',flat=True).first() if self.pk else None
        self.body = sanitize_html(self.body)
        from .media import optimize_article_image
        optimize_article_image(self)
        super().save(*args,**kwargs)
        for slug in {self.slug, previous} - {None, ''}:
            reservation, _ = ArticleURL.objects.get_or_create(slug=slug,defaults={'article':self})
            if reservation.article_id != self.pk:
                raise ValidationError({'slug':'This address belongs to another story, including its URL history.'})
    def clean(self):
        if ArticleURL.objects.filter(slug=self.slug).exclude(article_id=self.pk).exists():
            raise ValidationError({'slug':'This address is reserved by another story.'})
        if self.image and not self.image_alt:
            raise ValidationError({'image_alt':'Describe the image for readers using assistive technology.'})

class Subscription(models.Model):
    email = models.EmailField(unique=True)
    active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True,blank=True)
    token_version = models.UUIDField(default=uuid.uuid4,editable=False)
    def __str__(self): return self.email

class ReaderMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    def __str__(self): return self.subject

class AdPlacement(models.Model):
    label = models.CharField(max_length=100)
    position = models.CharField(max_length=20,choices=[('header','Header'),('sidebar','Sidebar')],unique=True)
    image = models.ImageField(upload_to='ads/',validators=[image_size,FileExtensionValidator(['jpg','jpeg','png','webp'])])
    destination = models.URLField()
    active = models.BooleanField(default=True)
    def __str__(self): return self.label


class Page(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    body = ProseEditorField(extensions=EXTENSIONS,sanitize=True)
    seo_title = models.CharField(max_length=70,blank=True)
    seo_description = models.CharField(max_length=160,blank=True)
    published = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()
    class Meta: ordering = ['position','title']
    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('page',args=[self.slug])
    @property
    def rendered_body(self): return sanitize_html(self.body)
    def save(self,*args,**kwargs):
        self.body=sanitize_html(self.body)
        super().save(*args,**kwargs)

class Campaign(models.Model):
    subject = models.CharField(max_length=150)
    body = models.TextField(help_text='Plain-text newsletter. A personal unsubscribe link is appended automatically.')
    queued_at = models.DateTimeField(null=True,blank=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: permissions = [('send_campaign','Can send newsletter campaigns')]
    def __str__(self): return self.subject

class CampaignDelivery(models.Model):
    campaign = models.ForeignKey(Campaign,on_delete=models.CASCADE)
    subscriber = models.ForeignKey(Subscription,on_delete=models.CASCADE)
    email = models.ForeignKey('post_office.Email',on_delete=models.SET_NULL,null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['campaign','subscriber'],name='one_campaign_per_subscriber')]


class ArticleURL(models.Model):
    slug = models.SlugField(unique=True,max_length=240)
    article = models.ForeignKey(Article,on_delete=models.CASCADE,related_name='url_history')
    def __str__(self): return self.slug

class MediaAsset(models.Model):
    title = models.CharField(max_length=180)
    image = models.ImageField(upload_to='library/%Y/%m/',validators=[image_size,FileExtensionValidator(['jpg','jpeg','png','webp'])])
    thumbnail = models.ImageField(upload_to='library/thumbnails/%Y/%m/',blank=True,editable=False)
    alt_text = models.CharField(max_length=200)
    credit = models.CharField(max_length=200)
    rights = models.CharField(max_length=300,help_text='Record ownership, licence or permission to publish.')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title
    def save(self,*args,**kwargs):
        from .media import optimize_article_image
        optimize_article_image(self)
        super().save(*args,**kwargs)

class EditorialComment(models.Model):
    article = models.ForeignKey(Article,on_delete=models.CASCADE,related_name='editorial_comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True,blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='+')
    class Meta: ordering=['created_at','pk']

class DraftRecovery(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    article = models.ForeignKey(Article,on_delete=models.CASCADE,null=True,blank=True)
    data = models.JSONField(default=dict)
    version = models.PositiveIntegerField(default=0)
    base_updated_at = models.CharField(max_length=60,blank=True)
    saved_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-saved_at']

class StoryComment(models.Model):
    PENDING='pending'
    APPROVED='approved'
    REJECTED='rejected'
    STATUS_CHOICES=[(PENDING,'Awaiting moderation'),(APPROVED,'Approved'),(REJECTED,'Rejected')]
    article=models.ForeignKey(Article,on_delete=models.CASCADE,related_name='reader_comments')
    display_name=models.CharField(max_length=80)
    body=models.TextField(max_length=2000)
    status=models.CharField(max_length=10,choices=STATUS_CHOICES,default=PENDING,db_index=True)
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    moderated_at=models.DateTimeField(null=True,blank=True)
    moderated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    class Meta:
        ordering=['-created_at','-pk']
        indexes=[models.Index(fields=['article','status','-created_at'])]
    def __str__(self): return f'{self.display_name} on {self.article}'
