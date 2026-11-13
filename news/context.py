from django.conf import settings
from django.db.models import Q

from .models import AdPlacement, AdSenseConfiguration, Article, BreakingNewsTicker, Category, Page
from django.utils import timezone


def site(request):
    pages = list(Page.objects.filter(published=True).defer('body'))
    pages_by_slug = {page.slug: page for page in pages}
    current_time = timezone.now()
    active_ads = AdPlacement.objects.filter(active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=current_time),
        Q(ends_at__isnull=True) | Q(ends_at__gt=current_time),
    )
    ads = {item.position: item for item in active_ads}
    breaking_ticker = BreakingNewsTicker.objects.filter(active=True, starts_at__lte=current_time, ends_at__gt=current_time).first()
    adsense_config = AdSenseConfiguration.objects.first()
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
        'adsense_config': adsense_config,
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


def admin_dashboard(request):
    if request.path_info.rstrip('/') != '/admin' or not getattr(getattr(request, 'user', None), 'is_staff', False):
        return {}
    from datetime import timedelta
    from django.db.models import Sum
    from .models import ArticleDailyView, StoryComment

    from .newsroom import visible_articles

    user = request.user
    articles = visible_articles(user) if user.has_perm('news.view_article') else Article.objects.none()
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    weekly_views = ArticleDailyView.objects.filter(viewed_on__gte=week_start, viewed_on__lte=today)
    return {
        'dashboard_drafts': articles.filter(status='draft').count(),
        'dashboard_review': articles.filter(status='review').count(),
        'dashboard_published': articles.filter(status='published', published_at__lte=timezone.now()).count(),
        'dashboard_pending_comments': StoryComment.objects.filter(status=StoryComment.PENDING).count(),
        'dashboard_weekly_views': weekly_views.aggregate(total=Sum('view_count'))['total'] or 0,
        'dashboard_recent_articles': articles.order_by('-updated_at')[:6],
    }
