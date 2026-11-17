"""Optional integrations. Credentials are environment-only; defaults make no external calls."""
import os
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured

def flag(name): return os.getenv(name, '0') == '1'
def https_url(name):
    value = os.getenv(name, '').strip().rstrip('/')
    if value and (urlsplit(value).scheme != 'https' or not urlsplit(value).hostname or urlsplit(value).username or urlsplit(value).password):
        raise ImproperlyConfigured(f'{name} must be an HTTPS URL without embedded credentials.')
    return value

UNFOLD = {
    'SITE_TITLE': 'Cedarmond TV', 'SITE_HEADER': 'Newsroom', 'THEME': 'light',
    'SITE_SUBHEADER': 'Publishing and operations',
    'COLORS': {'primary': {str(k): v for k,v in {
        50:'255 241 242',100:'255 228 230',200:'254 205 211',300:'253 164 175',
        400:'251 113 133',500:'244 63 94',600:'225 29 72',700:'190 18 60',
        800:'159 18 57',900:'136 19 55',950:'76 5 25'}.items()}},
}
MEILISEARCH_URL = os.getenv('MEILISEARCH_URL', '').rstrip('/')
MEILISEARCH_KEY = os.getenv('MEILISEARCH_KEY', '')
MEILISEARCH_INDEX = 'cedarmond_articles'
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://redis:6379/0'))
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_TIME_LIMIT = 240
CELERY_TASK_SOFT_TIME_LIMIT = 210
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'refresh-public-search': {'task':'integrations.tasks.refresh_search', 'schedule':300.0},
}
ANONYMOUS_USER_NAME = None
AUDITLOG_DISABLE_REMOTE_ADDR = True
AUDITLOG_STORE_JSON_CHANGES = True
UMAMI_SCRIPT_URL = https_url('UMAMI_SCRIPT_URL')
UMAMI_WEBSITE_ID = os.getenv('UMAMI_WEBSITE_ID', '')
LISTMONK_URL = https_url('LISTMONK_URL')
LISTMONK_USERNAME = os.getenv('LISTMONK_USERNAME', '')
LISTMONK_TOKEN = os.getenv('LISTMONK_TOKEN', '')
WEBPUSH_ENABLED = flag('WEBPUSH_ENABLED')
VAPID_PUBLIC_KEY = os.getenv('VAPID_PUBLIC_KEY', '')
VAPID_PRIVATE_KEY = os.getenv('VAPID_PRIVATE_KEY', '')
VAPID_CONTACT = os.getenv('VAPID_CONTACT', '')
if WEBPUSH_ENABLED and not all((VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CONTACT)):
    raise ImproperlyConfigured('Web push requires all VAPID settings.')
# Browser subscription URLs are checked against exact trusted push hosts to prevent SSRF.
WEBPUSH_ALLOWED_HOSTS = ('fcm.googleapis.com', 'updates.push.services.mozilla.com', 'web.push.apple.com')
ANYMAIL = {
    'MAILGUN_API_KEY': os.getenv('MAILGUN_API_KEY', ''),
    'MAILGUN_SENDER_DOMAIN': os.getenv('MAILGUN_SENDER_DOMAIN', ''),
    'WEBHOOK_SECRET': os.getenv('ANYMAIL_WEBHOOK_SECRET', ''),
}
INTEGRATION_LINKS = {name: https_url(name) for name in (
    'UMAMI_DASHBOARD_URL', 'GLITCHTIP_DASHBOARD_URL', 'UPTIME_KUMA_URL', 'LISTMONK_URL')}
MEDIA_S3_ENABLED = flag('MEDIA_S3_ENABLED')
MEDIA_S3_OPTIONS = {
    'bucket_name': os.getenv('MEDIA_S3_BUCKET', ''),
    'endpoint_url': https_url('MEDIA_S3_ENDPOINT_URL') or None,
    'region_name': os.getenv('MEDIA_S3_REGION', 'auto'),
    'access_key': os.getenv('MEDIA_S3_ACCESS_KEY', ''),
    'secret_key': os.getenv('MEDIA_S3_SECRET_KEY', ''),
    'custom_domain': os.getenv('MEDIA_S3_CUSTOM_DOMAIN', '') or None,
    'querystring_auth': False,
    'default_acl': None,
    'file_overwrite': False,
}
if MEDIA_S3_ENABLED and not MEDIA_S3_OPTIONS['bucket_name']:
    raise ImproperlyConfigured('MEDIA_S3_BUCKET is required.')

import re
GTM_CONTAINER_ID = os.getenv('GTM_CONTAINER_ID', '')
if GTM_CONTAINER_ID and not re.fullmatch(r'GTM-[A-Z0-9]+', GTM_CONTAINER_ID):
    raise ImproperlyConfigured('Invalid GTM_CONTAINER_ID.')
