import math
import uuid
from django.conf import settings
from django.utils.html import strip_tags
from django_prose_editor.fields import ProseEditorField
from simple_history.models import HistoricalRecords
from .editor import EXTENSIONS, sanitize_html
from django.db import models
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

class Author(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    bio = models.TextField(blank=True)
    def __str__(self): return self.name
    def get_absolute_url(self): return reverse('author',args=[self.slug])

class ArticleQuerySet(models.QuerySet):
    def live(self):
        return self.filter(status='published',published_at__lte=timezone.now()).select_related('category','author')

class Article(models.Model):
    title = models.CharField(max_length=220)
    slug = models.SlugField(unique=True,max_length=240)
    summary = models.TextField(max_length=400)
    body = ProseEditorField(extensions=EXTENSIONS,sanitize=True)
    history = HistoricalRecords()
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='articles')
    thumbnail = models.ImageField(upload_to='thumbnails/%Y/%m/',blank=True,editable=False)
    category = models.ForeignKey(Category,on_delete=models.PROTECT)
    author = models.ForeignKey(Author,on_delete=models.PROTECT)
    tags = models.ManyToManyField(Tag,blank=True)
    image = models.ImageField(upload_to='articles/%Y/%m/',blank=True,validators=[image_size,FileExtensionValidator(['jpg','jpeg','png','webp'])])
    image_alt = models.CharField(max_length=200,blank=True)
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
    def save(self,*args,**kwargs):
        self.body = sanitize_html(self.body)
        from .media import optimize_article_image
        optimize_article_image(self)
        super().save(*args,**kwargs)
    def clean(self):
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
