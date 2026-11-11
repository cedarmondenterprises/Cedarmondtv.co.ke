from django.conf import settings

from .models import AdPlacement, Article, Category, Page


def site(request):
    pages = list(Page.objects.filter(published=True).defer('body'))
    ads = {item.position: item for item in AdPlacement.objects.filter(active=True)}
    return {
        'categories': Category.objects.all(),
        'breaking_story': Article.objects.live().filter(breaking=True).first(),
        'site_url': settings.SITE_URL,
        'canonical': settings.SITE_URL + request.path,
        'seo_title': 'Cedarmond TV | Kenya, in perspective.',
        'seo_description': 'Independent journalism and original reporting from Kenya, covering politics, business, counties, culture and sport.',
        'seo_image': settings.SITE_URL + settings.STATIC_URL + 'cedarmond-mark.svg',
        'seo_image_alt': 'Cedarmond TV',
        'noindex': False,
        'header_ad': ads.get('header'),
        'sidebar_ad': ads.get('sidebar'),
        'newsletter_enabled': settings.NEWSLETTER_ENABLED,
        'footer_pages': pages,
        'privacy_page': next((page for page in pages if page.slug == 'privacy'), None),
        'about_page': next((page for page in pages if page.slug == 'about'), None),
    }
