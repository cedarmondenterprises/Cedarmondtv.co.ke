from celery import shared_task
from django.core.cache import cache

@shared_task(name='integrations.tasks.refresh_search')
def refresh_search():
    # Redis lock has an expiry longer than the hard task timeout.
    if not cache.add('integrations:search-sync', True, timeout=300): return 0
    try:
        from .search import refresh_search as sync
        return sync()
    finally:
        cache.delete('integrations:search-sync')
