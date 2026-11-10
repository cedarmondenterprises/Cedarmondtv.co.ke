from django.contrib.syndication.views import Feed
from django.contrib.sitemaps import Sitemap
from django.conf import settings
from .models import Article
class LatestFeed(Feed):
    title = 'Cedarmond TV'
    description = 'Kenya, in perspective.'
    def link(self): return settings.SITE_URL
    def items(self): return Article.objects.live()[:30]
    def item_title(self,item): return item.title
    def item_description(self,item): return item.summary
    def item_pubdate(self,item): return item.published_at
    def item_link(self,item): return settings.SITE_URL+item.get_absolute_url()
class ArticleSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.8
    def items(self): return Article.objects.live()
    def lastmod(self,item): return item.updated_at
