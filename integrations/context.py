from django.conf import settings

def public_integrations(request):
    return {
        'umami_script_url': settings.UMAMI_SCRIPT_URL,
        'umami_website_id': settings.UMAMI_WEBSITE_ID,
        'webpush_enabled': settings.WEBPUSH_ENABLED,
        'gtm_container_id': settings.GTM_CONTAINER_ID,
        'vapid_public_key': settings.VAPID_PUBLIC_KEY if settings.WEBPUSH_ENABLED else '',
    }
