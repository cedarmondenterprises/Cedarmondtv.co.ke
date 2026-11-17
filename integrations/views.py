import hashlib
import json
import secrets
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse, Http404
from django.template.response import TemplateResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_GET
from django_ratelimit.decorators import ratelimit
from news.security import rate_key
from .models import PushSubscription


def dashboard(request, site):
    if not request.user.is_superuser: raise PermissionDenied
    rows = [
        ('Django Unfold', True, 'White and red admin; existing 2FA enforced when enabled.'),
        ('Import/export', True, 'Superuser-only category/topic CSV import and export.'),
        ('ImageKit', True, 'WebP article and card sizes generated on upload.'),
        ('S3 media storage', settings.MEDIA_S3_ENABLED, 'Existing media must be migrated before switching storage.'),
        ('Meilisearch', bool(settings.MEILISEARCH_URL and settings.MEILISEARCH_KEY), 'Requires sync worker; database fallback remains available.'),
        ('Umami', bool(settings.UMAMI_SCRIPT_URL and settings.UMAMI_WEBSITE_ID), 'Analytics starts only after reader consent.'),
        ('Listmonk', bool(settings.LISTMONK_URL and settings.LISTMONK_TOKEN), 'Console command creates newsletter drafts; never auto-sends.'),
        ('Anymail', settings.EMAIL_BACKEND.startswith('anymail.'), 'Provider credentials and authenticated webhook required.'),
        ('Web push', settings.WEBPUSH_ENABLED, 'Opt-in subscription and explicit console delivery.'),
        ('CookieConsent', True, 'Reader-controlled optional analytics and advertising.'),
        ('Celery', False, 'Check worker container separately; settings alone do not prove it is running.'),
        ('Celery Beat', False, 'Start exactly one scheduler container.'),
        ('GlitchTip/Sentry', bool(settings.SENTRY_DSN), 'DSN configured; verify receipt in the error dashboard.'),
        ('Uptime Kuma', bool(settings.INTEGRATION_LINKS['UPTIME_KUMA_URL']), 'Monitor setup and external host required.'),
        ('Dependency health', True, 'Staff-only database and cache checks.'),
        ('Restic', False, 'Run backup and isolated restore verification; configure off-server destination.'),
        ('Guardian', True, 'Console grants for individual draft collaboration.'),
        ('Auditlog', True, 'Changes to ads and breaking-news settings; excludes subscriber data.'),
        ('axe-core', True, 'Accessibility checks available through npm run test:a11y.'),
        ('pip-audit', True, 'Dependency scan in CI; inspect workflow results.'),
    ]
    return TemplateResponse(request, 'admin/integrations.html', dict(site.each_context(request),
        title='Platform integrations', integrations=rows, integration_links=settings.INTEGRATION_LINKS))

@never_cache
def dependency_health(request):
    if not request.user.is_superuser: raise PermissionDenied
    from health_check.mixins import CheckMixin
    check = CheckMixin()
    check.use_threading = False
    errors = check.run_check()
    return JsonResponse({'status':'error' if errors else 'ok'}, status=503 if errors else 200)

@require_GET
@never_cache
def service_worker(request):
    if not settings.WEBPUSH_ENABLED: raise Http404
    from pathlib import Path
    body = (Path(__file__).parent/'webpush-worker.js').read_text()
    response=HttpResponse(body,content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response

@require_POST
@never_cache
@ratelimit(key=rate_key, rate='10/h', method='POST', block=False)
def push_subscription(request):
    if not settings.WEBPUSH_ENABLED: raise Http404
    if getattr(request, 'limited', False): return JsonResponse({'error':'Try later'},status=429)
    if len(request.body)>4096: return JsonResponse({'error':'Too large'},status=400)
    try:
        data=json.loads(request.body)
        endpoint=data['endpoint']; url=urlsplit(endpoint)
        if url.scheme!='https' or url.hostname not in settings.WEBPUSH_ALLOWED_HOSTS or url.port not in (None,443) or url.username or url.password:
            raise ValueError()
        token=request.headers.get('X-Subscription-Token','')
        existing=PushSubscription.objects.filter(endpoint=endpoint).first()
        if existing and not secrets.compare_digest(existing.token_hash,hashlib.sha256(token.encode()).hexdigest()):
            return JsonResponse({'error':'Subscription ownership required'},status=403)
        if data.get('action')=='delete':
            if existing: existing.delete()
            return JsonResponse({'ok':True})
        keys=data['keys']
        import base64
        for key,length in [('p256dh',65),('auth',16)]:
            value=keys[key]
            if len(value)>200 or len(base64.urlsafe_b64decode(value+'='*(-len(value)%4)))!=length: raise ValueError()
        token=secrets.token_urlsafe(32)
        PushSubscription.objects.update_or_create(endpoint=endpoint,defaults={
            'p256dh':keys['p256dh'],'auth':keys['auth'],'token_hash':hashlib.sha256(token.encode()).hexdigest()})
        return JsonResponse({'token':token})
    except (KeyError,TypeError,ValueError,AttributeError):
        return JsonResponse({'error':'Invalid subscription'},status=400)
