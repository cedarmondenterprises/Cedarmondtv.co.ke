def client_ip(request):
    # Production web has no host port; Caddy overwrites forwarding headers.
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[-1].strip() if forwarded else request.META.get('REMOTE_ADDR')
