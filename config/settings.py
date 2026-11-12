import os
from datetime import timedelta
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DEBUG', '0') == '1'
SECRET_KEY = os.getenv('SECRET_KEY', 'development-only-key' if DEBUG else '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set SECRET_KEY before starting production.')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000').rstrip('/')
CSRF_TRUSTED_ORIGINS = [SITE_URL]
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','django.contrib.sitemaps','rest_framework','drf_spectacular','drf_spectacular_sidecar','axes','django_prose_editor','simple_history','post_office','news']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','news.security_headers.CSPNonceMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','axes.middleware.AxesMiddleware','simple_history.middleware.HistoryRequestMiddleware']
ROOT_URLCONF = 'config.urls'
LOGIN_URL = '/admin/login/'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','news.context.site','news.context.admin_dashboard']}}]
WSGI_APPLICATION = 'config.wsgi.application'
if os.getenv('POSTGRES_HOST'):
    DATABASES = {'default':{'ENGINE':'django.db.backends.postgresql','HOST':os.environ['POSTGRES_HOST'],'NAME':os.getenv('POSTGRES_DB','cedarmond'),'USER':os.getenv('POSTGRES_USER','cedarmond'),'PASSWORD':os.environ['POSTGRES_PASSWORD'],'CONN_MAX_AGE':60}}
else:
    DATABASES = {'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.'+name} for name in ['UserAttributeSimilarityValidator','MinimumLengthValidator','CommonPasswordValidator','NumericPasswordValidator']]
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend','django.contrib.auth.backends.ModelBackend']
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']
AXES_CLIENT_IP_CALLABLE = 'news.security.client_ip'
LANGUAGE_CODE = 'en-ke'
TIME_ZONE = 'Africa/Nairobi'
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR/'staticfiles'
STATICFILES_DIRS = [BASE_DIR/'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR/'media'
STORAGES = {'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https')
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
# Do not preload or extend HSTS to subdomains until every subdomain is confirmed HTTPS-only.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST','')
EMAIL_PORT = int(os.getenv('EMAIL_PORT','587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS','1') == '1'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL','0') == '1'
EMAIL_TIMEOUT = 20
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL','Cedarmond TV <news@cedarmondtv.co.ke>')

# Optional services are never presented as working until configured.
NEWSLETTER_ENABLED = os.getenv('NEWSLETTER_ENABLED','0') == '1'
REDIS_URL = os.getenv('REDIS_URL','')
if REDIS_URL:
    CACHES = {'default': {'BACKEND':'django_redis.cache.RedisCache','LOCATION':REDIS_URL,'OPTIONS':{'CLIENT_CLASS':'django_redis.client.DefaultClient','SOCKET_CONNECT_TIMEOUT':3,'SOCKET_TIMEOUT':3}}}
else:
    CACHES = {'default': {'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
RATELIMIT_ENABLE = bool(REDIS_URL)
TRUST_PROXY_HEADERS = os.getenv('TRUST_PROXY_HEADERS','0') == '1'
SIMPLE_HISTORY_REVERT_DISABLED = True
POST_OFFICE = {'BACKENDS':{'default':EMAIL_BACKEND},'DEFAULT_PRIORITY':'medium','MAX_RETRIES':3,'RETRY_INTERVAL':timedelta(minutes=5),'BATCH_SIZE':100,'THREADS_PER_PROCESS':1}
POST_OFFICE_CACHE = False
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PAGINATION_CLASS': 'news.api_support.PublicPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': ['news.api_support.PublicAPIThrottle'],
    'DEFAULT_THROTTLE_RATES': {'public_api': '600/hour'},
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
SPECTACULAR_SETTINGS = {
    'TITLE': 'Cedarmond TV Public API',
    'DESCRIPTION': 'Read-only access to Cedarmond TV published articles and newsroom metadata.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'REDOC_DIST': 'SIDECAR',
}
if not DEBUG:
    if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('replace-'):
        raise ImproperlyConfigured('Production SECRET_KEY must contain at least 50 random characters.')
    if not SITE_URL.startswith('https://'):
        raise ImproperlyConfigured('Production SITE_URL must use HTTPS.')
    if NEWSLETTER_ENABLED and (not EMAIL_HOST or EMAIL_BACKEND != 'django.core.mail.backends.smtp.EmailBackend'):
        raise ImproperlyConfigured('Newsletter requires an SMTP host and SMTP backend.')

SENTRY_DSN = os.getenv('SENTRY_DSN', '').strip()
if SENTRY_DSN and not DEBUG:
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.getenv('SENTRY_ENVIRONMENT', 'production'),
        send_default_pii=False,
        max_request_body_size='never',
        traces_sample_rate=0.0,
        include_local_variables=False,
    )
