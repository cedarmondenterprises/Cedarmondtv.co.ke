from django.conf import settings

from .models import AdPlacement, Article, BreakingNewsTicker, Category, Page
from django.utils import timezone


def site(request):
    pages = list(Page.objects.filter(published=True).defer('body'))
    pages_by_slug = {page.slug: page for page in pages}
    ads = {item.position: item for item in AdPlacement.objects.filter(active=True)}
    current_time = timezone.now()
    breaking_ticker = BreakingNewsTicker.objects.filter(active=True, starts_at__lte=current_time, ends_at__gt=current_time).first()
    return {
        'categories': Category.objects.all(),
        'breaking_story': Article.objects.live().filter(breaking=True).first(),
        'breaking_ticker': breaking_ticker,
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
        'editorial_page': pages_by_slug.get('editorial-standards'),
        'corrections_page': pages_by_slug.get('corrections'),
        'advertising_page': pages_by_slug.get('advertising'),
        'cookies_page': pages_by_slug.get('cookies'),
        'terms_page': pages_by_slug.get('terms'),
    }
