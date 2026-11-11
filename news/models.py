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
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator, RegexValidator
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
    homepage_rank = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(99)], help_text='Higher numbers appear earlier among homepage stories. Leave at 0 to use the normal publication order.')
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


class LiveBlog(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_LIVE = 'live'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [(STATUS_DRAFT,'Draft'),(STATUS_LIVE,'Live'),(STATUS_CLOSED,'Closed')]

    title = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240,unique=True)
    summary = models.TextField(max_length=400)
    category = models.ForeignKey(Category,on_delete=models.PROTECT,related_name='live_blogs')
    author = models.ForeignKey(Author,on_delete=models.PROTECT,related_name='live_blogs')
    cover_asset = models.ForeignKey('MediaAsset',on_delete=models.SET_NULL,null=True,blank=True,related_name='live_blogs')
    status = models.CharField(max_length=10,choices=STATUS_CHOICES,default=STATUS_DRAFT,db_index=True)
    published_at = models.DateTimeField(null=True,blank=True,db_index=True)
    started_at = models.DateTimeField(null=True,blank=True)
    closed_at = models.DateTimeField(null=True,blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at','-pk']
        indexes = [models.Index(fields=['status','published_at'])]
        verbose_name = 'live coverage'
        verbose_name_plural = 'live coverage'

    def __str__(self): return self.title
    def get_absolute_url(self): return reverse('live_blog',args=[self.slug])
    @property
    def display_image(self): return self.cover_asset.image if self.cover_asset_id else None
    @property
    def display_alt(self): return self.cover_asset.alt_text if self.cover_asset_id else ''
    @property
    def is_open(self): return self.status == self.STATUS_LIVE

    def clean(self):
        super().clean()
        if self.closed_at and self.started_at and self.closed_at < self.started_at:
            raise ValidationError({'closed_at':'The close time cannot be earlier than the start time.'})

    def save(self,*args,**kwargs):
        if self.status in {self.STATUS_LIVE,self.STATUS_CLOSED} and not self.published_at:
            self.published_at=timezone.now()
        if self.status == self.STATUS_LIVE:
            if not self.started_at: self.started_at=timezone.now()
            self.closed_at=None
        elif self.status == self.STATUS_CLOSED and not self.closed_at:
            self.closed_at=timezone.now()
        super().save(*args,**kwargs)


class LiveBlogUpdate(models.Model):
    live_blog = models.ForeignKey(LiveBlog,on_delete=models.CASCADE,related_name='updates')
    content = ProseEditorField(extensions=EXTENSIONS,sanitize=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='live_blog_updates')
    published = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True,db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned','-created_at','-pk']
        indexes = [models.Index(fields=['live_blog','published','created_at'])]
        verbose_name = 'live coverage update'
        verbose_name_plural = 'live coverage updates'

    def __str__(self): return f'{self.live_blog}: {self.created_at:%Y-%m-%d %H:%M}'

    @property
    def rendered_content(self): return sanitize_html(self.content)

    def save(self,*args,**kwargs):
        self.content=sanitize_html(self.content)
        super().save(*args,**kwargs)


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


class AdSenseConfiguration(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    active = models.BooleanField(default=False, help_text='Leave off until the site is approved by AdSense and the privacy notice and required consent choices are in place.')
    publisher_id = models.CharField(max_length=23, blank=True, validators=[RegexValidator(r'^ca-pub-\d{16}$', 'Enter a Google publisher ID in the form ca-pub-1234567890123456.')], help_text='Publisher ID only. Never paste script or HTML here.')
    header_slot_id = models.CharField(max_length=20, blank=True, validators=[RegexValidator(r'^\d{6,20}$', 'Enter the numeric ad unit ID from AdSense.')])
    article_slot_id = models.CharField(max_length=20, blank=True, validators=[RegexValidator(r'^\d{6,20}$', 'Enter the numeric ad unit ID from AdSense.')])
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AdSense configuration'
        verbose_name_plural = 'AdSense configuration'

    def __str__(self): return 'Google AdSense settings'

    def clean(self):
        super().clean()
        if self.pk != 1:
            raise ValidationError('Only the single site-wide AdSense configuration is allowed.')
        if self.active and (not self.publisher_id or not (self.header_slot_id or self.article_slot_id)):
            raise ValidationError('To enable AdSense, provide a publisher ID and at least one ad unit ID.')

    def save(self,*args,**kwargs):
        self.pk = 1
        super().save(*args,**kwargs)


class BreakingNewsTicker(models.Model):
    message = models.CharField(max_length=240, help_text='Short, verified text shown in the scrolling breaking-news strip.')
    link = models.URLField(blank=True, help_text='Optional destination, such as the full article URL.')
    active = models.BooleanField(default=True, help_text='Turn off to hide this message without deleting it.')
    starts_at = models.DateTimeField(default=timezone.now, help_text='The message becomes visible at this time (Nairobi time in the admin).')
    ends_at = models.DateTimeField(help_text='The message stops appearing at this time (Nairobi time in the admin).')
    scroll_seconds = models.PositiveSmallIntegerField(default=32, validators=[MinValueValidator(10), MaxValueValidator(90)], help_text='Seconds for one pass across the screen. Choose 10–90 seconds.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-starts_at', '-pk']
        indexes = [models.Index(fields=['active', 'starts_at', 'ends_at'])]
        verbose_name = 'breaking-news ticker message'
        verbose_name_plural = 'breaking-news ticker messages'

    def __str__(self): return self.message

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'End time must be later than start time.'})


class ArticleDailyView(models.Model):
    DEVICE_TYPES = [('mobile','Mobile'),('tablet','Tablet'),('desktop','Desktop'),('other','Other')]
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='daily_views')
    viewed_on = models.DateField(db_index=True)
    country_code = models.CharField(max_length=2, default='ZZ', help_text='ISO country code from the trusted edge, or ZZ when unavailable.')
    device_type = models.CharField(max_length=10, choices=DEVICE_TYPES, default='other')
    view_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-viewed_on','-view_count']
        constraints = [models.UniqueConstraint(fields=['article','viewed_on','country_code','device_type'], name='unique_daily_article_view_dimension')]
        indexes = [models.Index(fields=['viewed_on','country_code']), models.Index(fields=['viewed_on','device_type'])]
        verbose_name = 'article analytics'
        verbose_name_plural = 'article analytics'

    def __str__(self): return f'{self.article} · {self.viewed_on} · {self.view_count} views'


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
