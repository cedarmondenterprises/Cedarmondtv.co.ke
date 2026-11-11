import base64
import secrets


class CSPNonceMiddleware:
    """Apply a nonce-based CSP to public HTML while leaving Django admin's own UI policy intact."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = base64.b64encode(secrets.token_bytes(18)).decode('ascii')
        response = self.get_response(request)
        content_type = response.get('Content-Type', '')
        if request.path.startswith('/admin/') or request.path.startswith(('/api/docs/', '/api/redoc/')) or not content_type.startswith('text/html'):
            return response
        nonce = request.csp_nonce
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            f"script-src 'nonce-{nonce}' 'strict-dynamic' 'unsafe-inline' 'unsafe-eval' https: http:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' https: data: blob:; "
            "font-src 'self' https: data:; "
            "connect-src 'self' https:; "
            "frame-src https:; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; "
            "upgrade-insecure-requests"
        )
        return response
