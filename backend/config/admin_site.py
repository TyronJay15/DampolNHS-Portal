"""The Django admin console, used only by maintenance accounts.

Failed sign-ins are limited per address, and every successful one is audited and reported to the administrators
(apps.accounts.signals).
"""

from django.contrib.admin import AdminSite
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.throttling import BaseThrottle

FAILED_LIMIT = 10
FAILED_WINDOW = 3600  # seconds


class PortalAdminSite(AdminSite):
    site_header = 'Dampol 1st NHS maintenance console'
    site_title = 'Maintenance console'

    def login(self, request, extra_context=None):
        key = f'admin_login_failures_{BaseThrottle().get_ident(request)}'
        if request.method == 'POST' and cache.get(key, 0) >= FAILED_LIMIT:
            return HttpResponse('Too many failed sign-ins from this address. Try again later.', status=429)
        response = super().login(request, extra_context)
        # A sign-in that passed the password answers with a redirect into the console.
        signed_in = response.status_code == 302 and request.user.is_authenticated
        if request.method == 'POST' and not signed_in:
            cache.set(key, cache.get(key, 0) + 1, FAILED_WINDOW)
        return response
