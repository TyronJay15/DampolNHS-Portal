"""Security headers for API answers (security plan W5, section 34).

The API only returns JSON, so its pages may load nothing and may not be framed. Django's own middleware already
sends nosniff, the referrer policy, X-Frame-Options, Cross-Origin-Opener-Policy and (in production) HSTS. The
maintenance console keeps Django's defaults because it needs its own scripts and styles.
"""

API_POLICY = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'


class ApiSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/'):
            response.headers.setdefault('Content-Security-Policy', API_POLICY)
        response.headers.setdefault('Permissions-Policy', PERMISSIONS_POLICY)
        return response
