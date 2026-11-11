from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.contrib.syndication.views import Feed
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from urllib.parse import urlsplit

from .models import Article, Author, Category, LiveBlog, Page, Tag


class LatestFeed(Feed):
    title = 'Cedarmond TV'
    description = 'Independent journalism and context from Kenya.'

    def link(self):
        return settings.SITE_URL

    def items(self):
        return Article.objects.live()[:30]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_pubdate(self, item):
        return item.published_at

    def item_link(self, item):
        return settings.SITE_URL + item.get_absolute_url()


class CanonicalSitemap(Sitemap):
    def get_domain(self, site=None):
        return urlsplit(settings.SITE_URL).netloc

    def get_protocol(self, protocol=None):
        return urlsplit(settings.SITE_URL).scheme


class StaticSitemap(CanonicalSitemap):
    changefreq = 'daily'
    priority = 1.0

    def items(self):
        return ['home', 'latest']

    def location(self, item):
        return reverse(item)


class ArticleSitemap(CanonicalSitemap):
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Article.objects.live()

    def lastmod(self, item):
        return item.updated_at


class LiveBlogSitemap(CanonicalSitemap):
    changefreq = 'hourly'
    priority = 0.7

    def items(self):
        return LiveBlog.objects.filter(status__in=[LiveBlog.STATUS_LIVE, LiveBlog.STATUS_CLOSED], published_at__lte=timezone.now())

    def lastmod(self, item):
        return item.updated_at


def _has_live_article():
    return Q(article__status='published', article__published_at__lte=timezone.now())


class CategorySitemap(CanonicalSitemap):
    changefreq = 'daily'
    priority = 0.6

    def items(self):
        return Category.objects.filter(_has_live_article()).distinct().order_by('slug')


class AuthorSitemap(CanonicalSitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return Author.objects.filter(_has_live_article()).distinct().order_by('slug')


class TagSitemap(CanonicalSitemap):
    changefreq = 'weekly'
    priority = 0.4

    def items(self):
        return Tag.objects.filter(_has_live_article()).distinct().order_by('slug')


class PageSitemap(CanonicalSitemap):
    changefreq = 'monthly'
    priority = 0.3

    def items(self):
        return Page.objects.filter(published=True).order_by('position', 'slug')

    def lastmod(self, item):
        return item.updated_at
