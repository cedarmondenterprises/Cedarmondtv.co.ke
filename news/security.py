from django.conf import settings

def client_ip(request):
    # Only trust forwarding headers when web is private behind our reverse proxy.
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR','') if settings.TRUST_PROXY_HEADERS else ''
    return forwarded.split(',')[-1].strip() if forwarded else request.META.get('REMOTE_ADDR','127.0.0.1')

def rate_key(group,request):
    return client_ip(request)
