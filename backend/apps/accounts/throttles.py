"""Request limits for abuse-sensitive endpoints. Over the limit, the API answers 429.

Rates come from settings.API_THROTTLE_RATES at request time, so they can be tuned per environment and tests
can set their own. A scope with no rate is not limited. Counts live in Django's cache (per process); with
one web worker on Railway that is enough, and a shared cache can be added later without code changes.
"""

import hashlib
import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class ScopedThrottle(ScopedRateThrottle):
    """Per visitor (signed-in user, else IP address), with the view's throttle_scope.

    A view may set throttle_methods, e.g. ('POST',), so reading the same page is never limited.
    """

    def get_rate(self):
        return settings.API_THROTTLE_RATES.get(self.scope)

    def allow_request(self, request, view):
        methods = getattr(view, 'throttle_methods', None)
        if methods and request.method not in methods:
            return True
        return super().allow_request(request, view)


class LoginAccountThrottle(SimpleRateThrottle):
    """Failed sign-ins per account, whatever the IP, so one account cannot be guessed at from many places.

    Only failures count (record_failed_login), so a person who types the right password is never slowed down by
    their own successful sign-ins. The limit slides: each failure drops out after the period, so the lock is
    temporary and cannot be made permanent by an attacker. The identifier is stored only as a hash.
    """

    scope = 'login_account'

    def get_rate(self):
        return settings.API_THROTTLE_RATES.get(self.scope)

    def get_cache_key(self, request, view):
        return failure_key(request.data.get('identifier'))

    def allow_request(self, request, view):
        if self.rate is None:
            return True
        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True
        self.now = self.timer()
        self.history = [moment for moment in self.cache.get(self.key, []) if moment > self.now - self.duration]
        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
        return True


def failure_key(identifier):
    text = str(identifier or '').strip().lower()
    if not text:
        return None
    return 'throttle_login_account_' + hashlib.sha256(text.encode()).hexdigest()


def record_failed_login(identifier):
    """Count one failed sign-in for this identifier. Returns True when this failure reached the limit."""
    rate = settings.API_THROTTLE_RATES.get(LoginAccountThrottle.scope)
    key = failure_key(identifier)
    if not rate or key is None:
        return False
    limit, duration = LoginAccountThrottle().parse_rate(rate)
    now = time.time()
    history = [moment for moment in cache.get(key, []) if moment > now - duration]
    history.insert(0, now)
    cache.set(key, history, duration)
    return len(history) == limit
