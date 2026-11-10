from django.conf import settings
from .models import Category, Article, AdPlacement
def site(request):
    return {'categories':Category.objects.all(),'breaking_story':Article.objects.live().filter(breaking=True).first(),'site_url':settings.SITE_URL,'header_ad':AdPlacement.objects.filter(position='header',active=True).first(),'sidebar_ad':AdPlacement.objects.filter(position='sidebar',active=True).first()}
