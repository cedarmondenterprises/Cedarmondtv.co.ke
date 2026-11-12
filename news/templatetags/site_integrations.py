import os
from urllib.parse import urlsplit

from django import template

register = template.Library()

VERIFICATION_FIELDS = (
    ('GOOGLE_SITE_VERIFICATION', 'google-site-verification'),
    ('BING_SITE_VERIFICATION', 'msvalidate.01'),
    ('YANDEX_SITE_VERIFICATION', 'yandex-verification'),
    ('PINTEREST_SITE_VERIFICATION', 'p:domain_verify'),
)

CHANNELS = (
    ('WHATSAPP_CHANNEL_URL', 'WhatsApp', {'whatsapp.com', 'www.whatsapp.com'}),
    ('YOUTUBE_CHANNEL_URL', 'YouTube', {'youtube.com', 'www.youtube.com'}),
    ('TELEGRAM_CHANNEL_URL', 'Telegram', {'t.me'}),
    ('FACEBOOK_PAGE_URL', 'Facebook', {'facebook.com', 'www.facebook.com'}),
    ('INSTAGRAM_PROFILE_URL', 'Instagram', {'instagram.com', 'www.instagram.com'}),
    ('TIKTOK_PROFILE_URL', 'TikTok', {'tiktok.com', 'www.tiktok.com'}),
)


@register.inclusion_tag('news/site_verification.html')
def site_verification():
    return {'verification': [
        (name, value) for key, name in VERIFICATION_FIELDS
        if (value := os.getenv(key, '').strip())
    ]}


@register.inclusion_tag('news/social_channels.html')
def social_channels():
    links = []
    for key, label, hosts in CHANNELS:
        value = os.getenv(key, '').strip()
        try:
            url = urlsplit(value)
        except ValueError:
            continue
        if url.scheme == 'https' and url.netloc.lower() in hosts and url.path.strip('/'):
            links.append((label, value))
    return {'channels': links}
