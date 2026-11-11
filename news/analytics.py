import re

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import ArticleDailyView


def record_article_view(request, article):
    """Store aggregate counts only; never persist an IP, full UA, or fingerprint."""
    if request.method != 'GET' or getattr(request.user, 'is_staff', False):
        return

    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500].lower()
    if any(token in user_agent for token in ('bot', 'crawler', 'spider', 'preview', 'monitor')):
        return

    if 'ipad' in user_agent or 'tablet' in user_agent or ('android' in user_agent and 'mobile' not in user_agent):
        device_type = 'tablet'
    elif any(token in user_agent for token in ('mobile', 'iphone', 'ipod', 'android')):
        device_type = 'mobile'
    elif user_agent:
        device_type = 'desktop'
    else:
        device_type = 'other'

    country_code = request.META.get('HTTP_CF_IPCOUNTRY', '').upper()
    if not re.fullmatch(r'[A-Z]{2}', country_code) or country_code in {'XX', 'T1'}:
        country_code = 'ZZ'

    dimensions = {
        'article': article,
        'viewed_on': timezone.localdate(),
        'country_code': country_code,
        'device_type': device_type,
    }
    with transaction.atomic():
        row, created = ArticleDailyView.objects.get_or_create(**dimensions, defaults={'view_count': 1})
        if not created:
            ArticleDailyView.objects.filter(pk=row.pk).update(view_count=F('view_count') + 1)
