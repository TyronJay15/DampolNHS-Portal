"""CSRF protection for the endpoints that read or write the sign-in cookie: login, refresh and logout.

Every other API request is authenticated by the Authorization header, which a browser never adds by itself, so
only these three can be forged from another site. They use Django's own CSRF check: the X-CSRFToken header must
match the csrftoken cookie, and over HTTPS the Origin must be one of CSRF_TRUSTED_ORIGINS. The frontend gets the
token from GET /api/auth/csrf/ (CsrfTokenView) and keeps it in memory.
"""

from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied


def enforce_csrf(request):
    check = CSRFCheck(lambda _request: None)
    check.process_request(request)
    reason = check.process_view(request, None, (), {})
    if reason:
        raise PermissionDenied('The security check failed. Reload the page and try again.', code='csrf_failed')
