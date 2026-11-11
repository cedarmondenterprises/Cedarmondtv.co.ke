from django.conf import settings
from .models import Category, Article, AdPlacement, Page

def site(request):
    pages=list(Page.objects.filter(published=True).defer('body'))
    ads={item.position:item for item in AdPlacement.objects.filter(active=True)}
    return {'categories':Category.objects.all(),'breaking_story':Article.objects.live().filter(breaking=True).first(),'site_url':settings.SITE_URL,'header_ad':ads.get('header'),'sidebar_ad':ads.get('sidebar'),'newsletter_enabled':settings.NEWSLETTER_ENABLED,'footer_pages':pages,'privacy_page':next((p for p in pages if p.slug=='privacy'),None),'about_page':next((p for p in pages if p.slug=='about'),None)}
